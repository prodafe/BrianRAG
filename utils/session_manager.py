"""会话管理 — Redis 存储的用户会话/对话历史"""

import json
import logging
import time
import uuid

import redis

from config import Config

logger = logging.getLogger(__name__)

SESSION_TTL = 7 * 24 * 3600  # 7 天过期


class SessionManager:
    def __init__(self):
        redis_url = getattr(Config, "redis_url", "redis://localhost:6379/0")
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)

    def create_session(self, name: str = "") -> dict:
        sid = str(uuid.uuid4())[:8]
        session = {
            "id": sid,
            "name": name or f"对话 {sid}",
            "created_at": time.time(),
            "updated_at": time.time(),
            "message_count": 0,
        }
        self.redis.setex(f"session:{sid}", SESSION_TTL, json.dumps(session, ensure_ascii=False))
        self.redis.zadd("sessions", {sid: time.time()})
        return session

    def get_session(self, sid: str) -> dict | None:
        data = self.redis.get(f"session:{sid}")
        if not data:
            return None
        return json.loads(data)

    def list_sessions(self) -> list[dict]:
        sids = self.redis.zrevrange("sessions", 0, 49)
        sessions = []
        for sid in sids:
            data = self.redis.get(f"session:{sid}")
            if data:
                sessions.append(json.loads(data))
        return sessions

    def add_message(self, sid: str, role: str, content: str) -> bool:
        session = self.get_session(sid)
        if not session:
            return False
        msg = {"role": role, "content": content, "time": time.time()}
        self.redis.rpush(f"messages:{sid}", json.dumps(msg, ensure_ascii=False))
        self.redis.expire(f"messages:{sid}", SESSION_TTL)
        session["message_count"] += 1
        session["updated_at"] = time.time()
        self.redis.setex(f"session:{sid}", SESSION_TTL, json.dumps(session, ensure_ascii=False))
        self.redis.zadd("sessions", {sid: time.time()})
        return True

    def get_history(self, sid: str, limit: int = 20) -> list[dict]:
        raw = self.redis.lrange(f"messages:{sid}", -limit, -1)
        return [json.loads(r) for r in raw]

    def delete_session(self, sid: str) -> bool:
        self.redis.delete(f"session:{sid}", f"messages:{sid}")
        self.redis.zrem("sessions", sid)
        return True


# 单例
_session_mgr: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _session_mgr
    if _session_mgr is None:
        _session_mgr = SessionManager()
    return _session_mgr
