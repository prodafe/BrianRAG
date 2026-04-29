import re
from typing import List
from langchain_core.documents import Document


def smart_split_markdown(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """
    智能分割文档：
    - 表格、图片描述等特殊类型保持完整
    - 普通文本：优先按 Markdown 标题分割，其次按空行分割段落
    - 为每个块记录所属章节标题（section）
    - 为表格行记录所属表格块索引（table_block_index）
    """
    final_chunks = []
    current_section = "Root"
    # 用于存储当前段落所属的章节标题（按级别，但简化为最近一个非空标题）
    for doc in documents:
        content = doc.page_content
        # 提取文档中的章节标题（级别1-6）
        lines = content.split('\n')
        for line in lines:
            if line.startswith('#'):
                # 去除 # 号和前后空格
                current_section = line.lstrip('#').strip()
                break

        # 特殊类型（表格、图片描述）不拆分，但依然标注章节
        if doc.metadata.get("type") in ("table", "table_raw", "image_desc"):
            # 添加章节信息
            new_meta = doc.metadata.copy()
            new_meta["section"] = current_section
            final_chunks.append(Document(page_content=doc.page_content, metadata=new_meta))
            continue

        # 普通文本：先按标题分割
        sections = re.split(r'\n(?=#{1,6}\s+)', content)
        if len(sections) == 1:
            sections = re.split(r'\n\s*\n', content)

        current_chunk = ""
        for section in sections:
            if not section.strip():
                continue
            # 尝试将新section加入当前块
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                # 保存当前块
                new_meta = doc.metadata.copy()
                new_meta["section"] = current_section
                final_chunks.append(Document(page_content=current_chunk.strip(), metadata=new_meta))
                # 计算重叠部分
                overlap = current_chunk[-chunk_overlap:] if chunk_overlap > 0 and len(
                    current_chunk) > chunk_overlap else ""
                current_chunk = overlap + "\n\n" + section if overlap else section
            else:
                current_chunk += ("\n\n" if current_chunk else "") + section
        if current_chunk:
            new_meta = doc.metadata.copy()
            new_meta["section"] = current_section
            final_chunks.append(Document(page_content=current_chunk.strip(), metadata=new_meta))

    # 后处理：对于表格行类型的块（type=table_row），记录其所属的原始表格块索引（需要跨块扫描）
    # 注意：这一步需要知道每个 table_row 对应的 table_raw 块。简单做法：在 document_loader 生成 table_raw 和 table_row 时就建立关联，存储 table_block_id。
    # 我们将在 document_loader 中为每个 table_row 添加 metadata["table_block_index"]，这里不再额外处理。
    return final_chunks