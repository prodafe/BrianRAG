"""Redis 客户端 — 共享连接池，避免连接泄漏"""

import logging
import threading
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_pools: dict[int, "redis.ConnectionPool"] = {}
_pools_lock = threading.Lock()


def get_redis(db: int = 0, decode_responses: bool = True, socket_connect_timeout: int = 2) -> "redis.Redis":
    """Return a Redis client backed by a shared connection pool.

    Pools are cached per-db so each db number gets its own pool.
    All connections use Config.redis_url for host/port resolution.
    Thread-safe under concurrent access.
    """
    import redis as _redis

    from config import Config

    if db in _pools:
        return _redis.Redis(connection_pool=_pools[db])

    with _pools_lock:
        if db in _pools:
            return _redis.Redis(connection_pool=_pools[db])
        parsed = urlparse(Config.redis_url)
        try:
            _pools[db] = _redis.ConnectionPool(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                db=db,
                decode_responses=decode_responses,
                socket_connect_timeout=socket_connect_timeout,
                socket_keepalive=True,
                max_connections=50,
            )
        except Exception:
            logger.warning(f"Redis 连接池创建失败 (db={db})，回退到直连")
            return _redis.Redis(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                db=db,
                decode_responses=decode_responses,
                socket_connect_timeout=socket_connect_timeout,
            )
    return _redis.Redis(connection_pool=_pools[db])


def close_all():
    """Disconnect all shared connection pools. Call on app shutdown."""
    global _pools
    for db, pool in _pools.items():
        try:
            pool.disconnect()
        except Exception:
            pass
    _pools.clear()
