"""
RAGFlow 工具模块

把 RAGFlow 的聊天助手能力封装成 Agent 可调用的 LangChain 工具。
get_assistant_list 负责让模型先知道"有哪些助手、各自能回答什么"，
后面的提问工具再根据这里的结果选择要向哪个助手提问。
"""

from langchain_core.tools import tool
from ragflow_sdk import RAGFlow

from app.api.monitor import monitor
from app.ragflow.rag_config import _load_ragflow_env

# 模块级复用 RAGFlow 客户端，避免每次工具调用都重新初始化 SDK 对象
api_key, base_url = _load_ragflow_env()
ragflow_client = RAGFlow(api_key=api_key, base_url=base_url)


# @tool 会把函数签名和 docstring 暴露给 DeepAgents，模型据此决定是否调用以及如何填参
@tool
def get_assistant_list() -> str:
    """
    查询 RAGFlow 中有哪些聊天助手，以及每个助手关联了哪些知识库

    作用：让模型先了解"哪个助手能回答哪类内部文档问题"，再决定后续要向哪个助手提问。
    调用 create_ask_delete 之前，应先调用本工具确认助手名称。
    :return: 有助手时返回助手名称、功能介绍、关联知识库；无助手或异常时返回中文提示
    """
    # 埋点：工具被调用后，前端可以展示当前正在查询 RAGFlow 助手列表
    monitor.report_tool(
        tool_name="ragflow聊天助手列表查询工具：get_assistant_list", args={}
    )

    try:
        # list_chats 查询的是 RAGFlow 的 Chat 层，不是 Dataset 层
        # Chat 负责对外问答，Dataset 只负责承载文档
        chat_list = ragflow_client.list_chats()
        if not chat_list:
            return "没有任何可用助手"

        # 把每个助手的名称、描述和绑定知识库拼成模型容易阅读的路由信息
        count_chat_info = ""
        for chat in chat_list:
            # SDK 的 Chat 类只在运行时按接口响应补字段，静态类型标注里没有 description
            # 统一用 getattr 读取，同时兼容没写描述或没绑定知识库的助手
            description = getattr(chat, "description", "") or ""
            dataset_names = getattr(chat, "kb_names", []) or []
            kb_text = "、".join(dataset_names)

            count_chat_info += (
                f"助手名称:{chat.name};功能介绍：{description}; "
                f"关联的知识库：{kb_text} \n"
            )
        return count_chat_info
    except Exception as e:  # noqa: BLE001  工具异常不能中断 Agent 执行链路
        return f"查询助手信息异常，无可用助手,异常信息:{e!s}"
