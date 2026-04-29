import re
from typing import Literal


def classify_question(question: str) -> Literal["text", "chart", "table", "mixed"]:
    """
    基于关键词简单分类，后续可替换为 LLM 分类器
    """
    q_lower = question.lower()
    # 图表关键词
    chart_keywords = ["图", "figure", "图表", "流程图", "示意图", "柱状图", "饼图", "折线图", "diagram", "chart",
                      "graph"]
    # 表格关键词
    table_keywords = ["表", "表格", "tab", "matrix", "数据表", "清单"]

    has_chart = any(kw in q_lower for kw in chart_keywords)
    has_table = any(kw in q_lower for kw in table_keywords)

    if has_chart and has_table:
        return "mixed"
    if has_chart:
        return "chart"
    if has_table:
        return "table"
    return "text"