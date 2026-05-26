#!/usr/bin/env python
"""
检查评估报告中的指标是否低于阈值
用法: python scripts/check_scores.py --report logs/evaluation/report.json --threshold 0.7 --metric faithfulness
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, help="评估报告 JSON 文件路径")
    parser.add_argument("--metric", default="faithfulness", help="要检查的指标名称")
    parser.add_argument("--threshold", type=float, default=0.7, help="最低可接受分数")
    args = parser.parse_args()

    with open(args.report) as f:
        report = json.load(f)

    score = report.get("scores", {}).get(args.metric)
    if score is None:
        print(f"错误：报告中没有指标 {args.metric}")
        sys.exit(1)

    if score < args.threshold:
        print(f"❌ {args.metric} = {score:.4f} 低于阈值 {args.threshold}")
        sys.exit(1)
    else:
        print(f"✅ {args.metric} = {score:.4f} 符合要求 (≥{args.threshold})")
        sys.exit(0)


if __name__ == "__main__":
    main()
