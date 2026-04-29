from typing import List, Dict, Any, Optional, TypedDict, Literal, Annotated
import operator


class AgentState(TypedDict):
    # 输入
    question: str
    history: Optional[List[Dict[str, str]]]

    # 中间状态
    question_type: Literal["text", "chart", "table", "mixed"]
    retrieved_chunks: List[str]
    retrieved_images: List[str]
    table_data: Optional[Dict[str, Any]]  # 解析后的表格数据
    chart_description: Optional[str]  # 图表描述

    # 最终输出
    final_answer: str
    citations: Dict[str, str]

    # 调试与计数
    iteration: int
    metadata: Dict[str, Any]