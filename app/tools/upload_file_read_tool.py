"""
上传文件读取工具模块

read_file_content 负责把用户本次上传的附件读出内容，交给主智能体继续分析。
按后缀分派到不同解析方式：Markdown/TXT 直接读文本，Word 读段落，PDF 提取页面文本，
Excel 读取表格并附上行数、列名、前 5 行和统计描述，未识别的后缀按文本兜底。
"""

from pathlib import Path
from typing import Annotated

import pandas as pd
from docx import Document
from langchain_core.tools import tool
from pypdf import PdfReader

from app.api.context import get_session_context, set_session_context
from app.api.monitor import monitor
from app.utils.path_utils import resolve_path

# 文本类后缀：直接按文本读取，不需要额外的解析器
_TEXT_SUFFIXES = {".md", ".txt"}

# Excel 类后缀：交给 pandas 解析后，再汇总成表格摘要
_EXCEL_SUFFIXES = {".xlsx", ".xls"}


def _read_text(file_path: Path) -> str:
    """按 UTF-8 读取文本，非法字节直接忽略，避免个别脏字符导致整个文件读不出来。"""
    return file_path.read_text(encoding="utf-8", errors="ignore")


def _read_docx(file_path: Path) -> str:
    """读取 Word 文档的段落文本，跳过空段落。"""
    document = Document(str(file_path))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
    return "\n".join(text for text in paragraphs if text)


def _read_pdf(file_path: Path) -> str:
    """逐页提取 PDF 文本，页面之间用换行拼接。"""
    reader = PdfReader(str(file_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _read_excel(file_path: Path) -> str:
    """读取 Excel，返回行数、列名、前 5 行和统计描述。"""
    dataframe = pd.read_excel(file_path)

    sections = [
        f"行数：{len(dataframe)}",
        f"列名：{', '.join(str(column) for column in dataframe.columns)}",
        "",
        "前 5 行：",
        dataframe.head(5).to_string(index=False),
    ]

    # describe 在数据全空或列类型无法统计时会报错，单独兜底，保证前 5 行仍然返回给模型
    try:
        sections += ["", "统计描述：", dataframe.describe(include="all").to_string()]
    except Exception:  # noqa: BLE001  统计失败不影响表格本体展示
        sections += ["", "统计描述：当前数据无法生成统计信息"]

    return "\n".join(sections)


@tool
def read_file_content(
    filename: Annotated[
        str, "要读取的文件名或路径（支持 .md, .docx, .pdf, .xlsx, .xls）"
    ],
    instruction: Annotated[
        str, "对提取内容的具体指令（例如：'提取摘要', '统计数据'）"
    ] = "提取全部内容",
) -> str:
    """
    读取当前会话目录中的指定文件内容

    对于 Excel 文件，会自动提供数据统计信息（head 和 describe）。
    :param filename: 文件名或相对路径，通常由主智能体从上传文件列表中选择
    :param instruction: 模型传入的读取意图，用于监控展示，不改变底层解析逻辑
    :return: 文件文本内容、表格摘要，或中文错误提示
    """
    monitor.report_tool(
        "文件内容读取工具", {"filename": filename, "instruction": instruction}
    )

    # 解析路径时优先约束在当前 session_dir 内，避免模型传入绝对路径导致越界读取
    session_dir = get_session_context()
    file_path = Path(resolve_path(filename, session_dir))

    if not file_path.exists():
        return f"错误：文件 '{filename}' 不存在 (解析路径: {file_path})。"

    # 根据文件后缀选择解析方式；未知后缀会先按 UTF-8 文本兜底读取
    ext = file_path.suffix.lower()

    try:
        if ext in _TEXT_SUFFIXES:
            return _read_text(file_path)
        if ext == ".docx":
            return _read_docx(file_path)
        if ext == ".pdf":
            return _read_pdf(file_path)
        if ext in _EXCEL_SUFFIXES:
            return _read_excel(file_path)
        return _read_text(file_path)
    except Exception as e:  # noqa: BLE001  读取失败返回中文提示，避免中断 Agent 执行链路
        return f"读取文件失败：{e!s}"


if __name__ == "__main__":
    # 本地调试入口：把会话目录临时固定到 examples/test_docs，逐个读取其中的测试文件
    test_docs_dir = Path(__file__).parents[2] / "examples" / "test_docs"
    set_session_context(str(test_docs_dir))

    for test_file in sorted(test_docs_dir.rglob("*")):
        if not test_file.is_file():
            continue
        relative_name = test_file.relative_to(test_docs_dir).as_posix()
        print("=" * 70)
        print(f"读取文件：{relative_name}")
        print(read_file_content.invoke({"filename": relative_name}))
