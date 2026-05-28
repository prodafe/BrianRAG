import logging
import os

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

# 本地模型缓存目录
_HF_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "hf_cache")
os.makedirs(_HF_CACHE, exist_ok=True)


class Reranker:
    def __init__(self, model_name="BAAI/bge-reranker-v2-m3", device=None, use_fp16=False):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model_name = model_name
        # 检查本地缓存路径
        local_path = os.path.join(_HF_CACHE, model_name.replace("/", "_"))
        if os.path.isdir(local_path) and os.path.exists(os.path.join(local_path, "config.json")):
            model_name = local_path
            logger.info(f"从本地缓存加载重排序模型: {local_path}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=_HF_CACHE)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name, cache_dir=_HF_CACHE)
            self.model.to(self.device)
            if use_fp16 and self.device.type == "cuda":
                self.model.half()
            self.model.eval()
            self._loaded = True
            logger.info(f"重排序模型加载成功: {self.model_name}")
        except Exception as e:
            logger.warning(f"重排序模型加载失败 ({model_name}): {e}，重排序将不可用")
            self.tokenizer = None
            self.model = None
            self._loaded = False

    @property
    def is_available(self) -> bool:
        return self._loaded

    def rerank(self, query: str, passages: list[str], top_k: int = 3) -> list[tuple]:
        """
        对检索到的段落进行重排序，返回 (score, index, text) 列表，按分数降序。
        """
        if not passages or not self._loaded:
            return [(0.0, i, passages[i]) for i in range(min(top_k, len(passages)))]
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
