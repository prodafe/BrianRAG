"""用户级 Memory 系统 — 跨会话上下文持久化，关键信息提取与检索

对标 RAGFlow v0.25 Memory + Dify Conversation Variables
存储: Redis（短期对话记忆）+ 关键事实提取（长期记忆）
"""

import contextlib
import json
import logging
import time

logger = logging.getLogger(__name__)

# ── Memory 条目 ──


class MemoryEntry:
    """一条用户记忆"""

    def __init__(self, key: str, value: str, category: str = "fact", confidence: float = 1.0, ttl: int | None = None):
        self.key = key
        self.value = value
        self.category = category
        self.timestamp = time.time()
        self.confidence = confidence
        self.ttl = ttl

    def to_dict(self) -> dict:
        return {
            "key": self.key, "value": self.value, "category": self.category,
            "timestamp": self.timestamp, "confidence": self.confidence, "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        return cls(d["key"], d["value"], d.get("category", "fact"),
                   d.get("confidence", 1.0), d.get("ttl"))


class UserMemory:
    """用户级记忆管理器。

    Usage:
        mem = UserMemory("user_123")
        mem.remember("role", "backend engineer")
        mem.remember("prefers", "concise answers", category="preference")
        context = mem.relevant_context("what's my role?")
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._memories: dict[str, MemoryEntry] = {}
        self._redis = None
        self._loaded = False

    @property
    def redis(self):
        if self._redis is None:
            try:
                from core.redis_client import get_redis
                self._redis = get_redis(db=4, decode_responses=True)
            except Exception:
                pass
        return self._redis

    def _key(self, k: str) -> str:
        return f"mem:{self.user_id}:{k}"

    def _load(self):
        if self._loaded:
            return
        if not self.redis:
            self._loaded = True
            return
        try:
            raw = self.redis.hgetall(self._key("entries"))
            for k, v in (raw or {}).items():
                with contextlib.suppress(json.JSONDecodeError, KeyError):
                    self._memories[k] = MemoryEntry.from_dict(json.loads(v))
        except Exception:
            pass
        self._loaded = True

    def _save(self):
        if not self.redis:
            return
        try:
            data = {k: json.dumps(v.to_dict(), ensure_ascii=False) for k, v in self._memories.items()}
            self.redis.hset(self._key("entries"), mapping=data)
        except Exception:
            pass

    def remember(self, key: str, value: str, category: str = "fact", confidence: float = 1.0, ttl: int | None = None):
        """存储一条记忆"""
        self._load()
        self._memories[key] = MemoryEntry(key, value, category, confidence, ttl)
        self._save()
        logger.debug(f"Memory [{self.user_id}]: {key} = {value[:80]}")

    def recall(self, key: str) -> str | None:
        """精确查询一条记忆"""
        self._load()
        entry = self._memories.get(key)
        return entry.value if entry else None

    def forget(self, key: str):
        """删除一条记忆"""
        self._load()
        self._memories.pop(key, None)
        self._save()

    def clear(self):
        """清除所有记忆"""
        self._memories.clear()
        self._save()
        if self.redis:
            self.redis.delete(self._key("entries"))

    def relevant_context(self, query: str = "", max_items: int = 10) -> str:
        """返回格式化的记忆上下文，用于拼入 LLM 提示词"""
        self._load()
        if not self._memories:
            return ""

        entries = list(self._memories.values())
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        lines = ["## 用户记忆与偏好"]
        for e in entries[:max_items]:
            cat_tag = f"[{e.category}] " if e.category != "fact" else ""
            lines.append(f"- {cat_tag}{e.key}: {e.value}")
        return "\n".join(lines)

    def extract_and_remember(self, conversation_text: str, llm=None):
        """从对话中自动提取关键信息并存储。

        使用 LLM 提取: 姓名/角色/偏好/项目/约束 等
        """
        self._load()
        if llm is None:
            from core.llm_provider import get_small_llm
            llm = get_small_llm()

        prompt = f"""从以下对话中提取用户的关键信息。每行一条，格式为 `类型|键|值`。
类型包括: role(角色), preference(偏好), project(项目), constraint(约束), fact(事实)。
只提取明确陈述的信息，不要推测。如果没有可提取的信息，输出"无"。

对话:
{conversation_text}

提取结果:"""

        try:
            result = llm.generate(prompt, options={"temperature": 0, "num_predict": 256})
            for line in result.strip().split("\n"):
                if not line or line == "无" or "|" not in line:
                    continue
                parts = line.split("|", 2)
                if len(parts) >= 3:
                    cat, key, val = parts[0].strip(), parts[1].strip(), parts[2].strip()
                    if key and val:
                        self.remember(key, val, category=cat)
        except Exception as e:
            logger.warning(f"Memory extraction failed: {e}")

    def stats(self) -> dict:
        self._load()
        cats = {}
        for e in self._memories.values():
            cats[e.category] = cats.get(e.category, 0) + 1
        return {"user_id": self.user_id, "total": len(self._memories), "by_category": cats}


# ── 全局 Memory 注册表 ──
_user_memories: dict[str, UserMemory] = {}


def get_user_memory(user_id: str = "default") -> UserMemory:
    if user_id not in _user_memories:
        _user_memories[user_id] = UserMemory(user_id)
    return _user_memories[user_id]
