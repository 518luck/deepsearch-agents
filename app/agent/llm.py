"""
大模型初始化模块

负责从 .env 中读取模型配置，并创建项目统一复用的模型对象。
后续主智能体和子智能体都从这里导入 model，避免在多个文件里重复加载环境变量。
"""

import os
from typing import cast

from dotenv import find_dotenv, load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

# find_dotenv 会从当前目录向上查找 .env，适合脚本和 Web 服务从不同入口启动的场景
load_dotenv(find_dotenv())

# 使用 OpenAI 兼容协议接入模型；具体模型名由 .env 中的 LLM_QWEN_MAX 控制
# init_chat_model 的返回标注是 BaseChatModel | _ConfigurableModel，但只有传 configurable_fields
# 时才会返回后者；这里没传，运行时必定是 BaseChatModel，cast 回真实类型供下游类型检查
model = cast(
    "BaseChatModel",
    init_chat_model(
        model=os.getenv("LLM_QWEN_MAX"),
        model_provider="openai",
    ),
)
