"""
Markdown 文件生成工具模块

generate_markdown 负责把模型整理好的正文写成 Markdown 文件。
落盘前统一用 resolve_path 清洗路径，让产物收敛到当前会话目录，
前端只要看会话目录就能列出本次任务生成的文件。
"""

from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool

from app.api.context import get_session_context, set_session_context
from app.api.monitor import monitor
from app.utils.path_utils import resolve_path


@tool
def generate_markdown(
    content: Annotated[str, "要写入Markdown文档的文本内容"],
    filename: Annotated[str, "Markdown文档的文件名（不包含扩展名或包含.md）"],
    path: Annotated[str, "文件保存的绝对路径"] = "",
) -> str:
    """
    根据提供的文本内容生成 Markdown 文件

    :param content: 要写入 Markdown 文档的完整文本
    :param filename: 输出文件名，缺少 .md 后缀时会自动补全
    :param path: 可选保存路径；通常由运行时工作目录指令约束为相对路径
    :return: 文件生成结果说明
    """
    print(f"[MarkdownTool] 输入保存路径: {path or '当前会话目录'}")
    monitor.report_tool("Markdown文档生成工具", {"写入的文本内容": content})

    if not filename.endswith(".md"):
        filename += ".md"

    # session_dir 由 run_deep_agent 写入 ContextVar，保证文件写入当前会话工作目录
    session_dir = get_session_context()

    # 先把模型传入的 path/filename 合成一个逻辑路径，再交给 resolve_path 做统一清洗
    if path and path != ".":
        full_input_path = str(Path(path) / filename)
    else:
        full_input_path = filename

    full_path_str = resolve_path(full_input_path, session_dir)
    file_path = Path(full_path_str)
    parent_dir = file_path.parent

    # 允许模型指定 session_dir 下的子目录；不存在时自动创建
    if not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

    file_path.write_text(content, encoding="utf-8")
    return f"Markdown文件 '{file_path}' 已成功生成并保存。"


if __name__ == "__main__":
    # 本地调试入口：把会话目录临时固定到 examples/test_docs，验证 Markdown 落盘路径
    # 注意这里故意不用 测试文件.md 这类名字，避免覆盖 examples/test_docs 里已有的测试素材
    test_docs_dir = Path(__file__).parents[2] / "examples" / "test_docs"
    set_session_context(str(test_docs_dir))

    print("=" * 70)
    print("场景①：只给文件名（不带 .md），验证后缀自动补全 + 写入会话目录")
    print(
        generate_markdown.invoke(
            {
                "content": "# 调试入口生成\n\n这是 generate_markdown 本地调试写入的示例内容。\n",
                "filename": "调试生成结果",
            }
        )
    )

    print("=" * 70)
    print("场景②：指定已存在的子目录")
    print(
        generate_markdown.invoke(
            {
                "content": "## 子目录场景\n\n验证 path 参数生效。\n",
                "filename": "调试生成结果",
                "path": "sub_dir",
            }
        )
    )

    print("=" * 70)
    print("场景③：指定不存在的多级子目录，验证自动创建")
    print(
        generate_markdown.invoke(
            {
                "content": "## 多级目录场景\n\n验证 parent_dir.mkdir(parents=True) 生效。\n",
                "filename": "调试生成结果.md",
                "path": "sub_dir/新目录",
            }
        )
    )
