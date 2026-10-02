# 请求上下文：在异步请求链路中保存当前任务的 thread_id 和 session_dir，深层函数免传参读取
from contextvars import ContextVar, Token

# > 协程级上下文变量，每个 asyncio Task 各持一份值，禁止改成全局变量或 threading.local
_session_dir_ctx: ContextVar[str | None] = ContextVar("session_dir", default=None)
_thread_id_ctx: ContextVar[str | None] = ContextVar("thread_id", default=None)


# 设置当前请求链路的会话目录
def set_session_context(path: str) -> Token[str | None]:
    return _session_dir_ctx.set(path)  # path: 当前任务的工作目录


# 读取当前请求链路的会话目录，未设置时返回 None
def get_session_context() -> str | None:
    return _session_dir_ctx.get()


# 设置当前请求链路的线程 ID
def set_thread_context(thread_id: str) -> Token[str | None]:
    return _thread_id_ctx.set(
        thread_id
    )  # thread_id: 前端连接与 Agent 执行共用的任务 ID


# 读取当前请求链路的线程 ID，未设置时返回 None
def get_thread_context() -> str | None:
    return _thread_id_ctx.get()


# 恢复请求进入前的上下文，防止本次任务信息残留到后续请求
# ! Web 服务常驻运行，任务结束必须用 token reset，禁止跳过
def reset_session_context(
    session_token: Token[str | None],  # set_session_context 返回的 token
    thread_token: Token[str | None] | None = None,  # set_thread_context 返回的 token
) -> None:
    _session_dir_ctx.reset(session_token)
    if thread_token is not None:
        _thread_id_ctx.reset(thread_token)
