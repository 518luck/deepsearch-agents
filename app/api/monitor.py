"""Agent 执行监控：把工具调用、子智能体调用、任务结果等事件统一包装后推送。"""

import asyncio
import builtins
import datetime
from typing import Any, Self

from fastapi import WebSocket

from app.api.context import get_thread_context


class ToolMonitor:
    """工具和子智能体的统一监控入口，业务代码只调 report_* 方法，不关心推送细节。"""

    _instance = None  # 类级单例缓存

    def __new__(cls) -> Self:
        """保证全局唯一实例，初始未绑定连接管理器。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.websocket_manager = None  # 连接管理器，服务启动时绑定
        return cls._instance

    def set_websocket_manager(self, manager: "ConnectionManager") -> None:
        """绑定 FastAPI 的 WebSocket 连接管理器。"""
        self.websocket_manager = manager

    def _emit(
        self,
        event_type: str,  # 事件类型，如 tool_start、assistant_call
        message: str,  # 面向前端展示的事件说明
        data: dict[str, Any] | None = None,  # 附加结构化数据
    ) -> None:
        """构造统一监控事件，并推送到当前 thread_id 对应的前端连接。"""
        payload = {
            "type": "monitor_event",
            "event": event_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        if self.websocket_manager:
            try:
                # thread_id 来自 ContextVar，确保事件只推给当前任务对应的前端连接
                thread_id = get_thread_context()
                manager_loop = self.websocket_manager.loop

                if manager_loop and thread_id:
                    self._send_to_websocket(payload, thread_id, manager_loop)
            except Exception as e:  # noqa: BLE001  监控失败不允许中断主任务
                print(f"[Monitor] WebSocket send failed: {e}")

        # DeepAgents 脚本调试时，若运行时暴露了 stream_writer，同步写入流式输出
        # runtime 由脚本模式动态注入 builtins，静态类型检查器不可知，用 getattr 读取
        runtime = getattr(builtins, "runtime", None)
        if runtime is not None and hasattr(runtime, "stream_writer"):
            try:
                runtime.stream_writer(payload)
            except Exception:  # noqa: BLE001, S110  调试通道失败时静默忽略
                pass

        # 控制台保底输出，无前端场景也能观察执行过程
        print(f"\n[Monitor:{event_type}] {message}")

    def _send_to_websocket(
        self,
        payload: dict[str, Any],  # 统一消息体
        thread_id: str,  # 目标前端连接的任务 ID
        manager_loop: asyncio.AbstractEventLoop,  # WebSocket 所属事件循环
    ) -> None:
        """把监控事件投递回 WebSocket 所在的事件循环。"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        coroutine = self.websocket_manager.send_to_thread(payload, thread_id)
        if current_loop and current_loop == manager_loop:
            current_loop.create_task(
                coroutine
            )  # 已在 WebSocket 所属循环，直接派生异步任务
        else:
            # ! WebSocket 只能在创建它的循环里收发消息，跨线程/跨循环必须走线程安全投递
            asyncio.run_coroutine_threadsafe(coroutine, manager_loop)

    def report_tool(self, tool_name: str, args: dict[str, Any] | None = None) -> None:
        """报告开始执行某个工具。"""
        self._emit(
            "tool_start",
            f"开始执行工具: {tool_name}",
            {"tool_name": tool_name, "args": args},  # args: 工具入参快照
        )

    def report_assistant(
        self, assistant_name: str, args: dict[str, Any] | None = None
    ) -> None:
        """报告正在调用某个子智能体。"""
        self._emit(
            "assistant_call",
            f"正在调用助手: {assistant_name}",
            {"assistant_name": assistant_name, "args": args},  # args: 调用入参快照
        )

    def report_task_result(self, result: str) -> None:
        """报告任务最终结果。"""
        self._emit("task_result", "任务执行完成", {"result": result})

    def report_task_cancelled(self) -> None:
        """报告任务已被用户取消。"""
        self._emit("task_cancelled", "任务已取消")

    def report_session_dir(self, path: str) -> None:
        """报告当前会话输出目录。"""
        self._emit("session_created", f"工作目录已创建: {path}", {"path": path})


# > 模块级单例，业务代码统一 `from app.api.monitor import monitor` 使用，禁止重新实例化
monitor = ToolMonitor()


class ConnectionManager:
    """WebSocket 连接管理器，active_connections 以 thread_id 为 key，事件只发回对应页面。"""

    def __init__(self) -> None:
        """初始化空连接表，事件循环留待服务启动时绑定。"""
        self.active_connections: dict[str, WebSocket] = {}  # thread_id -> 前端连接
        # WebSocket 发送必须回到创建连接的事件循环，启动时需显式绑定 loop
        self.loop: asyncio.AbstractEventLoop | None = None

    # > 必须在服务启动时调用；未绑定 loop 前 monitor 只会走控制台输出
    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """记录 FastAPI 主事件循环，并把自身注册到 monitor。"""
        self.loop = loop
        monitor.set_websocket_manager(self)
        print(f"[Monitor] ConnectionManager manually bound to loop: {id(self.loop)}")

    async def connect(self, websocket: WebSocket, thread_id: str) -> None:
        """接受 WebSocket 连接并按 thread_id 保存。"""
        await websocket.accept()
        self.active_connections[thread_id] = websocket

    def disconnect(self, websocket: WebSocket, thread_id: str) -> None:
        """移除已断开的连接；新旧连接交替时保留当前生效的连接。"""
        if self.active_connections.get(thread_id) is websocket:
            del self.active_connections[thread_id]
            print(f"Client disconnected: {thread_id}")
        else:
            print(f"Stale websocket disconnected, current connection kept: {thread_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """向指定连接发送纯文本消息。"""
        await websocket.send_text(message)

    async def send_to_thread(self, message: dict[str, Any], thread_id: str) -> None:
        """向指定 thread_id 对应的前端连接发送 JSON 消息，连接不存在时静默跳过。"""
        if thread_id in self.active_connections:
            websocket = self.active_connections[thread_id]
            await websocket.send_json(message)


# 模块级单例，由 server 启动时 set_loop 绑定到主事件循环
manager = ConnectionManager()
