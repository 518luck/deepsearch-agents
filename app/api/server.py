"""
FastAPI 服务入口模块

把主智能体接到 HTTP 与 WebSocket 上：HTTP 负责发起动作（启动任务、取消、
上传、列文件、下载），WebSocket 负责把执行过程的进度推回前端。

本模块先做基础准备（生命周期、应用对象、运行目录、跨域），
再提供任务接口：启动任务、替换同会话旧任务、取消任务。
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent.main_agent import run_deep_agent
from app.api.monitor import manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    服务生命周期入口。

    启动时绑定当前事件循环到 WebSocket 管理器，确保后台 Agent 任务可以把
    monitor 事件投递回 FastAPI 所在的 loop。
    """
    loop = asyncio.get_running_loop()
    manager.set_loop(loop)
    print(f"[Server] WebSocket Manager bound to loop: {id(loop)}")
    yield


# 当前文件位于 app/api/server.py，运行时目录统一收敛到 app 目录
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

app = FastAPI(title="DeepAgents API", lifespan=lifespan)

# 教学项目通常前后端分别本地启动，这里放开跨域以便 Vite 页面直接调用 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 保存 thread_id -> 后台 Agent 任务，用于同一会话任务替换和主动取消
active_tasks: dict[str, asyncio.Task] = {}

# output 保存每个会话最终工作区，前端只允许从这里浏览和下载生成文件
output_dir = project_root / "output"
output_dir.mkdir(exist_ok=True)

# updated 暂存用户上传文件，run_deep_agent 启动时会复制到对应 output/session_xxx
updated_dir = project_root / "updated"
updated_dir.mkdir(exist_ok=True)


class TaskRequest(BaseModel):
    """前端启动任务时提交的请求体。"""

    query: str
    thread_id: str | None = None


def _forget_task(thread_id: str, task: asyncio.Task) -> None:
    """
    清理已结束任务的登记关系。

    done_callback 触发时，active_tasks 中可能已经被新任务替换；只有仍是同一个
    task 时才删除，避免误清理同 thread_id 下刚启动的新任务。
    """
    if active_tasks.get(thread_id) is task:
        active_tasks.pop(thread_id, None)


@app.post("/api/task")
async def run_task(request: TaskRequest):
    """
    启动一次 DeepAgents 后台任务。

    HTTP 请求只负责创建后台协程并立即返回，后续执行轨迹、子智能体调用和最终
    答案都会由 monitor 通过 `/ws/{thread_id}` 推送给同一会话的前端。
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    # 同一个 thread_id 只保留一个活跃任务，新任务会先取消旧任务，避免并发写同一会话目录
    old_task = active_tasks.get(thread_id)
    if old_task and not old_task.done():
        old_task.cancel()

    # create_task 把长耗时 Agent 执行交给事件循环，接口本身不用等待最终结果
    task = asyncio.create_task(run_deep_agent(request.query, thread_id))
    active_tasks[thread_id] = task
    task.add_done_callback(lambda finished_task: _forget_task(thread_id, finished_task))

    return {"status": "started", "thread_id": thread_id}


@app.post("/api/task/{thread_id}/cancel")
async def cancel_task(thread_id: str):
    """
    取消指定 thread_id 对应的后台 Agent 任务。

    注意：取消会向 asyncio.Task 注入 CancelledError。若底层第三方工具正在执行不可中断
    的同步阻塞调用，任务可能需要等该调用返回后才会真正结束。
    """
    task = active_tasks.get(thread_id)
    if not task or task.done():
        active_tasks.pop(thread_id, None)
        raise HTTPException(status_code=404, detail="任务不存在或已结束")

    # 先发出取消信号，再短暂等待协程响应；若底层阻塞中，则返回 cancelling 给前端继续展示状态
    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.CancelledError:
        _forget_task(thread_id, task)
        return {"status": "cancelled", "thread_id": thread_id}
    except TimeoutError:
        # 超时说明取消信号已发出但协程还没退出，保持登记让前端继续展示"取消中"
        return {"status": "cancelling", "thread_id": thread_id}
    except Exception as e:  # noqa: BLE001  取消失败也要回给前端，不能变成 500
        _forget_task(thread_id, task)
        return {"status": "cancelled", "thread_id": thread_id, "message": str(e)}

    _forget_task(thread_id, task)
    return {"status": "cancelled", "thread_id": thread_id}
