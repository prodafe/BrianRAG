import redis
import re
from config import Config

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def normalize_question(question: str) -> str:
    """标准化问题：去空格、转小写、去除标点符号"""
    q = re.sub(r"[^\w\u4e00-\u9fff]", "", question.strip().lower())
    return q


def record_question(question: str) -> int:
    """记录一次提问，返回该问题的当前计数"""
    q_norm = normalize_question(question)
    key = f"hot:count:{q_norm}"
    count = r.incr(key)
    if count == Config.HOT_QUESTION_THRESHOLD:
        r.sadd("hot:questions", q_norm)
        r.hset("hot:question_text", q_norm, question)
    r.expire(key, Config.HOT_QUESTION_TTL)
    return count


def get_hot_questions() -> list:
    """返回所有热点问题的原始文本列表"""
    q_norms = r.smembers("hot:questions")
    hot_list = []
    for q_norm in q_norms:
        original = r.hget("hot:question_text", q_norm)
        if original:
            hot_list.append(original)
        else:
            hot_list.append(q_norm)
    return hot_list


def clear_hot_question(question: str):
    """手动清除某个热点问题"""
    q_norm = normalize_question(question)
    r.delete(f"hot:count:{q_norm}")
    r.srem("hot:questions", q_norm)
    r.hdel("hot:question_text", q_norm)
