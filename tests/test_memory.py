"""Memory 系统测试"""

import pytest


class TestMemoryEntry:
    def test_create_and_serialize(self):
        from core.memory import MemoryEntry

        e = MemoryEntry("role", "backend engineer", category="role", confidence=0.9)
        d = e.to_dict()
        assert d["key"] == "role"
        assert d["value"] == "backend engineer"
        assert d["category"] == "role"

    def test_roundtrip(self):
        from core.memory import MemoryEntry

        e = MemoryEntry("pref", "concise", "preference", 0.8)
        e2 = MemoryEntry.from_dict(e.to_dict())
        assert e2.key == "pref"
        assert e2.value == "concise"


class TestUserMemory:
    def test_remember_and_recall(self, monkeypatch):
        monkeypatch.setattr("core.memory.UserMemory._load", lambda s: setattr(s, "_loaded", True))
        monkeypatch.setattr("core.memory.UserMemory._save", lambda s: None)

        from core.memory import UserMemory

        m = UserMemory("test_user")
        m._loaded = True
        m.remember("name", "Alice", category="fact")
        assert m.recall("name") == "Alice"

    def test_forget(self, monkeypatch):
        monkeypatch.setattr("core.memory.UserMemory._load", lambda s: setattr(s, "_loaded", True))
        monkeypatch.setattr("core.memory.UserMemory._save", lambda s: None)

        from core.memory import UserMemory

        m = UserMemory("test_user")
        m._loaded = True
        m.remember("temp", "value")
        m.forget("temp")
        assert m.recall("temp") is None

    def test_relevant_context_formatted(self, monkeypatch):
        monkeypatch.setattr("core.memory.UserMemory._load", lambda s: setattr(s, "_loaded", True))
        monkeypatch.setattr("core.memory.UserMemory._save", lambda s: None)

        from core.memory import UserMemory

        m = UserMemory("u1")
        m._loaded = True
        m.remember("role", "engineer")
        m.remember("prefers", "short answers", category="preference")

        ctx = m.relevant_context()
        assert "role" in ctx.lower()
        assert "prefers" in ctx.lower()

    def test_clear(self, monkeypatch):
        monkeypatch.setattr("core.memory.UserMemory._load", lambda s: setattr(s, "_loaded", True))
        monkeypatch.setattr("core.memory.UserMemory._save", lambda s: None)
        monkeypatch.setattr("core.memory.UserMemory.redis", property(lambda s: None))

        from core.memory import UserMemory

        m = UserMemory("u2")
        m._loaded = True
        m.remember("key", "value")
        assert m.recall("key") is not None
        m.clear()
        assert m.recall("key") is None

    def test_stats(self, monkeypatch):
        monkeypatch.setattr("core.memory.UserMemory._load", lambda s: setattr(s, "_loaded", True))
        monkeypatch.setattr("core.memory.UserMemory._save", lambda s: None)

        from core.memory import UserMemory

        m = UserMemory("u3")
        m._loaded = True
        m.remember("a", "1", "fact")
        m.remember("b", "2", "preference")
        s = m.stats()
        assert s["user_id"] == "u3"
        assert s["total"] == 2


class TestGetUserMemory:
    def test_caching_same_user(self, monkeypatch):
        monkeypatch.setattr("core.memory.UserMemory._load", lambda s: setattr(s, "_loaded", True))

        from core.memory import get_user_memory, _user_memories

        _user_memories.clear()
        m1 = get_user_memory("alice")
        m2 = get_user_memory("alice")
        assert m1 is m2

    def test_different_users(self, monkeypatch):
        monkeypatch.setattr("core.memory.UserMemory._load", lambda s: setattr(s, "_loaded", True))

        from core.memory import get_user_memory, _user_memories

        _user_memories.clear()
        m1 = get_user_memory("alice")
        m2 = get_user_memory("bob")
        assert m1 is not m2
