# Markdown 转 PDF 底层工具：用 ReportLab 直接生成，不依赖本机 Word
# 职责单一：只负责把已存在的 .md 文件转成 .pdf，不关心报告如何生成、前端如何下载
# reportlab 是可选依赖，try 导入失败时其余名字不会被绑定，静态检查器无法确认，故文件级豁免
# pyright: reportPossiblyUnboundVariable=false
from __future__ import annotations

import html
import logging
import re
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    # 缺少 reportlab 时仍允许模块被导入，方便其它代码正常启动
    SimpleDocTemplate = None

logger = logging.getLogger(__name__)

# 常见系统中文字体路径，命中哪个就嵌入哪个；都找不到才退回 CID 字体
_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方
    "/System/Library/Fonts/Supplemental/Songti.ttc",  # macOS 宋体
    "C:/Windows/Fonts/msyh.ttc",  # Windows 微软雅黑
    "C:/Windows/Fonts/simsun.ttc",  # Windows 宋体
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux 思源黑体
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux 文泉驿
]
# 嵌入真实字体时统一注册为这个名字，样式统一引用它
_FONT_NAME = "STSong-Light"


def convert_md_to_pdf(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """
    将 Markdown 文件转换为 PDF

    :param md_abs_path: Markdown 文件绝对路径
    :param pdf_abs_path: 输出 PDF 文件绝对路径
    :return: 转换结果说明
    """
    if SimpleDocTemplate is None:
        return "缺少依赖库，请安装 reportlab"

    # 读取智能体生成的 Markdown 报告
    with open(md_abs_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # 确保输出目录存在，避免 doc.build 写文件时报路径不存在
    pdf_abs_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _register_fonts()
        doc = SimpleDocTemplate(
            str(pdf_abs_path),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        styles = _build_styles()
        story = _markdown_to_story(md_content, styles)
        doc.build(story)
        return f"成功将 Markdown 转换为 PDF: {pdf_abs_path}"
    except Exception as e:
        logger.exception("Markdown 转 PDF 失败")
        return f"Markdown 转 PDF 失败: {e!s}"


def _register_fonts() -> None:
    """注册中文字体：优先嵌入系统真实字体（任何阅读器都能显示），找不到再退回 CID 字体。"""
    global _FONT_NAME
    for font_path in _FONT_CANDIDATES:
        if Path(font_path).exists():
            # TTC 字体集合取第一个子字体；嵌入后中文不依赖阅读器自带字体
            pdfmetrics.registerFont(TTFont("ChineseFont", font_path, subfontIndex=0))
            # 加粗/斜体标签映射到同一字体，避免 <b>/<i> 找不到对应字重而报错
            pdfmetrics.registerFontFamily(
                "ChineseFont",
                normal="ChineseFont",
                bold="ChineseFont",
                italic="ChineseFont",
                boldItalic="ChineseFont",
            )
            _FONT_NAME = "ChineseFont"
            return
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def _build_styles() -> dict[str, ParagraphStyle]:
    """构建 PDF 各级文本样式，键与 Markdown 元素类型对应。"""
    base = getSampleStyleSheet()
    return {
        # 中文必须用注册好的中文字体，默认 Helvetica 不含中文字形会显示成方块
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=_FONT_NAME,
            fontSize=18,
            leading=24,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=_FONT_NAME,
            fontSize=15,
            leading=20,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName=_FONT_NAME,
            fontSize=12.5,
            leading=17,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=_FONT_NAME,
            fontSize=10.5,
            leading=17,
            spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "Code",
            fontName=_FONT_NAME,  # 代码块可能含中文注释，也用中文字体
            fontSize=9,
            leading=12,
            backColor=colors.HexColor("#F4F4F4"),
            leftIndent=6,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "list": ParagraphStyle(
            "List",
            parent=base["BodyText"],
            fontName=_FONT_NAME,
            fontSize=10.5,
            leading=16,
            leftIndent=18,
            bulletIndent=6,
            spaceAfter=2,
        ),
    }


def _markdown_to_story(md_content: str, styles: dict[str, ParagraphStyle]) -> list:
    """
    把 Markdown 文本解析成 ReportLab story 元素

    story 可以理解成 PDF 页面里的内容队列：
    标题、正文、代码块、表格都会被依次放进去，最后交给 doc.build 生成 PDF。
    """
    story: list = []
    lines = md_content.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]

        # 围栏代码块：收集到结束围栏为止，交给 Preformatted 保留原始排版
        if line.strip().startswith("```"):
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1  # 跳过结束围栏
            story.append(Preformatted("\n".join(code_lines), styles["code"]))
            continue

        stripped = line.strip()

        # 表格：连续以 | 开头的行聚合成一个 Table
        if stripped.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            story.append(_build_table(table_lines, styles))
            continue

        if not stripped:
            index += 1
            continue

        # 分隔线 --- 转成一段空隙
        if re.fullmatch(r"-{3,}", stripped):
            story.append(Spacer(1, 8))
            index += 1
            continue

        # 标题 # ~ ######，超过三级统一按三级样式处理
        heading_match = re.match(r"(#{1,6})\s+(.*)", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            style_key = "h1" if level == 1 else "h2" if level == 2 else "h3"
            story.append(
                Paragraph(_format_inline(heading_match.group(2)), styles[style_key])
            )
            index += 1
            continue

        # 无序列表项，用圆点做项目符号
        if re.match(r"[-*]\s+", stripped):
            content = re.sub(r"[-*]\s+", "", stripped, count=1)
            story.append(
                Paragraph(_format_inline(content), styles["list"], bulletText="•")
            )
            index += 1
            continue

        # 有序列表项，保留原始编号做项目符号
        ordered_match = re.match(r"(\d+)\.\s+(.*)", stripped)
        if ordered_match:
            story.append(
                Paragraph(
                    _format_inline(ordered_match.group(2)),
                    styles["list"],
                    bulletText=f"{ordered_match.group(1)}.",
                )
            )
            index += 1
            continue

        # 普通正文段落
        story.append(Paragraph(_format_inline(stripped), styles["body"]))
        index += 1

    return story


def _build_table(table_lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    """把 Markdown 表格行转换成带网格线的 ReportLab Table。"""
    rows: list[list[str]] = []
    for line in table_lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        # 形如 |---|---| 的分隔行直接跳过
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)

    # 单元格用 Paragraph 承载，否则 Table 里的中文会退回默认字体导致乱码
    data = [
        [Paragraph(_format_inline(cell), styles["body"]) for cell in row]
        for row in rows
    ]
    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFEFEF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _format_inline(text: str) -> str:
    """转义 HTML 并处理行内加粗、斜体、行内代码等简单 Markdown 语法。"""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+?)`", r'<font color="#C7254E">\1</font>', text)
    return text
