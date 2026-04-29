import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_relevance
from ragas.llms import LangchainLLMWrapper
from langchain_community.chat_models import ChatOllama
from config import Config
from core.rag_pipeline import RAGPipeline


def run_evaluation(test_data_path: str, query_mode: str = "快速模式 (RAG)"):
    """
    运行 RAGAS 评估
    test_data_path: JSONL 文件路径，每行包含 {"question": "...", "ground_truth": "..."}
    query_mode: 使用的问答模式 (快速模式/智能体模式/图谱工作流等)
    """
    # 1. 加载测试数据
    df = pd.read_json(test_data_path, lines=True)
    if "ground_truth" not in df.columns:
        raise ValueError("测试数据必须包含 ground_truth 列")

    # 2. 初始化 RAG 管道
    pipeline = RAGPipeline()

    # 3. 对每个问题生成答案和检索到的上下文
    answers = []
    contexts = []
    for idx, row in df.iterrows():
        question = row["question"]
        if query_mode == "快速模式 (RAG)":
            result = pipeline.query(question)
        elif query_mode == "智能体模式 (Agentic)":
            result = pipeline.agentic_query(question)
        elif query_mode == "图谱工作流 (LangGraph)":
            result = pipeline.graph_query(question)
        else:
            result = pipeline.query(question)
        answers.append(result["answer"])
        # 注意：RAGAS 需要 contexts 是一个列表（每个元素是一个文档片段）
        contexts.append(result["used_chunks"])

    df["answer"] = answers
    df["contexts"] = contexts

    # 4. 配置评估 LLM（使用你的生成模型）
    llm = ChatOllama(model=Config.LLM_MODEL, base_url=Config.OLLAMA_BASE_URL)
    evaluator_llm = LangchainLLMWrapper(llm)

    # 5. 运行评估
    result = evaluate(
        dataset=df,
        metrics=[faithfulness, answer_relevancy, context_relevance],
        llm=evaluator_llm  # 使用封装后的 Wrapper
    )
    print("评估结果:")
    print(result)

    # 6. 保存结果
    result.to_csv("evaluation_results.csv", index=False)
    return result


if __name__ == "__main__":
    # 示例用法：需要先准备 test_data.jsonl
    test_file = "test_data.jsonl"
    if os.path.exists(test_file):
        run_evaluation(test_file, query_mode="快速模式 (RAG)")
    else:
        print(f"请先创建测试数据文件 {test_file}")