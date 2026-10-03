"""
RAGFlow 知识库管理示例模块

演示如何用 RAGFlow SDK 通过代码创建知识库、批量上传文档。
学习阶段仍建议优先用 RAGFlow 页面操作，因为页面能直观看到每个文件的解析状态；
本模块用于理解 SDK 的调用方式，等流程跑通后再考虑做成后台管理能力。
"""

import os

from ragflow_sdk import RAGFlow

from app.ragflow.rag_config import _load_ragflow_env

# RAGFlow SDK 的入口客户端，后续 Dataset、Chat、Session 操作都从这里发起
api_key, base_url = _load_ragflow_env()
ragflow_client = RAGFlow(api_key=api_key, base_url=base_url)


def create_knowledge_base(
    knowledge_base_name: str,  # 知识库名称
    description: str,  # 知识库描述
    embedding_model: str = "Qwen/Qwen3-Embedding-8B@SILICONFLOW",  # 嵌入模型，格式为「模型名@供应商」
) -> object:
    """
    通过代码创建 RAGFlow 知识库

    知识库名称和描述要写准确：后续聊天助手会绑定知识库，
    Agent 又会根据助手描述和关联知识库来判断该问哪个助手。
    :param knowledge_base_name: 知识库名称
    :param description: 知识库描述
    :param embedding_model: 嵌入模型，必须和 RAGFlow 页面里已配置的模型保持一致
    :return: 创建出的 Dataset 对象，id 即知识库 ID
    """
    # RAGFlow SDK 中知识库通常对应 Dataset；Chat 会再绑定一个或多个 Dataset 对外提供问答
    # embedding_model 需要和 RAGFlow 页面中可用的模型供应商配置保持一致
    # 注意：教程示例用的是 text-embedding-v3@Tongyi-Qianwen，本项目实际配置的是硅基流动的嵌入模型
    ds = ragflow_client.create_dataset(
        name=knowledge_base_name,
        description=description,
        embedding_model=embedding_model,
    )
    print(f"创建知识库成功：{ds},{ds.id}")
    return ds


def upload_file_to_knowledge_base(kb_id: str, file_paths: list[str]) -> None:
    """
    向指定知识库上传一个或多个本地文件

    注意：此函数只负责把文件送进 Dataset。上传后仍需要在 RAGFlow 页面或任务中完成解析，
    否则文档还没有切片、向量化，后续聊天助手可能检索不到内容。
    :param kb_id: RAGFlow 知识库 ID，也就是 Dataset ID
    :param file_paths: 本地文件路径列表
    """
    # 先根据知识库 ID 查询 Dataset 对象，确认文件会上传到目标知识库
    datasets = ragflow_client.list_datasets(id=kb_id, page=1, page_size=10)
    dataset = datasets[0]

    # RAGFlow upload_documents 接收的是文档字典列表：
    # display_name/name 用于页面展示，blob 存放文件二进制内容
    document_list = []
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            blob = f.read()
            document_list.append(
                {"display_name": file_name, "name": file_name, "blob": blob}
            )

    # 上传完成后，RAGFlow 侧还要执行解析流程，解析成功后才能被 Chat 检索
    dataset.upload_documents(document_list)
