"""RAGAS 自动化回归测试 — 一键评估 + 历史对比

Usage:
    python evaluation/ragas_runner.py          # 运行评估
    python evaluation/ragas_runner.py --compare # 对比历史结果
"""

import json
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

logger = logging.getLogger(__name__)

# ── 内置评估问题集 ──
_DEFAULT_QA_PAIRS = [
    {"question": "减震器结构设计要点是什么", "reference": "减震器结构设计需考虑阻尼比、固有频率和最大行程三个核心参数。"},
    {"question": "驱动轮与地面的作用力公式", "reference": "驱动轮与地面的摩擦力公式为 F = μ·N，其中 μ 为摩擦系数，N 为正压力。"},
    {"question": "弹簧预压力的作用是什么", "reference": "弹簧预压力的作用是保证弹簧在初始状态就具有一定的压缩量，防止松动并提高稳定性。"},
    {"question": "Flex调试前需要准备什么", "reference": "Flex 调试前需要确保编译环境正确配置，包括 SDK 路径和调试器设置。"},
]


def run_ragas_eval(
    pipeline,
    qa_pairs: list[dict] | None = None,
    output_dir: str = "evaluation/results",
) -> dict:
    """运行 RAGAS 评估，返回指标"""
    qa = qa_pairs or _DEFAULT_QA_PAIRS

    results = []
    total_start = time.perf_counter()

    for i, pair in enumerate(qa):
        q = pair["question"]
        ref = pair.get("reference", "")
        t0 = time.perf_counter()

        try:
            resp = pipeline.query(q, history=None)
            answer = resp.get("answer", "")

            # Faithfulness: 检查答案是否可从上下文中推断
            contexts = resp.get("context", resp.get("used_chunks", []))
            faithfulness = _estimate_faithfulness(answer, contexts)

            # Answer Relevancy: 检查答案与问题的相关性
            relevancy = _estimate_relevancy(q, answer)

            # Context Recall: 检查上下文覆盖率
            recall = _estimate_recall(ref, contexts) if ref else 0.5

            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            results.append({
                "question": q, "answer": answer[:200], "reference": ref[:200],
                "faithfulness": round(faithfulness, 3), "relevancy": round(relevancy, 3),
                "context_recall": round(recall, 3), "latency_ms": elapsed,
            })

        except Exception as e:
            logger.error(f"Eval failed for '{q}': {e}")
            results.append({"question": q, "error": str(e)})

    total_time = round(time.perf_counter() - total_start, 1)

    # Aggregate scores
    valid = [r for r in results if "faithfulness" in r]
    agg = {
        "faithfulness": round(sum(r["faithfulness"] for r in valid) / len(valid), 3) if valid else 0,
        "relevancy": round(sum(r["relevancy"] for r in valid) / len(valid), 3) if valid else 0,
        "context_recall": round(sum(r["context_recall"] for r in valid) / len(valid), 3) if valid else 0,
        "total_time_s": total_time, "queries": len(qa), "errors": len(results) - len(valid),
    }

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"ragas_{ts}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "aggregate": agg, "details": results}, f, indent=2, ensure_ascii=False)

    # Update latest symlink
    latest_path = os.path.join(output_dir, "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "aggregate": agg, "details": results}, f, indent=2, ensure_ascii=False)

    logger.info(f"RAGAS eval complete: {agg}")
    logger.info(f"Results saved to {output_path}")
    return agg


def _estimate_faithfulness(answer: str, contexts: list[str]) -> float:
    """启发式 Faithfulness 评估 — 检查答案中的声明是否可在上下文中找到"""
    if not contexts:
        return 0.0
    ctx_text = " ".join(contexts).lower()
    answer_lower = answer.lower()

    # Split answer into sentences
    sentences = [s.strip() for s in answer.replace("。", ".").split(".") if len(s.strip()) > 10]
    if not sentences:
        return 0.5

    # Count sentences with keyword overlap in contexts
    supported = 0
    for sent in sentences:
        words = [w for w in sent.lower().split() if len(w) > 1]
        if not words:
            continue
        overlap = sum(1 for w in words if w in ctx_text)
        if overlap / len(words) > 0.3:
            supported += 1

    return round(supported / len(sentences), 3)


def _estimate_relevancy(question: str, answer: str) -> float:
    """启发式 Answer Relevancy 评估"""
    if not answer:
        return 0.0

    # Extract keywords from question
    q_words = set(question.lower().split())
    a_words = set(answer.lower().split())

    # Jaccard similarity
    intersection = q_words & a_words
    union = q_words | a_words
    return round(len(intersection) / len(union), 3) if union else 0.0


def _estimate_recall(reference: str, contexts: list[str]) -> float:
    """启发式 Context Recall 评估"""
    if not contexts or not reference:
        return 0.0
    ref_words = set(reference.lower().split())
    ctx_text = " ".join(contexts).lower()

    recalled = sum(1 for w in ref_words if w in ctx_text)
    return round(recalled / len(ref_words), 3) if ref_words else 0.0


def compare_results(results_dir: str = "evaluation/results") -> list[dict]:
    """对比历史评估结果"""
    if not os.path.isdir(results_dir):
        return []

    files = sorted([f for f in os.listdir(results_dir) if f.startswith("ragas_") and f.endswith(".json")])
    history = []
    for f in files:
        with open(os.path.join(results_dir, f), encoding="utf-8") as fh:
            data = json.load(fh)
            agg = data.get("aggregate", {})
            history.append({"timestamp": data.get("timestamp", f), **agg})

    if len(history) >= 2:
        latest = history[-1]
        previous = history[-2]
        print("\n═══ RAGAS 趋势对比 ═══")
        for metric in ["faithfulness", "relevancy", "context_recall"]:
            curr = latest.get(metric, 0)
            prev = previous.get(metric, 0)
            delta = round((curr - prev) * 100, 1)
            direction = "↑" if delta > 0 else "↓" if delta < 0 else "→"
            print(f"  {metric}: {prev:.3f} → {curr:.3f} ({direction}{abs(delta)}%)")

    return history


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    from core.rag_pipeline import RAGPipeline

    pipeline = RAGPipeline()
    agg = run_ragas_eval(pipeline)

    print("\n═══ RAGAS Evaluation Results ═══")
    print(f"  Faithfulness:  {agg['faithfulness']:.3f}")
    print(f"  Relevancy:     {agg['relevancy']:.3f}")
    print(f"  Context Recall:{agg['context_recall']:.3f}")
    print(f"  Total time:    {agg['total_time_s']}s")

    # Compare with history
    history = compare_results()
