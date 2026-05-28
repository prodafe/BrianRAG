"""权限与鉴权模块测试"""

import pytest


class TestAuthFunctions:
    def test_has_permission_invalid_key(self, monkeypatch):
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: _FakeRedis())
        monkeypatch.setattr("utils.auth._redis_client", _FakeRedis())
        from utils.auth import has_permission

        ok, tenant = has_permission("", "query:read")
        assert ok is False

    def test_get_required_permissions_query(self):
        from utils.auth import get_required_permissions

        action = get_required_permissions("/api/query", "POST")
        assert isinstance(action, str)
        assert len(action) > 0

    def test_get_required_permissions_index(self):
        from utils.auth import get_required_permissions

        action = get_required_permissions("/api/index", "POST")
        assert isinstance(action, str)

    def test_get_required_permissions_upload(self):
        from utils.auth import get_required_permissions

        action = get_required_permissions("/api/upload", "POST")
        assert isinstance(action, str)

    def test_get_required_permissions_get_request(self):
        from utils.auth import get_required_permissions

        action = get_required_permissions("/api/health", "GET")
        assert isinstance(action, str)

    def test_get_required_permissions_unknown(self):
        from utils.auth import get_required_permissions

        action = get_required_permissions("/api/unknown_endpoint", "GET")
        assert isinstance(action, str)


class TestAuthConstants:
    def test_roles_defined(self):
        from utils.auth import ROLES

        assert isinstance(ROLES, dict)
        assert "admin" in ROLES
        assert "viewer" in ROLES

    def test_role_permissions_defined(self):
        try:
            from utils.auth import ROLE_PERMISSIONS

            assert isinstance(ROLE_PERMISSIONS, dict)
        except ImportError:
            pytest.skip("ROLE_PERMISSIONS not defined")


class TestSessionManager:
    def test_create_session(self, monkeypatch):
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: _FakeRedis())
        from utils.session_manager import SessionManager

        sm = SessionManager()
        result = sm.create_session("test_tenant")
        assert isinstance(result, dict)
        assert "id" in result
        assert len(result["id"]) > 0

    def test_get_session_not_found(self, monkeypatch):
        monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: _FakeRedis())
        from utils.session_manager import SessionManager

        sm = SessionManager()
        data = sm.get_session("nonexistent_session_id")
        assert data is None or data == {}


class _FakeRedis:
    def __init__(self, **kw):
        self._store = {}

    def ping(self):
        return True

    def get(self, k):
        return self._store.get(k)

    def setex(self, k, t, v):
        self._store[k] = v
        return True

    def set(self, k, v, ex=None):
        self._store[k] = v
        return True

    def delete(self, k):
        self._store.pop(k, None)
        return True

    def exists(self, k):
        return k in self._store

    def lrange(self, k, start, end):
        return []

    def rpush(self, k, *vals):
        return 1

    def expire(self, k, ttl):
        return True

    def sadd(self, k, *vals):
        return 1

    def smembers(self, k):
        return set()

    def sismember(self, k, v):
        return False

    def zadd(self, k, mapping):
        return 1

    def zrangebyscore(self, k, min_s, max_s):
        return []

    def hset(self, *a, **kw):
        return None

    def hgetall(self, k):
        return {}

    def hget(self, k, f):
        return None

    def hmset(self, k, mapping):
        return True

    def keys(self, pattern=""):
        return []

    def close(self):
        pass

    @property
    def connection_pool(self):
        return type("_", (), {})()

    def pipeline(self):
        return type("_", (), {"execute": lambda: None})()
