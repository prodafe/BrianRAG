from .state import AgentState

def route_question(state: AgentState) -> str:
    """返回下一步要进入的节点名称"""
    qtype = state.get("question_type", "text")
    if qtype == "text":
        return "text_retriever"
    elif qtype in ("chart", "table", "mixed"):
        return "vision_processor"
    else:
        return "text_retriever"