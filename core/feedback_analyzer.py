import json
from collections import Counter

def analyze_low_quality_feedback(file_path="feedback.jsonl"):
    low_quality = []
    with open(file_path, "r") as f:
        for line in f:
            record = json.loads(line)
            if record["feedback"] == "negative":
                low_quality.append(record)
    # 统计高频问题类型、检索片段长度等
    return low_quality