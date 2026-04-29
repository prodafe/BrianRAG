# core/agents/workflow.py
import re
import pandas as pd
import io
from langgraph.graph import StateGraph, END
from .state import AgentState
from .classifier import classify_question
from .router import route_question
from .vision_agent import generate_image_caption
from core.generator import Generator
from config import Config
import ollama
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 延迟初始化检索器和生成器，捕获异常
_retriever = None
_generator = None

def get_retriever():
    global _retriever
    if _retriever is None:
        try:
            from core.retriever import HybridRetriever
            _retriever = HybridRetriever()
            # 如果已有文档元数据，则标记为已加载
            if _retriever.doc_meta:
                _retriever.is_loaded = True
                logger.info("多模态智能体检索器已从已有索引加载")
        except Exception as e:
            logger.error(f"Failed to initialize HybridRetriever: {e}")
            _retriever = None
    return _retriever

def get_generator():
    global _generator
    if _generator is None:
        _generator = Generator()
    return _generator

def extract_table_from_chunk(chunk_text: str) -> pd.DataFrame:
    """
    从文本块中提取第一个 Markdown 表格，返回 DataFrame，若无则返回 None
    """
    try:
        lines = chunk_text.split('\n')
        table_lines = []
        in_table = False
        for line in lines:
            if re.match(r'^\|.*\|$', line):
                in_table = True
                table_lines.append(line)
            elif in_table and line.strip() == '':
                break
            elif in_table and not re.match(r'^\|.*\|$', line):
                break
        if not table_lines:
            return None
        html_rows = []
        for line in table_lines:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            html_rows.append('<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>')
        html_table = '<table>' + ''.join(html_rows) + '</table>'
        df = pd.read_html(io.StringIO(html_table))[0]
        return df
    except Exception as e:
        print(f"表格解析失败: {e}")
        return None

def describe_table(df: pd.DataFrame) -> str:
    """将 DataFrame 转换为自然语言描述"""
    if df is None:
        return ""
    desc = f"该表格有 {df.shape[0]} 行 {df.shape[1]} 列。\n"
    desc += df.to_markdown(index=False)
    return desc

def classify_node(state):
    start = time.perf_counter()
    qtype = classify_question(state["question"])
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"[classify] cost={elapsed:.2f}ms, result={qtype}")
    return {"question_type": qtype}

def text_retriever_node(state: AgentState) -> dict:
    ret = get_retriever()
    if ret is None:
        return {
            "retrieved_chunks": [],
            "retrieved_images": [],
            "metadata": {"error": "检索器不可用"}
        }
    start = time.perf_counter()
    chunks, indices = ret.hybrid_search(state["question"], top_k=Config.TOP_K)
    used_images = ret.get_chunk_images(indices)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"[text_retriever] cost={elapsed:.2f}ms, chunks={len(chunks)}")
    return {
        "retrieved_chunks": chunks,
        "retrieved_images": used_images,
        "metadata": {"indices": indices}
    }

def vision_processor_node(state: AgentState) -> dict:
    ret = get_retriever()
    if ret is None:
        return {
            "retrieved_chunks": [],
            "retrieved_images": [],
            "chart_description": "",
            "metadata": {"error": "检索器不可用"}
        }
    start = time.perf_counter()
    chunks, indices = ret.hybrid_search(state["question"], top_k=Config.TOP_K * 2)
    used_images = ret.get_chunk_images(indices)

    image_descriptions = []
    for img_list in used_images:
        for img_path in img_list:
            if img_path:
                desc = generate_image_caption(img_path)
                image_descriptions.append(desc)

    table_descriptions = []
    table_data_list = []
    for chunk in chunks:
        df = extract_table_from_chunk(chunk)
        if df is not None and not df.empty:
            table_desc = describe_table(df)
            table_descriptions.append(table_desc)
            table_data_list.append(df.to_dict(orient='records'))

    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"[vision_processor] cost={elapsed:.2f}ms, chunks={len(chunks)}, images={len(image_descriptions)}, tables={len(table_descriptions)}")

    return {
        "retrieved_chunks": chunks,
        "retrieved_images": used_images,
        "chart_description": "\n".join(image_descriptions + table_descriptions),
        "metadata": {
            "indices": indices,
            "tables": table_data_list
        }
    }

def generate_node(state: AgentState) -> dict:
    gen = get_generator()
    start = time.perf_counter()
    if state.get("metadata", {}).get("error"):
        # 检索器不可用，直接返回错误答案
        answer = "检索服务暂时不可用，请检查数据库连接。"
        citations = {}
    else:
        if state["question_type"] == "text":
            answer, citations = gen.generate(
                state["question"],
                state.get("retrieved_chunks", []),
                history=state.get("history")
            )
        else:
            context = state.get("retrieved_chunks", [])
            if state.get("chart_description"):
                context.append(state["chart_description"])
            answer, citations = gen.generate(
                state["question"],
                context,
                history=state.get("history")
            )
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"[generate] cost={elapsed:.2f}ms, answer_len={len(answer)}")
    return {"final_answer": answer, "citations": citations}

def build_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("classify", classify_node)
    workflow.add_node("text_retriever", text_retriever_node)
    workflow.add_node("vision_processor", vision_processor_node)
    workflow.add_node("generate", generate_node)

    workflow.set_entry_point("classify")
    workflow.add_conditional_edges("classify", route_question, {
        "text_retriever": "text_retriever",
        "vision_processor": "vision_processor"
    })
    workflow.add_edge("text_retriever", "generate")
    workflow.add_edge("vision_processor", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()

agent_app = build_workflow()