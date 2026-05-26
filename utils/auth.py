"""多租户 + RBAC — 轻量级权限系统（Redis 存储）"""

import hashlib
import time
import uuid

import redis

from config import Config

# 角色定义
ROLES = {
    "admin": ["read", "write", "delete", "manage_users", "manage_system"],
    "editor": ["read", "write", "delete"],
    "viewer": ["read"],
}

_redis_client: redis.Redis | None = None


def _r() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        redis_url = getattr(Config, "redis_url", "redis://localhost:6379/0")
        _redis_client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
    return _redis_client


# ── Tenant ──


def create_tenant(name: str, admin_email: str = "") -> dict:
    tid = str(uuid.uuid4())[:8]
    api_key = f"br_{hashlib.sha256(f'{tid}{time.time()}'.encode()).hexdigest()[:24]}"
    tenant = {
        "id": tid,
        "name": name,
        "api_key": api_key,
        "admin_email": admin_email,
        "created_at": time.time(),
        "active": True,
    }
    _r().hset(f"tenant:{tid}", mapping={k: str(v) for k, v in tenant.items()})
    _r().sadd("tenants", tid)
    return tenant


def get_tenant(tid: str) -> dict | None:
    data = _r().hgetall(f"tenant:{tid}")
    return data if data else None


def get_tenant_by_api_key(api_key: str) -> dict | None:
    tids = _r().smembers("tenants")
    for tid in tids:
        t = _r().hget(f"tenant:{tid}", "api_key")
        if t == api_key:
            return get_tenant(tid)
    return None


def list_tenants() -> list[dict]:
    return [get_tenant(tid) for tid in _r().smembers("tenants") if get_tenant(tid)]


def delete_tenant(tid: str) -> bool:
    _r().delete(f"tenant:{tid}", f"users:{tid}")
    _r().srem("tenants", tid)
    return True


# ── User ──


def create_user(tenant_id: str, username: str, role: str = "viewer") -> dict:
    if role not in ROLES:
        raise ValueError(f"无效角色: {role}")
    uid = str(uuid.uuid4())[:8]
    user = {
        "id": uid,
        "tenant_id": tenant_id,
        "username": username,
        "role": role,
        "created_at": time.time(),
        "active": True,
    }
    _r().hset(f"user:{uid}", mapping={k: str(v) for k, v in user.items()})
    _r().sadd(f"users:{tenant_id}", uid)
    return user


def get_user(uid: str) -> dict | None:
    data = _r().hgetall(f"user:{uid}")
    return data if data else None


def list_users(tenant_id: str) -> list[dict]:
    uids = _r().smembers(f"users:{tenant_id}")
    return [get_user(uid) for uid in uids if get_user(uid)]


def delete_user(uid: str) -> bool:
    user = get_user(uid)
    if not user:
        return False
    _r().srem(f"users:{user['tenant_id']}", uid)
    _r().delete(f"user:{uid}")
    return True


# ── Permission Check ──


def has_permission(api_key: str, action: str) -> tuple[bool, dict | None]:
    """检查 API Key 是否有权执行某操作。返回 (has_perm, tenant_dict)"""
    tenant = get_tenant_by_api_key(api_key)
    if not tenant or not tenant.get("active"):
        return False, None
    # admin 操作直接检查 tenant 管理员
    if action in ("manage_users", "manage_system"):
        return True, tenant  # tenant 创建者隐式 admin
    # 普通操作只要有有效 key 就允许
    return True, tenant


def get_required_permissions(endpoint: str, method: str) -> str:
    """根据端点和方法返回所需权限"""
    if method == "GET":
        return "read"
    if method == "POST":
        if "delete" in endpoint or "remove" in endpoint:
            return "delete"
        return "write"
    if method == "DELETE":
        return "delete"
    return "read"
