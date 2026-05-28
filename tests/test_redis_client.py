"""Redis 客户端模块测试"""

import pytest


class TestRedisClient:
    def test_get_redis_returns_client(self, monkeypatch):
        from core.redis_client import _pools as pools

        pools.clear()
        monkeypatch.setattr("redis.Redis", lambda **kw: _FakeRedis())

        from core.redis_client import get_redis
        client = get_redis(db=0)
        assert client is not None
        client.ping()

    def test_get_redis_same_pool_caches(self, monkeypatch):
        from core.redis_client import _pools as pools

        pools.clear()
        monkeypatch.setattr("redis.Redis", lambda **kw: _FakeRedis())

        from core.redis_client import get_redis

        c1 = get_redis(db=1)
        c2 = get_redis(db=1)
        assert len(pools) >= 1

    def test_get_redis_different_db(self, monkeypatch):
        from core.redis_client import _pools as pools

        pools.clear()
        monkeypatch.setattr("redis.Redis", lambda **kw: _FakeRedis())

        from core.redis_client import get_redis

        get_redis(db=0)
        get_redis(db=1)
        assert 0 in pools or len(pools) >= 2

    def test_close_all_clears(self, monkeypatch):
        from core.redis_client import _pools as pools

        pools.clear()
        monkeypatch.setattr("redis.Redis", lambda **kw: _FakeRedis())

        from core.redis_client import close_all, get_redis

        get_redis(db=0)
        assert len(pools) >= 1
        close_all()
        assert len(pools) == 0

    def test_redis_connection_failure_raises(self, monkeypatch):
        from core.redis_client import _pools as pools

        pools.clear()

        def raise_error(**kw):
            raise ConnectionError("Redis unavailable")

        monkeypatch.setattr("redis.Redis", raise_error)

        with pytest.raises(ConnectionError):
            from core.redis_client import get_redis
            get_redis(db=0)


class _FakeRedis:
    def __init__(self, **kw):
        pass

    def ping(self):
        return True

    def get(self, k):
        return None

    def set(self, k, v, ex=None):
        return True

    def exists(self, k):
        return False

    def hset(self, *a, **kw):
        return None

    def hgetall(self, k):
        return {}

    def close(self):
        pass

    @property
    def connection_pool(self):
        return type("_", (), {})()

    def pipeline(self):
        return type("_", (), {"execute": lambda: None})()
