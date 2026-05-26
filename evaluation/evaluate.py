#!/usr/bin/env python
"""
RAGAS 离线评估脚本，支持对比模式
用法:
    python evaluate.py                                    # 自动使用同目录下的 test_data.jsonl
    python evaluate.py --test-data my_test.jsonl          # 指定测试文件
    python evaluate.py --compare logs/run1/report.json logs/run2/report.json
"""

import json
import logging
import os
import sys
from typing import Any

import pandas as pd
from datasets import Dataset
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
from tqdm import tqdm

# ---------- 路径处理：确保能导入项目模块 ----------
# 当前脚本所在目录（即 evaluation 文件夹）
script_dir = os.path.dirname(os.path.abspath(__file__))
# 尝试向上查找包含 core 文件夹的目录（项目根目录）
project_root = script_dir
while project_root != os.path.dirname(project_root):
    if os.path.exists(os.path.join(project_root, "core")):
        break
    project_root = os.path.dirname(project_root)
else:
    # 如果没找到，则假设项目根目录是 evaluation 的父目录
    project_root = os.path.dirname(script_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 现在可以导入项目模块
from config import Config
from core.rag_pipeline import RAGPipeline

# ---------- 默认测试数据路径：同目录下的 test_data.jsonl ----------
DEFAULT_TEST_DATA = os.path.join(script_dir, "test_data.jsonl")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_test_data(file_path: str) -> pd.DataFrame:
    """支持 JSONL 或 JSON 数组格式"""
    if file_path.endswith(".jsonl"):
        df = pd.read_json(file_path, lines=True)
    else:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

    if "ground_truth_contexts" not in df.columns:
        df["ground_truth_contexts"] = [[] for _ in range(len(df))]
        logger.info("未发现 ground_truth_contexts 列，将跳过 context_precision/recall")
    if "ground_truth" not in df.columns:
        df["ground_truth"] = ""
        logger.warning("缺少 ground_truth 列，answer_correctness 不可用")
    return df


def run_evaluation(
    test_data_path: str,
    query_mode: str = "快速模式 (RAG)",
    output_dir: str = "logs/evaluation",
    limit: int | None = None,
    metrics: list[str] | None = None,
    skip_missing_contexts: bool = True,
) -> dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)

    df = load_test_data(test_data_path)
    if limit:
        df = df.head(limit)
    logger.info(f"加载测试数据 {len(df)} 条，来源: {test_data_path}")

    pipeline = RAGPipeline()

    answers = []
    contexts = []
    questions = []
    ground_truths = []
    ground_truth_contexts_list = []

    for _idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating"):
        question = row["question"]
        gt = row.get("ground_truth", "")
        gt_ctx = row.get("ground_truth_contexts", [])
        questions.append(question)
        ground_truths.append(gt)
        ground_truth_contexts_list.append(gt_ctx)

        try:
            if query_mode == "快速模式 (RAG)":
                result = pipeline.query(question)
            elif query_mode == "智能体模式 (Agentic)":
                result = pipeline.agentic_query(question)
            elif query_mode == "图谱工作流 (LangGraph)":
                result = pipeline.graph_query(question)
            else:
                result = pipeline.query(question)

            answers.append(result["answer"])
            contexts.append(result.get("used_chunks", []))
        except Exception as e:
            logger.error(f"问题 '{question}' 失败: {e}")
            answers.append("")
            contexts.append([])

    eval_df = pd.DataFrame(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
            "ground_truth_contexts": ground_truth_contexts_list,
        }
    )
    dataset = Dataset.from_pandas(eval_df)

    ollama_base = getattr(Config, "OLLAMA_BASE_URL", "http://localhost:11434")
    evaluator_model = getattr(Config, "EVALUATOR_MODEL", "qwen2.5:1.5b")
    llm = ChatOllama(model=evaluator_model, base_url=ollama_base, temperature=0)
    evaluator_llm = LangchainLLMWrapper(llm)

    # 使用本地 Ollama 嵌入模型，避免依赖 OpenAI
    embedding_model = getattr(Config, "EMBEDDING_MODEL", "bge-m3:latest")
    ollama_emb = OllamaEmbeddings(model=embedding_model, base_url=ollama_base)
    evaluator_embeddings = LangchainEmbeddingsWrapper(ollama_emb)

    available_metrics = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }
    if metrics is None:
        metrics = ["faithfulness", "answer_relevancy"]
        has_gt_ctx = eval_df["ground_truth_contexts"].apply(lambda x: len(x) > 0).any()
        if has_gt_ctx and not skip_missing_contexts:
            metrics.extend(["context_precision", "context_recall"])
        else:
            logger.info("跳过 context_precision/recall（缺少真实上下文或已设置跳过）")
    else:
        metrics = [m for m in metrics if m in available_metrics]

    selected = [available_metrics[m] for m in metrics]

    logger.info(f"开始 RAGAS 评估，指标: {metrics}")
    result = evaluate(dataset=dataset, metrics=selected, llm=evaluator_llm, embeddings=evaluator_embeddings)

    result_df = result.to_pandas()
    csv_path = os.path.join(output_dir, "ragas_scores.csv")
    result_df.to_csv(csv_path, index=False)
    logger.info(f"详细得分保存至 {csv_path}")

    print("\n========== RAGAS 评估摘要 ==========")
    report_scores = {}
    for metric_name in metrics:
        try:
            col = result_df[metric_name]
            mean_score = float(col.mean())
            print(f"{metric_name}: {mean_score:.4f}")
            report_scores[metric_name] = mean_score
        except Exception:
            print(f"{metric_name}: N/A")
            report_scores[metric_name] = 0.0

    report = {
        "query_mode": query_mode,
        "test_data": test_data_path,
        "num_samples": len(df),
        "scores": report_scores,
        "timestamp": pd.Timestamp.now().isoformat(),
    }
    report_path = os.path.join(output_dir, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info(f"汇总报告保存至 {report_path}")

    return result


def compare_evaluations(report1_path: str, report2_path: str):
    """对比两次评估的 report.json"""
    with open(report1_path) as f1, open(report2_path) as f2:
        r1 = json.load(f1)
        r2 = json.load(f2)

    print("\n========== 评估对比 ==========")
    print(f"{'Metric':<20} {'Base':<12} {'New':<12} {'Change':<10}")
    all_metrics = set(r1.get("scores", {}).keys()) | set(r2.get("scores", {}).keys())
    for metric in sorted(all_metrics):
        v1 = r1["scores"].get(metric, 0.0)
        v2 = r2["scores"].get(metric, 0.0)
        change = v2 - v1
        print(f"{metric:<20} {v1:<12.4f} {v2:<12.4f} {change:+.4f}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--test-data", default=DEFAULT_TEST_DATA, help=f"测试数据文件路径（默认: {DEFAULT_TEST_DATA}）")
    parser.add_argument(
        "--mode", default="快速模式 (RAG)", choices=["快速模式 (RAG)", "智能体模式 (Agentic)", "图谱工作流 (LangGraph)"]
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", default="logs/evaluation")
    parser.add_argument(
        "--metrics",
        nargs="+",
        choices=["faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"],
        default=None,
        help="手动指定指标",
    )
    parser.add_argument("--skip-missing-contexts", action="store_true", default=True)
    parser.add_argument("--compare", nargs=2, metavar=("REPORT1", "REPORT2"), help="对比两个评估报告，不需要其他参数")

    args = parser.parse_args()

    if args.compare:
        compare_evaluations(args.compare[0], args.compare[1])
    else:
        if not os.path.exists(args.test_data):
            print(f"错误：测试数据文件不存在: {args.test_data}")
            sys.exit(1)
        run_evaluation(
            test_data_path=args.test_data,
            query_mode=args.mode,
            output_dir=args.output,
            limit=args.limit,
            metrics=args.metrics,
            skip_missing_contexts=args.skip_missing_contexts,
        )
