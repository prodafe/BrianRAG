import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rag_pipeline import RAGPipeline

pipeline = RAGPipeline()

# 加载原始测试数据
with open("data/test.json", encoding="utf-8") as f:
    qas = [json.loads(line) for line in f]

# 对每个问题检索，展示前3个候选块，让用户选择哪些是理想上下文
for idx, qa in enumerate(qas):
    print(f"\n===== 问题 {idx + 1}: {qa['question']} =====")
    result = pipeline.query(qa["question"])
    chunks = result.get("used_chunks", [])[:5]  # 取前5个候选
    for i, chunk in enumerate(chunks):
        print(f"\n候选 {i + 1}: {chunk[:200]}...")
    print("\n请手动输入应该作为理想上下文的候选编号（用逗号分隔，如 1,3），或留空跳过：")
    choice = input().strip()
    if choice:
        indices = [int(x) - 1 for x in choice.split(",") if x.strip()]
        qa["ground_truth_contexts"] = [chunks[i] for i in indices if i < len(chunks)]
    else:
        qa["ground_truth_contexts"] = []

# 保存新文件
with open("data/test_with_contexts.jsonl", "w", encoding="utf-8") as f:
    for qa in qas:
        f.write(json.dumps(qa, ensure_ascii=False) + "\n")

print("\n已生成 data/test_with_contexts.jsonl")
