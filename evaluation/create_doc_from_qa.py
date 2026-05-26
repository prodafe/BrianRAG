import os
import json

# 获取当前脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, "test_data.jsonl")  # 假设文件在脚本同目录
output_file = os.path.join(script_dir, "document_from_qa.md")

try:
    with open(input_file, "r", encoding="utf-8") as f:
        # 读取 JSONL 内容
        qas = [json.loads(line) for line in f if line.strip()]
except FileNotFoundError:
    print(f"错误：找不到文件 {input_file}")
    print("请确保 test_data.jsonl 与脚本放在同一目录下，或修改 input_file 路径")
    exit(1)

# 生成 Markdown 文档
with open(output_file, "w", encoding="utf-8") as f:
    for idx, qa in enumerate(qas, 1):
        f.write(f"## {idx}. {qa['question']}\n\n")
        f.write(f"{qa['ground_truth']}\n\n")

print(f"已生成文档：{output_file}")
