"""
Markdown 转 PDF 工具模块

convert_md_to_pdf 把已经写好的 Markdown 文件转换成 PDF。
它不重新组织内容，只负责确认输入文件、决定输出路径，再把排版细节交给
app/utils/word_converter.py 里的 ReportLab 转换链路。
"""

import logging
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool

from app.api.context import get_session_context, set_session_context
from app.api.monitor import monitor
from app.utils.path_utils import resolve_path

# 底层转换函数在本项目里叫 convert_md_to_pdf，与下面的工具函数同名
# 用别名导入，既避免名字冲突，又让调用点语义更明确
from app.utils.word_converter import convert_md_to_pdf as convert_md_to_pdf_via_word

logger = logging.getLogger(__name__)


@tool
def convert_md_to_pdf(
    md_filename: Annotated[str, "要转换的Markdown文档路径（包含.md后缀）"],
    pdf_filename: Annotated[
        str | None, "输出的PDF文件路径（可选，默认与源文件同名）"
    ] = None,
) -> str:
    """
    将当前会话目录中的 Markdown 文档转换为 PDF

    :param md_filename: Markdown 文件名或相对路径，缺少后缀时会自动补为 .md
    :param pdf_filename: 可选 PDF 输出文件名；不传时与 Markdown 同名
    :return: 转换结果说明
    """
    monitor.report_tool("Markdown转PDF工具")

    try:
        # 输入路径必须先落到当前会话目录，避免模型传入任意系统路径
        session_dir = get_session_context()
        md_path = Path(md_filename).with_suffix(".md")
        md_abs_path = Path(resolve_path(str(md_path), session_dir))

        if not md_abs_path.exists():
            return f"错误：文件不存在 {md_abs_path}"

        # 未指定 PDF 文件名时，默认与源 Markdown 同目录同名
        if pdf_filename:
            pdf_path = Path(pdf_filename).with_suffix(".pdf")
            pdf_abs_path = Path(resolve_path(str(pdf_path), session_dir))
        else:
            pdf_abs_path = md_abs_path.with_suffix(".pdf")

        # PDF 版式、中文字体和 Markdown 解析细节都封装在底层转换模块中
        return convert_md_to_pdf_via_word(md_abs_path, pdf_abs_path)

    except Exception as e:
        # 转换失败返回中文提示，避免中断 Agent 执行链路
        # logger.exception 自带异常堆栈，消息里不用再拼一次 e
        logger.exception("Markdown 转 PDF 工具执行失败")
        return f"转换失败: {e!s}"


# 调试入口用的示例正文：覆盖标题、列表、表格、代码块和行内样式
_SAMPLE_MARKDOWN = """# 药品销售分析报告

## 一、核心结论

本报告基于**销售记录表**统计，覆盖华北、华东、华南三个区域。

## 二、区域销售额

| 区域 | 销售额 | 占比 |
| --- | --- | --- |
| 华东区 | 84900 | 55% |
| 华北区 | 17250 | 11% |
| 华南区 | 28500 | 18% |

## 三、要点清单

- 华东区贡献最高，主要来自上海华山医院
- 华南区次之，广州与深圳两地接近
- 华北区客单价偏低，但销量稳定

## 四、示例查询

```sql
SELECT region, SUM(total_amount)
FROM sales_records
GROUP BY region;
```

---

以上数据来自 `sales_records` 表。
"""


if __name__ == "__main__":
    # 本地调试入口：把会话目录固定到 examples/test_docs，先造 Markdown 再转 PDF
    # 文件名特意避开 测试文件.md 等已有素材，避免覆盖
    test_docs_dir = Path(__file__).parents[2] / "examples" / "test_docs"
    set_session_context(str(test_docs_dir))

    sample_md = test_docs_dir / "调试生成报告.md"
    sample_md.write_text(_SAMPLE_MARKDOWN, encoding="utf-8")
    print(f"已准备示例 Markdown：{sample_md}")

    print("=" * 70)
    print("场景①：不传 pdf_filename，验证与源文件同名")
    print(convert_md_to_pdf.invoke({"md_filename": "调试生成报告.md"}))

    print("=" * 70)
    print("场景②：传入 pdf_filename，验证输出名可控")
    print(
        convert_md_to_pdf.invoke(
            {"md_filename": "调试生成报告", "pdf_filename": "指定名称报告"}
        )
    )

    print("=" * 70)
    print("场景③：源文件不存在，验证错误提示")
    print(convert_md_to_pdf.invoke({"md_filename": "不存在的报告.md"}))
