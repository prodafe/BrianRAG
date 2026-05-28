"""API 结构和模型测试"""

import pytest


class _MockLimiter:
    """Mock slowapi.Limiter — both a class and callable (ASGI middleware)"""
    _instance = None

    def __new__(cls, *a, **kw):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kw):
        pass

    def __call__(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return lambda f: f


class TestRequestModels:
    def test_index_request_model(self, monkeypatch):
        monkeypatch.setattr("slowapi.Limiter", _MockLimiter)
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: None)
        from api.main import IndexRequest
        req = IndexRequest(file_paths=["/tmp/test.md"], incremental=True)
        assert req.file_paths == ["/tmp/test.md"]
        assert req.incremental is True

    def test_index_request_default(self, monkeypatch):
        monkeypatch.setattr("slowapi.Limiter", _MockLimiter)
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: None)
        from api.main import IndexRequest
        req = IndexRequest(file_paths=["/tmp/test.md"])
        assert req.incremental is True

    def test_query_request(self, monkeypatch):
        monkeypatch.setattr("slowapi.Limiter", _MockLimiter)
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: None)
        from api.main import QueryRequest
        req = QueryRequest(question="test")
        assert req.question == "test"

    def test_feedback_request(self, monkeypatch):
        monkeypatch.setattr("slowapi.Limiter", _MockLimiter)
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: None)
        from api.main import FeedbackRequest
        req = FeedbackRequest(question="q", answer="test answer", feedback="positive")
        assert req.feedback == "positive"


class TestAPIModuleStructure:
    def test_app_created(self, monkeypatch):
        monkeypatch.setattr("slowapi.Limiter", _MockLimiter)
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: None)
        from api.main import app
        assert app is not None
        assert "BrianRAG" in app.title

    def test_tags_metadata(self, monkeypatch):
        monkeypatch.setattr("slowapi.Limiter", _MockLimiter)
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: None)
        from api.main import tags_metadata
        assert len(tags_metadata) >= 7
        tag_names = [t["name"] for t in tags_metadata]
        assert "Query" in tag_names
        assert "Knowledge Graph" in tag_names

    def test_cors_middleware(self, monkeypatch):
        monkeypatch.setattr("slowapi.Limiter", _MockLimiter)
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: None)
        from api.main import app
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes


class TestPipelineAccess:
    def test_get_pipeline_caching(self, monkeypatch):
        monkeypatch.setattr("slowapi.Limiter", _MockLimiter)
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: None)
        import api.main
        p1 = api.main.get_pipeline()
        p2 = api.main.get_pipeline()
        assert p1 is p2
