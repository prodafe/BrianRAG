"""Reranker 模块测试"""

import pytest


class TestRerankerUnit:
    def test_rerank_empty_passages(self, monkeypatch):
        monkeypatch.setattr("torch.cuda.is_available", lambda: False)
        monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", lambda *a, **kw: _mock_tokenizer())
        monkeypatch.setattr("transformers.AutoModelForSequenceClassification.from_pretrained", lambda *a, **kw: _mock_model())
        from core.reranker import Reranker

        r = Reranker(model_name="BAAI/bge-reranker-base")
        result = r.rerank("test query", [], top_k=3)
        assert result == []

    def test_is_available_true(self, monkeypatch):
        monkeypatch.setattr("torch.cuda.is_available", lambda: False)
        monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", lambda *a, **kw: _mock_tokenizer())
        monkeypatch.setattr("transformers.AutoModelForSequenceClassification.from_pretrained", lambda *a, **kw: _mock_model())
        from core.reranker import Reranker

        r = Reranker(model_name="BAAI/bge-reranker-base")
        assert r.is_available is True

    def test_model_load_failure_graceful(self, monkeypatch):
        monkeypatch.setattr("torch.cuda.is_available", lambda: False)
        monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", lambda *a, **kw: _raise_oserror())
        from core.reranker import Reranker

        r = Reranker(model_name="BAAI/nonexistent-model")
        assert r.is_available is False
        result = r.rerank("test", ["passage 1", "passage 2"], top_k=2)
        assert len(result) == 2
        assert result[0][2] == "passage 1"

    def test_rerank_returns_correct_order(self, monkeypatch):
        monkeypatch.setattr("torch.cuda.is_available", lambda: False)
        monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", lambda *a, **kw: _mock_tokenizer())
        monkeypatch.setattr("transformers.AutoModelForSequenceClassification.from_pretrained", lambda *a, **kw: _scored_model([2.0, 1.0]))
        from core.reranker import Reranker

        r = Reranker(model_name="mock-model")
        result = r.rerank("test query", ["low relevance", "high relevance"], top_k=2)
        assert result[0][2] == "low relevance"
        assert result[0][0] > result[1][0]

    def test_rerank_score_normalization(self, monkeypatch):
        monkeypatch.setattr("torch.cuda.is_available", lambda: False)
        monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", lambda *a, **kw: _mock_tokenizer())
        monkeypatch.setattr("transformers.AutoModelForSequenceClassification.from_pretrained", lambda *a, **kw: _scored_model([5.0, 0.5, 2.0]))
        from core.reranker import Reranker

        r = Reranker(model_name="mock")
        result = r.rerank("q", ["a", "b", "c"], top_k=3)
        assert result[0][0] == 1.0
        assert result[-1][0] < 1.0

    def test_rerank_truncates_to_top_k(self, monkeypatch):
        monkeypatch.setattr("torch.cuda.is_available", lambda: False)
        monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", lambda *a, **kw: _mock_tokenizer())
        monkeypatch.setattr("transformers.AutoModelForSequenceClassification.from_pretrained", lambda *a, **kw: _scored_model([0.9, 0.8, 0.7, 0.6, 0.5]))
        from core.reranker import Reranker

        r = Reranker(model_name="mock")
        result = r.rerank("q", ["a", "b", "c", "d", "e"], top_k=3)
        assert len(result) == 3


# ── Mock helpers ──

import torch


class _MockTokenizer:
    def __call__(self, pairs, **kw):
        n = len(pairs)
        return {"input_ids": torch.zeros(n, 10, dtype=torch.long),
                "attention_mask": torch.ones(n, 10, dtype=torch.long)}


def _mock_tokenizer():
    return _MockTokenizer()


class _MockModel:
    def __init__(self, scores):
        self._scores = scores
    def to(self, d):
        return self
    def eval(self):
        return self
    def half(self):
        return self
    def __call__(self, **kw):
        s = torch.tensor([[v] for v in self._scores])
        return type("_", (), {"logits": s})()


def _mock_model():
    return _MockModel([0.9, 0.5, 0.3])


def _scored_model(scores):
    return _MockModel(scores)


def _raise_oserror():
    raise OSError("Network unavailable")
