import re
import os
import time
import hashlib
import pickle
import base64
import logging
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Literal, Annotated, TypedDict

import operator
import pandas as pd
import ollama
from langgraph.graph import StateGraph, END

from config import Config
from core.generator import Generator

logger = logging.getLogger(__name__)

# ── State ──────────────────────────────────────────────────


class AgentState(TypedDict):
    question: str
    history: Optional[List[Dict[str, str]]]
    question_type: Literal["text", "chart", "table", "mixed"]
    retrieved_chunks: List[str]
    retrieved_images: List[str]
    table_data: Optional[Dict[str, Any]]
    chart_description: Optional[str]
    final_answer: str
    citations: Dict[str, str]
    iteration: int
    metadata: Dict[str, Any]


# ── Classifier ─────────────────────────────────────────────


def classify_question(question: str) -> Literal["text", "chart", "table", "mixed"]:
    q_lower = question.lower()
    chart_keywords = [
        "图",
        "figure",
        "图表",
        "流程图",
        "示意图",
        "柱状图",
        "饼图",
        "折线图",
        "diagram",
        "chart",
        "graph",
    ]
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


# ── Router ─────────────────────────────────────────────────


def route_question(state: AgentState) -> str:
    qtype = state.get("question_type", "text")
    if qtype == "text":
        return "text_retriever"
    elif qtype in ("chart", "table", "mixed"):
        return "vision_processor"
    else:
        return "text_retriever"


# ── Vision Agent ───────────────────────────────────────────

_IMAGE_CAPTION_CACHE_FILE = os.path.join(Config.CACHE_DIR, "image_captions.pkl")


def _load_caption_cache():
    if os.path.exists(_IMAGE_CAPTION_CACHE_FILE):
        with open(_IMAGE_CAPTION_CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def _save_caption_cache(cache):
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    with open(_IMAGE_CAPTION_CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)


def generate_image_caption(image_path: str) -> str:
    if not os.path.isabs(image_path):
        abs_path = os.path.join(Config.DATA_DIR, image_path)
    else:
        abs_path = image_path
    if not os.path.exists(abs_path):
        return f"[图片缺失: {os.path.basename(abs_path)}]"
    with open(abs_path, "rb") as f:
        img_hash = hashlib.md5(f.read()).hexdigest()
    cache = _load_caption_cache()
    if img_hash in cache:
        return cache[img_hash]
    try:
        with open(abs_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()
        response = ollama.chat(
            model=Config.VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "请用中文详细描述这张图片的内容，只输出描述，不要额外解释。",
                    "images": [img_base64],
                }
            ],
        )
        desc = response["message"]["content"]
        cache[img_hash] = desc
        _save_caption_cache(cache)
        return desc
    except Exception as e:
        logger.error(f"图片描述生成失败: {e}")
        return f"[图片: {os.path.basename(abs_path)}]"


def describe_chart(chart_image_path: str) -> str:
    return generate_image_caption(chart_image_path)


# ── Workflow ───────────────────────────────────────────────

_retriever = None
_generator = None


def get_retriever():
    global _retriever
    if _retriever is None:
        try:
            from core.retriever import HybridRetriever

            _retriever = HybridRetriever()
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
    try:
        lines = chunk_text.split("\n")
        table_lines = []
        in_table = False
        for line in lines:
            if re.match(r"^\|.*\|$", line):
                in_table = True
                table_lines.append(line)
            elif in_table and line.strip() == "":
                break
            elif in_table and not re.match(r"^\|.*\|$", line):
                break
        if not table_lines:
            return None
        html_rows = []
        for line in table_lines:
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            html_rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
        html_table = f"<table>{chr(10).join(html_rows)}</table>"
        df = pd.read_html(io.StringIO(html_table))[0]
        return df
    except Exception as e:
        logger.debug(f"表格解析失败: {e}")
        return None


def describe_table(df: pd.DataFrame) -> str:
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
        return {"retrieved_chunks": [], "retrieved_images": [], "metadata": {"error": "检索器不可用"}}
    start = time.perf_counter()
    chunks, indices = ret.hybrid_search(state["question"], top_k=Config.TOP_K)
    used_images = ret.get_chunk_images(indices)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"[text_retriever] cost={elapsed:.2f}ms, chunks={len(chunks)}")
    return {"retrieved_chunks": chunks, "retrieved_images": used_images, "metadata": {"indices": indices}}


def vision_processor_node(state: AgentState) -> dict:
    ret = get_retriever()
    if ret is None:
        return {
            "retrieved_chunks": [],
            "retrieved_images": [],
            "chart_description": "",
            "metadata": {"error": "检索器不可用"},
        }
    start = time.perf_counter()
    chunks, indices = ret.hybrid_search(state["question"], top_k=Config.TOP_K * 2)
    used_images = ret.get_chunk_images(indices)

    image_descriptions = []

    def _gen_caption(img_path):
        if not img_path:
            return ""
        if img_path.startswith("/images/"):
            abs_path = os.path.join(Config.DATA_DIR, img_path[8:])
        elif img_path.startswith("missing/"):
            return f"[缺失] {img_path}"
        else:
            abs_path = os.path.join(Config.DATA_DIR, img_path)
        return generate_image_caption(abs_path)

    with ThreadPoolExecutor(max_workers=Config.VISION_WORKERS) as executor:
        futures = []
        for img_list in used_images:
            for img_path in img_list:
                if img_path:
                    futures.append(executor.submit(_gen_caption, img_path))
        for future in as_completed(futures):
            desc = future.result()
            if desc:
                image_descriptions.append(desc)

    table_descriptions = []
    table_data_list = []
    for chunk in chunks:
        df = extract_table_from_chunk(chunk)
        if df is not None and not df.empty:
            table_desc = describe_table(df)
            table_descriptions.append(table_desc)
            table_data_list.append(df.to_dict(orient="records"))

    elapsed = (time.perf_counter() - start) * 1000
    logger.info(
        f"[vision_processor] cost={elapsed:.2f}ms, chunks={len(chunks)}, images={len(image_descriptions)}, tables={len(table_descriptions)}"
    )

    return {
        "retrieved_chunks": chunks,
        "retrieved_images": used_images,
        "chart_description": "\n".join(image_descriptions + table_descriptions),
        "metadata": {"indices": indices, "tables": table_data_list},
    }


def generate_node(state: AgentState) -> dict:
    gen = get_generator()
    start = time.perf_counter()
    if state.get("metadata", {}).get("error"):
        answer = "检索服务暂时不可用，请检查数据库连接。"
        citations = {}
    else:
        if state["question_type"] == "text":
            answer, citations = gen.generate(
                state["question"], state.get("retrieved_chunks", []), history=state.get("history")
            )
        else:
            context = state.get("retrieved_chunks", [])
            if state.get("chart_description"):
                context.append(state["chart_description"])
            answer, citations = gen.generate(state["question"], context, history=state.get("history"))
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
    workflow.add_conditional_edges(
        "classify", route_question, {"text_retriever": "text_retriever", "vision_processor": "vision_processor"}
    )
    workflow.add_edge("text_retriever", "generate")
    workflow.add_edge("vision_processor", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile()


agent_app = build_workflow()
