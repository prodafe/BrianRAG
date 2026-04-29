import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.维护.document_loader import load_single_document
from core.retriever import HybridRetriever

# 1. 加载文档
file_path = "data/AMR常用减震结构设计要点.md"  # 请修改为你的实际路径
docs = load_single_document(file_path)
print(f"原始文档块数: {len(docs)}")
for i, d in enumerate(docs[:3]):
    print(f"块{i}元数据: {d.metadata}")
    print(f"块{i}内容预览: {d.page_content[:200]}...")

# 2. 初始化检索器（会清空旧数据？注意：incremental=False 会全量重建，但这里我们手动调用 load_documents）
ret = HybridRetriever()
# 注意：下面会清空旧索引，如果要保留旧数据请先备份
num = ret.load_documents([file_path], incremental=False, progress_callback=lambda p: print(f"进度 {p*100:.0f}%"))
print(f"索引完成，生成 {num} 个文本块")

# 3. 检查内存中的 chunks
print(f"ret.chunks 数量: {len(ret.chunks)}")
for i, c in enumerate(ret.chunks[:3]):
    print(f"chunk{i}: {c[:100]}...")

# 4. 测试检索
query = "AMR常用减震结构设计要点是什么？"
chunks, idxs = ret.hybrid_search(query, top_k=5)
print(f"检索到 {len(chunks)} 个块")
for c in chunks:
    print(f"结果: {c[:200]}...")