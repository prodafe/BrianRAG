"""PDF 版式分析器 — 多栏检测、阅读顺序、表格识别、段落层级"""

import logging
import os
import re

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class LayoutBlock:
    __slots__ = ("x0", "y0", "x1", "y1", "text", "block_type", "page_num")

    def __init__(self, x0, y0, x1, y1, text, block_type="text", page_num=0):
        self.x0 = float(x0)
        self.y0 = float(y0)
        self.x1 = float(x1)
        self.y1 = float(y1)
        self.text = text.strip() if text else ""
        self.block_type = block_type  # text / heading / table / image
        self.page_num = page_num

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    @property
    def center_x(self):
        return (self.x0 + self.x1) / 2

    @property
    def font_size(self) -> float:
        return self.height / max(len(self.text.split("\n")), 1) if self.text else 12


def _detect_columns(blocks: list[LayoutBlock], page_width: float, overlap_ratio: float = 0.3) -> int:
    """通过水平投影检测列数"""
    if not blocks or page_width < 400:
        return 1
    x_centers = [b.center_x for b in blocks if b.block_type == "text" and b.width < page_width * 0.9]
    if len(x_centers) < 3:
        return 1

    x_centers.sort()
    gaps = [(x_centers[i + 1] - x_centers[i]) for i in range(len(x_centers) - 1)]
    avg_gap = sum(gaps) / len(gaps) if gaps else 0
    # 显著大于平均间距的 => 列分隔
    col_gaps = [g for g in gaps if g > avg_gap * 1.8 and g > page_width * 0.08]
    return min(len(col_gaps) + 1, 3)


def _sort_by_reading_order(blocks: list[LayoutBlock], num_columns: int, page_width: float) -> list[LayoutBlock]:
    """按阅读顺序排序：从上到下，列内从左到右"""
    if num_columns <= 1:
        return sorted(blocks, key=lambda b: (b.y0, b.x0))

    col_width = page_width / num_columns
    for b in blocks:
        col_idx = min(int(b.center_x / col_width), num_columns - 1)
        b._col = col_idx  # 临时存储列号

    # 按行分组（y 坐标接近的块视为同一行）
    blocks = sorted(blocks, key=lambda b: b.y0)
    rows = []
    current_row = [blocks[0]]
    for b in blocks[1:]:
        prev = current_row[-1]
        if abs(b.y0 - prev.y0) < 15 or (b.y0 < prev.y1 and abs(b.center_x - prev.center_x) < col_width * 0.5):
            current_row.append(b)
        else:
            rows.append(sorted(current_row, key=lambda x: x.x0))
            current_row = [b]
    rows.append(sorted(current_row, key=lambda x: x.x0))

    result = []
    for row in rows:
        result.extend(row)
    return result


def _detect_tables(blocks: list[LayoutBlock], table_min_rows: int = 3) -> list[LayoutBlock]:
    """检测文本块中的表格模式"""
    if len(blocks) < table_min_rows:
        return blocks

    result = []
    i = 0
    while i < len(blocks):
        # 查找潜在的表格行（文本包含 | 或对齐的数字/文本列）
        current = blocks[i]
        text = current.text
        is_table_row = (
            text.count("|") >= 2
            or text.count("\t") >= 2
            or bool(re.match(r"^[\s\d.,%+\-*/=×÷±μ°ΩαβγΔ∑∫√∞≠≤≥]+$", text.split("\n")[0] if text else ""))
        )

        if is_table_row and i + 1 < len(blocks):
            # 检查连续行是否有相似结构
            table_blocks = [current]
            j = i + 1
            while j < len(blocks):
                next_b = blocks[j]
                # 列数一致则视为表格
                if next_b.text.count("|") == text.count("|") or abs(next_b.x0 - current.x0) < 5:
                    table_blocks.append(next_b)
                    j += 1
                else:
                    break
            if len(table_blocks) >= table_min_rows:
                merged = LayoutBlock(
                    x0=min(b.x0 for b in table_blocks),
                    y0=table_blocks[0].y0,
                    x1=max(b.x1 for b in table_blocks),
                    y1=table_blocks[-1].y1,
                    text="|".join(b.text for b in table_blocks),
                    block_type="table",
                    page_num=current.page_num,
                )
                # 保留结构：用 Markdown 表格格式
                lines = [b.text for b in table_blocks]
                if all("|" in l for l in lines):
                    merged.text = "\n".join(lines)
                else:
                    merged.text = "\n".join(f"| {l} |" for l in lines)
                result.append(merged)
                i = j
                continue
        result.append(current)
        i += 1
    return result


def _detect_headings(blocks: list[LayoutBlock], avg_font_size: float) -> list[LayoutBlock]:
    """检测标题：字体显著大于正文 或 粗体短文本"""
    for b in blocks:
        if b.block_type != "text":
            continue
        lines = b.text.split("\n")
        font = b.font_size
        if font > avg_font_size * 1.3 and len(b.text) < 200:
            b.block_type = "heading"
            # 尝试判断标题级别
            if font > avg_font_size * 1.8:
                b.text = f"# {b.text}"
            elif font > avg_font_size * 1.5:
                b.text = f"## {b.text}"
            else:
                b.text = f"### {b.text}"
    return blocks


def _extract_images(page: fitz.Page, page_num: int, output_dir: str) -> list[LayoutBlock]:
    """提取页面中的图片"""
    img_blocks = []
    for img_index, img in enumerate(page.get_images(full=True)):
        try:
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            if not base_image:
                continue
            ext = base_image["ext"]
            if ext not in ("png", "jpeg", "jpg"):
                continue
            img_bytes = base_image["image"]
            filename = f"page{page_num + 1}_img{img_index}.{ext}"
            img_path = os.path.join(output_dir, filename)
            with open(img_path, "wb") as f:
                f.write(img_bytes)

            # 获取图片在页面中的位置
            rects = page.get_image_rects(xref)
            if rects:
                r = rects[0]
                img_blocks.append(
                    LayoutBlock(
                        x0=r.x0,
                        y0=r.y0,
                        x1=r.x1,
                        y1=r.y1,
                        text=f"![图片](images/{filename})",
                        block_type="image",
                        page_num=page_num,
                    )
                )
        except Exception as e:
            logger.debug(f"图片提取失败: {e}")
    return img_blocks


def analyze_pdf_layout(pdf_path: str, image_output_dir: str = "") -> str:
    """
    分析 PDF 版式，返回结构化的 Markdown 文本。

    处理流程：
    1. 提取所有文本块（位置+内容）
    2. 检测列数（多栏文档）
    3. 检测表格（对齐的文本行）
    4. 检测标题（字体大小）
    5. 提取图片
    6. 按阅读顺序重组文本
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF 不存在: {pdf_path}")
        return ""

    doc = fitz.open(pdf_path)
    os.makedirs(image_output_dir, exist_ok=True) if image_output_dir else None

    all_markdown_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_width = page.rect.width
        page_height = page.rect.height

        # 1. 提取文本块
        blocks = []
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block["type"] == 0:  # 文本块
                text_lines = []
                for line in block.get("lines", []):
                    line_text = "".join([span["text"] for span in line.get("spans", [])])
                    if line_text.strip():
                        text_lines.append(line_text.strip())
                if text_lines:
                    blocks.append(
                        LayoutBlock(
                            x0=block["bbox"][0],
                            y0=block["bbox"][1],
                            x1=block["bbox"][2],
                            y1=block["bbox"][3],
                            text="\n".join(text_lines),
                            block_type="text",
                            page_num=page_num,
                        )
                    )

        if not blocks:
            continue

        # 2. 列检测
        num_columns = _detect_columns(blocks, page_width)

        # 3. 标题检测
        fonts = [b.font_size for b in blocks if b.block_type == "text"]
        avg_font = sum(fonts) / len(fonts) if fonts else 12
        blocks = _detect_headings(blocks, avg_font)

        # 4. 表格检测
        blocks = _detect_tables(blocks)

        # 5. 阅读顺序排序
        blocks = _sort_by_reading_order(blocks, num_columns, page_width)

        # 6. 图片提取
        if image_output_dir:
            img_blocks = _extract_images(page, page_num, image_output_dir)
            blocks = _sort_by_reading_order(blocks + img_blocks, num_columns, page_width)

        # 7. 生成 Markdown
        page_md = []
        for b in blocks:
            if b.block_type == "heading" or b.block_type == "table" or b.block_type == "image":
                page_md.append(b.text)
            else:
                page_md.append(b.text)

        if num_columns > 1:
            page_md.insert(0, f"> 第{page_num + 1}页（{num_columns}栏布局）\n")
        all_markdown_parts.extend(page_md)

    doc.close()
    return "\n\n".join(all_markdown_parts)


def pdf_has_text_layer(pdf_path: str) -> bool:
    """判断 PDF 是否有文字层（非纯扫描件）"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) > 200:
                break
        doc.close()
        return len(text.strip()) > 100
    except Exception:
        return False
