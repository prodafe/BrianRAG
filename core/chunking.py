"""父子分块 + Table-aware 切分引擎

Parent-Child Chunking:
  - child_chunk (小) → 精确检索（向量索引）
  - parent_chunk (大) → 上下文窗口（拼接相邻 child，送入 LLM）

Table-aware:
  - 检测 Markdown/HTML 表格，跨 chunk 不切断
"""

import logging
import re
from collections.abc import Sequence

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# 表格检测模式
_TABLE_START = re.compile(r"^\|.*\|$|^\+[-+]+\+$|^\|[-| ]+\|$")
_HTML_TABLE = re.compile(r"<table[\s>]", re.IGNORECASE)


def _is_table_line(line: str) -> bool:
    return bool(_TABLE_START.match(line.strip()) or _HTML_TABLE.search(line))


def _detect_tables(text: str) -> list[tuple[int, int]]:
    """检测文本中的表格区域，返回 [(start_line, end_line), ...]"""
    lines = text.split("\n")
    tables = []
    in_table = False
    table_start = 0
    sep_count = 0  # Markdown 表格头部分隔行计数器

    for i, line in enumerate(lines):
        stripped = line.strip()
        is_sep = bool(re.match(r"^\|[-:| ]+\|$", stripped))

        if _is_table_line(line) or is_sep:
            if not in_table:
                in_table = True
                table_start = i
                sep_count = 1 if is_sep else 0
            elif is_sep and sep_count < 2:
                sep_count += 1
        else:
            if in_table:
                # 只有至少2行（表头+分隔行）才视为有效表格
                if i - table_start >= 2:
                    tables.append((table_start, i - 1))
                in_table = False
                sep_count = 0

    if in_table and len(lines) - table_start >= 2:
        tables.append((table_start, len(lines) - 1))

    return tables


def _table_aware_split(text: str, chunk_size: int) -> list[str]:
    """不切断表格的文本切分。表格内部允许超过 chunk_size。"""
    lines = text.split("\n")
    tables = _detect_tables(text)
    table_line_set = set()
    for s, e in tables:
        for i in range(s, e + 1):
            table_line_set.add(i)

    chunks = []
    current = ""
    current_lines = 0
    i = 0

    while i < len(lines):
        line = lines[i]

        if i in table_line_set:
            if current:
                chunks.append(current.strip())
                current = ""
                current_lines = 0

            # Collect complete table
            table_start = i
            while i < len(lines) and i in table_line_set:
                i += 1
            chunk = "\n".join(lines[table_start:i])
            if chunk.strip():
                chunks.append(chunk.strip())
            continue

        new_text = current + ("\n" if current else "") + line
        if len(new_text) > chunk_size and current_lines >= 3:
            chunks.append(current.strip())
            current = line
            current_lines = 1
        else:
            current = new_text
            current_lines += 1
        i += 1

    if current.strip():
        chunks.append(current.strip())

    return chunks


def parent_child_chunk(
    documents: list[Document],
    child_size: int = 400,
    child_overlap: int = 50,
    parent_window: int = 4,
) -> tuple[list[Document], list[Document]]:
    """父子分块。

    Returns:
        child_docs: 子块（用于向量索引）- 小粒度、高精度检索
        parent_docs: 父块（用于上下文）- 拼接相邻子块，保留完整语义

    每个 parent 包含 parent_window 个相邻 child 的内容，
    父块之间 overlap 为 parent_window // 2。
    """
    child_docs = []
    parent_docs = []

    for doc in documents:
        text = doc.page_content
        meta = doc.metadata.copy()

        # Table-aware 切分子块
        child_texts = _table_aware_split(text, child_size)

        # 生成子块 Document
        for i, ct in enumerate(child_texts):
            c_meta = meta.copy()
            c_meta["chunk_type"] = "child"
            c_meta["child_index"] = i
            c_meta["total_children"] = len(child_texts)
            child_docs.append(Document(page_content=ct, metadata=c_meta))

        # 生成父块 Document（拼接相邻子块）
        stride = max(parent_window // 2, 1)
        for i in range(0, len(child_texts), stride):
            start = max(0, i - stride)
            end = min(len(child_texts), i + parent_window)
            parent_text = "\n\n".join(child_texts[start:end])
            p_meta = meta.copy()
            p_meta["chunk_type"] = "parent"
            p_meta["child_range"] = f"{start}-{end - 1}"
            p_meta["child_count"] = end - start
            parent_docs.append(Document(page_content=parent_text, metadata=p_meta))

    return child_docs, parent_docs


def build_parent_context(
    child_indices: Sequence[int],
    child_docs: list[Document],
    child_to_parent: dict[int, int] | None = None,
) -> list[str]:
    """给定子块索引，返回对应的父块上下文"""
    parent_texts = []
    seen = set()

    for idx in child_indices:
        if child_to_parent and idx in child_to_parent:
            p_idx = child_to_parent[idx]
        else:
            p_idx = idx // 2  # 默认每2个子块对应1个父块
        if p_idx not in seen:
            seen.add(p_idx)
            parent_texts.append(child_docs[idx].page_content if idx < len(child_docs) else "")

    return parent_texts
