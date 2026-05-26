import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class Reranker:
    def __init__(self, model_name="BAAI/bge-reranker-base", device=None, use_fp16=False):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        if use_fp16 and self.device.type == "cuda":
            self.model.half()
        self.model.eval()

    def rerank(self, query: str, passages: list[str], top_k: int = 3) -> list[tuple]:
        """
        对检索到的段落进行重排序，返回 (score, index, text) 列表，按分数降序。
        """
        if not passages:
            return []
        pairs = [(query, p) for p in passages]
        with torch.no_grad():
            inputs = self.tokenizer(pairs, padding=True, truncation=True, return_tensors="pt", max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            scores = (
                self.model(**inputs)
                .logits.view(
                    -1,
                )
                .float()
            )
            scores = torch.sigmoid(scores).cpu().tolist()

        # Score normalization: scale to [0,1] relative to batch max for better thresholding
        max_s = max(scores) if scores else 1.0
        if max_s > 0:
            scores = [s / max_s for s in scores]

        scored = [(scores[i], i, passages[i]) for i in range(len(passages))]
        scored.sort(reverse=True, key=lambda x: x[0])
        return scored[:top_k]
