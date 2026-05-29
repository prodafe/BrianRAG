"""Deep Document Parser — 结构化文档深度解析引擎

对标 RAGFlow 95 分文档解析能力：
- 标题层级保留 (H1-H6)
- 表格语义提取（列名+统计）
- Excel/CSV 多 sheet 结构化解析
- 代码块语言检测与保留
- 图片 AI 描述生成（Ollama vision）
- 数学公式保留
- 列表结构保留
- 电子邮件 (.eml) 支持
"""

from __future__ import annotations

import csv
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from email.parser import Parser as EmailMessageParser

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# ── 结构化元素模型 ──


@dataclass
class StructuredElement:
    """文档结构化元素"""

    type: str  # heading, paragraph, table, code, image, list, formula, hr
    content: str
    level: int = 0  # heading level (1-6)
    metadata: dict = field(default_factory=dict)


# ── Markdown 深度解析 ──


class MarkdownDeepParser:
    """Markdown 结构化解析器，保留标题层级、表格、代码、公式"""

    HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    CODE_BLOCK = re.compile(r"```(\w+)?\n([\s\S]*?)```")
    TABLE_LINE = re.compile(r"^\|(.+)\|$")
    TABLE_SEP = re.compile(r"^\|[\s\-:|]+\|$")
    FORMULA = re.compile(r"\$\$([\s\S]*?)\$\$|\$(.+?)\$")
    IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.+)$")
    HR = re.compile(r"^(\*{3,}|-{3,}|_{3,})$")

    def parse(self, text: str, source: str = "") -> list[StructuredElement]:
        """解析 markdown 为结构化元素列表"""
        elements: list[StructuredElement] = []
        lines = text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 空行
            if not stripped:
                i += 1
                continue

            # 代码块
            if stripped.startswith("```"):
                code_match = re.match(r"```(\w*)$", stripped)
                lang = (code_match.group(1) if code_match else "") or ""
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # skip closing ```
                elements.append(
                    StructuredElement(
                        type="code",
                        content="\n".join(code_lines),
                        metadata={"language": lang, "source": source},
                    )
                )
                continue

            # 水平线
            if self.HR.match(stripped):
                elements.append(StructuredElement(type="hr", content=stripped, metadata={"source": source}))
                i += 1
                continue

            # 标题
            heading_match = self.HEADING.match(stripped)
            if heading_match:
                level = len(heading_match.group(1))
                elements.append(
                    StructuredElement(
                        type="heading",
                        content=heading_match.group(2).strip(),
                        level=level,
                        metadata={"source": source, "level": level},
                    )
                )
                i += 1
                continue

            # 表格（收集连续的表行）
            if self.TABLE_LINE.match(stripped):
                table_lines = []
                while i < len(lines) and (self.TABLE_LINE.match(lines[i].strip()) or self.TABLE_SEP.match(lines[i].strip())):
                    if not self.TABLE_SEP.match(lines[i].strip()):
                        table_lines.append(lines[i].strip())
                    i += 1
                if len(table_lines) >= 2:
                    elements.append(
                        StructuredElement(
                            type="table",
                            content="\n".join(table_lines),
                            metadata={"source": source, "rows": len(table_lines) - 1, "format": "markdown"},
                        )
                    )
                continue

            # 列表（收集连续的列表项）
            list_match = self.LIST_ITEM.match(stripped)
            if list_match:
                list_items = []
                indent = len(list_match.group(1))
                while i < len(lines):
                    li_match = self.LIST_ITEM.match(lines[i].strip())
                    if not li_match:
                        break
                    if li_match and abs(len(li_match.group(1)) - indent) <= 2:
                        list_items.append(li_match.group(3).strip())
                        i += 1
                    else:
                        break
                elements.append(
                    StructuredElement(
                        type="list",
                        content="\n".join(f"- {item}" for item in list_items),
                        metadata={"source": source, "items": len(list_items)},
                    )
                )
                continue

            # 公式块
            if stripped.startswith("$$"):
                formula_lines = [stripped]
                i += 1
                while i < len(lines) and not lines[i].strip().endswith("$$"):
                    formula_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    formula_lines.append(lines[i])
                    i += 1
                elements.append(
                    StructuredElement(type="formula", content="\n".join(formula_lines), metadata={"source": source, "display": True})
                )
                continue

            # 图片（单独一行）
            img_match = self.IMAGE.match(stripped)
            if img_match:
                alt = img_match.group(1) or "image"
                url = img_match.group(2)
                elements.append(
                    StructuredElement(type="image", content=url, metadata={"source": source, "alt": alt, "url": url})
                )
                i += 1
                continue

            # 普通段落（收集连续的非特殊行）
            para_lines = []
            while i < len(lines):
                s = lines[i].strip()
                if not s:
                    break
                if any(
                    pat.match(s)
                    for pat in (self.HEADING, self.TABLE_LINE, self.HR)
                ) or s.startswith("```"):
                    break
                if self.LIST_ITEM.match(s):
                    break
                para_lines.append(lines[i])
                i += 1
            para_text = " ".join(p.strip() for p in para_lines if p.strip())
            if para_text:
                elements.append(StructuredElement(type="paragraph", content=para_text, metadata={"source": source}))

        return elements

    def to_markdown(self, elements: list[StructuredElement]) -> str:
        """将结构化元素转回 markdown，保留层级"""
        result = []
        for elem in elements:
            prefix = ""
            if elem.type == "heading":
                prefix = "#" * min(elem.level, 6) + " "
            elif elem.type == "list":
                result.append(elem.content)
                continue
            elif elem.type == "code":
                lang = elem.metadata.get("language", "")
                result.append(f"```{lang}\n{elem.content}\n```")
                continue
            elif elem.type == "table":
                result.append(elem.content)
                continue
            elif elem.type == "hr":
                result.append("---")
                continue
            elif elem.type == "formula":
                result.append(elem.content)
                continue
            elif elem.type == "image":
                alt = elem.metadata.get("alt", "")
                url = elem.metadata.get("url", elem.content)
                result.append(f"![{alt}]({url})")
                continue
            result.append(f"{prefix}{elem.content}")
        return "\n\n".join(result)


# ── Excel/CSV 结构化解析 ──


class SpreadsheetDeepParser:
    """Excel/CSV 结构化解析，保留 sheet 名称、列名、统计数据"""

    def parse_csv(self, file_path: str, source: str = "") -> list[StructuredElement]:
        """解析 CSV 文件"""
        try:
            import pandas as pd

            df = pd.read_csv(file_path, nrows=1000)
            return self._dataframe_to_elements(df, source, os.path.basename(file_path))
        except Exception as e:
            logger.debug(f"Pandas CSV parse failed, falling back to csv module: {e}")

        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return []
        return [self._csv_rows_to_element(rows, source, os.path.basename(file_path))]

    def parse_excel(self, file_path: str, source: str = "") -> list[StructuredElement]:
        """解析 Excel 文件，每个 sheet 一个元素"""
        try:
            import pandas as pd

            xl = pd.ExcelFile(file_path)
            elements = []
            for sheet_name in xl.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=1000)
                elements.extend(self._dataframe_to_elements(df, source, f"{os.path.basename(file_path)} [{sheet_name}]"))
            return elements
        except Exception as e:
            logger.warning(f"Excel 结构化解析失败: {e}")
            return [StructuredElement(type="paragraph", content=f"[Excel file: {os.path.basename(file_path)}]", metadata={"source": source})]

    def _dataframe_to_elements(self, df, source: str, label: str) -> list[StructuredElement]:
        elements = []
        # Sheet summary
        cols = list(df.columns)
        shape = df.shape
        dtypes_summary = ", ".join(f"{c}({str(d).replace('object', 'text')})" for c, d in zip(cols, df.dtypes, strict=False))

        header = f"## {label}\n{table_summary(shape, cols)}"

        # Column statistics for numeric columns
        numeric_stats = []
        for col in df.select_dtypes(include=["number"]).columns[:10]:
            s = df[col].dropna()
            if len(s) > 0:
                numeric_stats.append(
                    f"- **{col}**: min={s.min():.2f}, max={s.max():.2f}, avg={s.mean():.2f}, median={s.median():.2f}"
                )

        # Markdown table (first 50 rows)
        table_md = df.head(50).to_markdown(index=False) if len(df) > 0 else "(empty)"

        content = f"{header}\n## Column Types\n{dtypes_summary}\n"
        if numeric_stats:
            content += f"\n## Statistics\n{chr(10).join(numeric_stats)}\n"
        content += f"\n## Data (first 50 of {shape[0]} rows)\n{table_md}"

        elements.append(
            StructuredElement(
                type="table",
                content=content,
                metadata={
                    "source": source,
                    "sheet": label,
                    "rows": shape[0],
                    "columns": shape[1],
                    "column_names": cols,
                    "format": "excel" if label.endswith("]") else "csv",
                },
            )
        )
        return elements

    def _csv_rows_to_element(self, rows: list[list[str]], source: str, label: str) -> StructuredElement:
        if not rows:
            return StructuredElement(type="paragraph", content=f"[Empty CSV: {label}]", metadata={"source": source})
        header = rows[0]
        body_rows = rows[1:51]
        md_lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
        for row in body_rows:
            padded = row + [""] * (len(header) - len(row))
            md_lines.append("| " + " | ".join(padded[:len(header)]) + " |")
        content = f"## {label}\n" + "\n".join(md_lines)
        if len(rows) > 51:
            content += f"\n\n*(+{len(rows) - 51} more rows)*"
        return StructuredElement(
            type="table", content=content, metadata={"source": source, "rows": len(rows) - 1, "columns": len(header), "format": "csv"},
        )


def table_summary(shape: tuple, columns: list[str]) -> str:
    return f"*{shape[0]} rows × {shape[1]} columns* — {', '.join(columns[:15])}" + (", ..." if len(columns) > 15 else "")


# ── Email 解析 ──


class EmailParser:
    """解析 .eml 文件"""

    def parse(self, file_path: str, source: str = "") -> list[StructuredElement]:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            msg = EmailMessageParser().parse(f)

        elements = []
        subject = msg.get("Subject", "(no subject)")
        sender = msg.get("From", "unknown")
        date_str = msg.get("Date", "unknown")
        recipients = msg.get("To", "")

        header = f"## Email: {subject}\n**From**: {sender}\n**To**: {recipients}\n**Date**: {date_str}"
        elements.append(StructuredElement(type="heading", content=f"Email: {subject}", level=2, metadata={"source": source, "from": sender, "to": recipients, "date": date_str}))

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="replace")
                elif ctype == "text/html":
                    try:
                        from html.parser import HTMLParser

                        class Stripper(HTMLParser):
                            def __init__(self):
                                super().__init__()
                                self.text = ""

                            def handle_data(self, data):
                                self.text += data + " "

                        s = Stripper()
                        payload = part.get_payload(decode=True)
                        if payload:
                            s.feed(payload.decode("utf-8", errors="replace"))
                            body += s.text
                    except Exception as e:
                        logger.debug(f"Email HTML body parse failed: {e}")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")

        if body.strip():
            elements.append(StructuredElement(type="paragraph", content=body.strip()[:5000], metadata={"source": source}))

        return elements


# ── 图片 AI 描述 ──


class ImageDescriber:
    """使用 Ollama vision 模型为文档中的图片生成描述"""

    def __init__(self):
        self._cache: dict[str, str] = {}
        self._cache_file = ""

    def describe(self, image_path: str, model: str = "qwen2.5vl:7b") -> str | None:
        """为图片生成中文描述，带缓存"""
        if not os.path.exists(image_path):
            return None

        with open(image_path, "rb") as f:
            img_hash = hashlib.md5(f.read()).hexdigest()

        if img_hash in self._cache:
            return self._cache[img_hash]

        try:
            import base64

            import ollama

            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            response = ollama.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": "请用中文详细描述这张图片的内容，包括关键信息、数据、图表类型等。只输出描述，不要额外解释。",
                        "images": [img_b64],
                    }
                ],
                options={"num_predict": 256},
            )
            desc = response["message"]["content"].strip()
            self._cache[img_hash] = desc
            return desc
        except Exception as e:
            logger.warning(f"图片 AI 描述失败: {e}")
            return None


# ── 增强文档生成 ──


def generate_enhanced_docs(
    file_path: str, elements: list[StructuredElement], image_describer: ImageDescriber | None = None
) -> list[Document]:
    """根据结构化元素生成增强版 LangChain Documents

    策略：
    - 标题作为 section 锚点，传递到相邻段落
    - 表格保留结构化 markdown + 统计摘要
    - 图片尝试 AI 描述
    - 代码块保留语言标记
    """
    from config import Config

    docs = []
    current_section = ""  # 当前所在章节标题
    current_chunk = ""
    chunk_size = getattr(Config, "CHUNK_SIZE", 800)

    for elem in elements:
        text = ""

        if elem.type == "heading":
            current_section = elem.content
            prefix = "#" * min(elem.level, 6) + " "
            text = prefix + elem.content
        elif elem.type == "paragraph":
            prefix = f"[{current_section}] " if current_section else ""
            text = prefix + elem.content
        elif elem.type == "code":
            lang = elem.metadata.get("language", "")
            prefix = f"[{current_section}] " if current_section else ""
            text = f"{prefix}```{lang}\n{elem.content}\n```"
        elif elem.type == "table":
            prefix = f"[{current_section}] " if current_section else ""
            text = prefix + elem.content
        elif elem.type == "image":
            prefix = f"[{current_section}] " if current_section else ""
            url = elem.metadata.get("url", elem.content)
            alt = elem.metadata.get("alt", "image")
            if image_describer:
                try:
                    desc = image_describer.describe(url)
                    text = f"{prefix}[Image: {alt}]\nDescription: {desc}" if desc else f"{prefix}[Image: {alt}]"
                except Exception:
                    text = f"{prefix}[Image: {alt}]"
            else:
                text = f"{prefix}[Image: {alt}]"
        elif elem.type == "list" or elem.type == "formula":
            prefix = f"[{current_section}] " if current_section else ""
            text = prefix + elem.content
        elif elem.type == "hr":
            if current_chunk:
                docs.append(
                    Document(
                        page_content=current_chunk.strip(),
                        metadata={"source": file_path, "type": "deep_parsed", "section": current_section},
                    )
                )
                current_chunk = ""
            continue
        else:
            continue

        if len(current_chunk) + len(text) > chunk_size and current_chunk:
            docs.append(
                Document(
                    page_content=current_chunk.strip(),
                    metadata={"source": file_path, "type": "deep_parsed", "section": current_section},
                )
            )
            current_chunk = text
        else:
            current_chunk += ("\n\n" if current_chunk else "") + text

    if current_chunk.strip():
        docs.append(
            Document(
                page_content=current_chunk.strip(),
                metadata={"source": file_path, "type": "deep_parsed", "section": current_section},
            )
        )

    return docs


# ── 统一入口 ──


def deep_parse(file_path: str) -> list[Document]:
    """统一深度解析入口：自动检测文件类型并调用相应解析器"""
    ext = os.path.splitext(file_path)[1].lower()
    source = file_path

    try:
        if ext == ".md":
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            parser = MarkdownDeepParser()
            elements = parser.parse(content, source)
            image_describer = ImageDescriber()
            return generate_enhanced_docs(file_path, elements, image_describer)

        elif ext in (".csv",):
            parser = SpreadsheetDeepParser()
            elements = parser.parse_csv(file_path, source)
            return generate_enhanced_docs(file_path, elements)

        elif ext in (".xlsx", ".xls"):
            parser = SpreadsheetDeepParser()
            elements = parser.parse_excel(file_path, source)
            return generate_enhanced_docs(file_path, elements)

        elif ext in (".eml",):
            parser = EmailParser()
            elements = parser.parse(file_path, source)
            return generate_enhanced_docs(file_path, elements)

        elif ext in (".txt", ".py", ".json", ".sh", ".yml", ".yaml", ".toml", ".ini", ".cfg"):
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            if not content.strip():
                return []
            return [
                Document(
                    page_content=f"[{os.path.basename(file_path)}]\n{content[:5000]}",
                    metadata={"source": source, "type": "text_deep_parsed", "file_type": ext},
                )
            ]

        else:
            return []
    except Exception as e:
        logger.error(f"Deep parse failed for {file_path}: {e}")
        return []
