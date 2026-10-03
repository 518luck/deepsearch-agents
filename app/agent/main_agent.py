"""
主智能体组装模块

把 DeepAgents 的主智能体装配起来：模型和提示词决定它是谁，
三个文件工具让它能读附件、写 Markdown、转 PDF，
三个子智能体让它可以委派网络搜索、数据库查询和知识库检索。
"""

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.llm import model
from app.agent.prompts import main_agent_content
from app.agent.subagents.database_query_agent import database_query_agent
from app.agent.subagents.knowledge_base_agent import knowledge_base_agent
from app.agent.subagents.network_search_agent import network_search_agent

# 文件类工具由主智能体直接掌握，负责读取上传附件和生成最终交付文档
from app.tools.markdown_tools import generate_markdown
from app.tools.pdf_tools import convert_md_to_pdf
from app.tools.upload_file_read_tool import read_file_content

# 主智能体是调度中心：
# 1. tools 只放最终交付相关的文件工具
# 2. subagents 放网络、数据库、RAGFlow 三类信息获取助手
# 3. checkpointer 通过 thread_id 保存同一会话中的执行上下文
main_agent = create_deep_agent(
    model=model,
    system_prompt=main_agent_content["system_prompt"],
    tools=[generate_markdown, convert_md_to_pdf, read_file_content],
    checkpointer=InMemorySaver(),
    subagents=[database_query_agent, network_search_agent, knowledge_base_agent],
)
