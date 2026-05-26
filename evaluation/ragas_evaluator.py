# evaluation/ragas_evaluator.py
import pandas as pd
from langchain_community.chat_models import ChatOllama
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

from config import Config
from core.rag_pipeline import RAGPipeline


def evaluate_params(top_k: int, alpha: float, score_threshold: float, test_dataset_path: str) -> float:
    """评估一组参数，返回 RAGAS 综合得分（四项指标的平均）"""
    old_top_k = Config.TOP_K
    old_alpha = Config.ALPHA
    old_threshold = Config.SCORE_THRESHOLD

    try:
        Config.TOP_K = top_k
        Config.ALPHA = alpha
        Config.SCORE_THRESHOLD = score_threshold

        pipeline = RAGPipeline()
        df = pd.read_json(test_dataset_path, lines=True)
        answers = []
        contexts = []

        for idx, row in df.iterrows():
            question = row["question"]
            res = pipeline.query(question)
            answers.append(res["answer"])
            contexts.append(res["used_chunks"])
            print(f"  Processed {idx + 1}/{len(df)}: {question[:50]}...")

        df["answer"] = answers
        df["contexts"] = contexts

        from langchain_community.embeddings import OllamaEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper

        llm = ChatOllama(model=Config.EVALUATOR_MODEL, base_url=Config.OLLAMA_BASE_URL)
        evaluator_llm = LangchainLLMWrapper(llm)

        ollama_emb = OllamaEmbeddings(model=Config.EMBEDDING_MODEL, base_url=Config.OLLAMA_BASE_URL)
        evaluator_embeddings = LangchainEmbeddingsWrapper(ollama_emb)

        result = evaluate(
            dataset=df,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
        # 综合得分：四项指标的平均
        score = (
            result["faithfulness"].mean()
            + result["answer_relevancy"].mean()
            + result["context_precision"].mean()
            + result["context_recall"].mean()
        ) / 4
        return score
    finally:
        Config.TOP_K = old_top_k
        Config.ALPHA = old_alpha
        Config.SCORE_THRESHOLD = old_threshold
