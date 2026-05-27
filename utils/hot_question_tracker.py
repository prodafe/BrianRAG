import re

from config import Config

_r = None


def _get_r():
    global _r
    if _r is None:
        from core.redis_client import get_redis

        _r = get_redis(db=0, decode_responses=True)
    return _r


def normalize_question(question: str) -> str:
    """标准化问题：去空格、转小写、去除标点符号"""
    q = re.sub(r"[^\w\u4e00-\u9fff]", "", question.strip().lower())
    return q


def record_question(question: str) -> int:
    """记录一次提问，返回该问题的当前计数"""
    q_norm = normalize_question(question)
    key = f"hot:count:{q_norm}"
    count = _get_r().incr(key)
    if count == Config.HOT_QUESTION_THRESHOLD:
        _get_r().sadd("hot:questions", q_norm)
        _get_r().hset("hot:question_text", q_norm, question)
    _get_r().expire(key, Config.HOT_QUESTION_TTL)
    return count


def get_hot_questions() -> list:
    """返回所有热点问题的原始文本列表"""
    q_norms = _get_r().smembers("hot:questions")
    hot_list = []
    for q_norm in q_norms:
        original = _get_r().hget("hot:question_text", q_norm)
        if original:
            hot_list.append(original)
        else:
            hot_list.append(q_norm)
    return hot_list


def clear_hot_question(question: str):
    """手动清除某个热点问题"""
    q_norm = normalize_question(question)
    _get_r().delete(f"hot:count:{q_norm}")
    _get_r().srem("hot:questions", q_norm)
    _get_r().hdel("hot:question_text", q_norm)
