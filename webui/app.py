import sys
import os
import logging

# 确保 logs 目录存在
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/brianrag.log", encoding='utf-8')
    ]
)

import queue
import threading
import json
from datetime import datetime
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from core.rag_pipeline import RAGPipeline
from config import Config
from celery.result import AsyncResult
from tasks import celery_app
import requests

API_BASE_URL = "http://localhost:8000"

USER_AVATAR = "./webui/assets/rui.png"
ASSISTANT_AVATAR = "./webui/assets/ass.png"

# ==================== 高级 UI 样式 ====================
CUSTOM_CSS = """
<style>
    /* 全局暗色主题 */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    /* 侧边栏毛玻璃效果 */
    [data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        backdrop-filter: blur(10px);
        border-right: 1px solid #30363d;
    }
    /* 主内容区背景 */
    [data-testid="stMainBlockContainer"] {
        background-color: #0d1117;
    }
    /* 卡片、expander 样式 */
    .stApp, .stMarkdown, div[data-testid="stExpander"] {
        background-color: transparent;
    }
    div[data-testid="stExpander"] details {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 0.5rem;
    }
    /* 按钮样式 */
     .stButton button {
        background: linear-gradient(135deg, #d73a49, #cb2431);
        border: none;
        color: white;
        border-radius: 24px;
        padding: 0.4rem 1.2rem;
        font-weight: 500;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .stButton button:hover {
        transform: translateY(-1px);
        filter: brightness(1.05);
    }
    .stButton button:active {
        transform: translateY(1px);
    }
    /* 文件上传器 */
    div[data-testid="stFileUploader"] {
        background: #161b22;
        border: 1px dashed #3b82f6;
        border-radius: 20px;
        padding: 1rem;
    }
    /* radio 分组 (问答模式) */
    div[role="radiogroup"] {
        background: #161b22;
        border-radius: 40px;
        padding: 0.3rem;
        display: inline-flex;
        gap: 0.5rem;
    }
    div[role="radiogroup"] label {
        background: transparent;
        border-radius: 32px;
        padding: 0.4rem 1.2rem;
        transition: 0.2s;
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background: #2ea043;
        color: white;
    }
    /* 聊天消息 */
    .stChatMessage {
        background: transparent;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 24px;
    }
    .stChatMessage[data-testid="user"] {
        background: #1f6feb;
        color: white;
        border-radius: 24px 24px 8px 24px;
    }
    .stChatMessage[data-testid="assistant"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 24px 24px 24px 8px;
    }
    /* 代码块 */
    pre, code {
        background: #0d1117;
        border-radius: 12px;
        font-family: 'JetBrains Mono', monospace;
    }
    /* tabs 胶囊 */
    button[data-baseweb="tab"] {
        background: transparent;
        border-radius: 40px;
        padding: 0.5rem 1.2rem;
        margin: 0 0.2rem;
        font-weight: 500;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: #2ea043;
        color: white;
    }
    /* 进度条 */
    div[data-testid="stProgress"] > div > div {
        background-color: #2ea043;
    }
    /* spinner */
    .stSpinner > div {
        border-top-color: #2ea043;
    }
    /* 滚动条 */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #161b22;
    }
    ::-webkit-scrollbar-thumb {
        background: #30363d;
        border-radius: 8px;
    }
    /* 标题 */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600;
    }
    hr {
        border-color: #30363d;
    }
</style>
"""

# ==================== 样式结束 ====================

def log_feedback(question: str, answer: str, mode: str, feedback: str, comment: str = ""):
    feedback_file = os.path.join(Config.BASE_DIR, "feedback.jsonl")
    record = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": answer,
        "mode": mode,
        "feedback": feedback,
        "comment": comment
    }
    with open(feedback_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def fetch_documents():
    """从后端获取当前已索引文档列表"""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/documents", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("documents", [])
    except Exception as e:
        st.warning(f"获取文档列表失败: {e}")
    return []

def check_and_refresh_documents():
    """检查文档版本，如有更新则重新加载文档列表并刷新页面"""
    if "last_updated" not in st.session_state:
        st.session_state.last_updated = 0
    try:
        resp = requests.get(f"{API_BASE_URL}/api/documents/last_updated", timeout=2)
        if resp.status_code == 200:
            remote_ts = resp.json().get("last_updated", 0)
            if remote_ts > st.session_state.last_updated:
                # 版本更新，重新拉取文档列表
                st.session_state.documents = fetch_documents()
                st.session_state.last_updated = remote_ts
                # 更新检索器的元数据（如果存在）
                if hasattr(st.session_state, 'pipeline') and st.session_state.pipeline.retriever:
                    st.session_state.pipeline.retriever._load_doc_meta()
                # 强制刷新页面
                st.rerun()
    except Exception:
        # 静默失败，不影响主流程
        pass

def main():
    st.set_page_config(page_title="BrianRAG 知识库", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.title("📚 BrianRAG - 企业知识库问答系统")

    # 自动检查文档更新（实现实时刷新）
    check_and_refresh_documents()

    if "pipeline" not in st.session_state:
        st.session_state.pipeline = RAGPipeline()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # 初始化文档列表状态
    if "documents" not in st.session_state:
        st.session_state.documents = fetch_documents()
    if "indexing_task_id" not in st.session_state:
        st.session_state.indexing_task_id = None
    if "indexing_status" not in st.session_state:
        st.session_state.indexing_status = "idle"
    if "feedback_expanded" not in st.session_state:
        st.session_state.feedback_expanded = {}
    if "tuning_in_progress" not in st.session_state:
        st.session_state.tuning_in_progress = False
    if "tune_process" not in st.session_state:
        st.session_state.tune_process = None
    if "tune_result" not in st.session_state:
        st.session_state.tune_result = None

    pipeline = st.session_state.pipeline

    # 调优进程检查
    if st.session_state.tuning_in_progress:
        if st.session_state.tune_process is None:
            st.session_state.tuning_in_progress = False
            st.error("调优进程启动失败，请检查 tune_parameters.py 是否存在。")
            st.rerun()
        poll = st.session_state.tune_process.poll()
        if poll is None:
            st.info("参数自动调优正在进行中，请稍候...")
            time.sleep(2)
            st.rerun()
        else:
            stdout, stderr = st.session_state.tune_process.communicate()
            returncode = st.session_state.tune_process.returncode
            st.session_state.tuning_in_progress = False
            st.session_state.tune_process = None
            if returncode == 0 and "配置文件已更新" in stdout:
                st.success("参数优化完成！请重启应用以使用新参数。")
            else:
                if "负面反馈不足" in stdout:
                    st.warning("负面反馈不足（至少需要3条），无法进行有效调优。")
                else:
                    st.error(f"调优失败:\n{stdout}\n{stderr}")
            st.session_state.tune_result = None
            st.rerun()

    # 侧边栏
    with st.sidebar:
        st.header("文档管理")
        uploaded_files = st.file_uploader(
            "上传文档 (txt, pdf, md, docx, html, csv, jpg, jpeg, png, gif, bmp)",
            type=["txt", "pdf", "md", "docx", "html", "csv", "jpg", "jpeg", "png", "gif", "bmp"],
            accept_multiple_files=True
        )
        incremental = st.checkbox("增量添加新文档", value=True)

        if st.button("构建索引", disabled=(st.session_state.indexing_status == "running")):
            if uploaded_files:
                try:
                    # 上传文件
                    files = [("files", (file.name, file.getvalue())) for file in uploaded_files]
                    upload_resp = requests.post(f"{API_BASE_URL}/api/upload", files=files, timeout=30)
                    upload_resp.raise_for_status()
                    file_paths = upload_resp.json()["file_paths"]
                except Exception as e:
                    st.error(f"文件上传失败: {e}")
                    return

                try:
                    # 提交索引任务
                    index_resp = requests.post(f"{API_BASE_URL}/api/index",
                                               json={"file_paths": file_paths, "incremental": incremental},
                                               timeout=10)
                    index_resp.raise_for_status()
                    task_id = index_resp.json()["task_id"]
                    st.session_state.indexing_task_id = task_id
                    st.session_state.indexing_status = "running"
                    st.rerun()
                except Exception as e:
                    st.error(f"提交索引任务失败: {e}")
                    return
            else:
                st.warning("请先上传文件")

        # 轮询任务状态
        if st.session_state.indexing_status == "running":
            task_id = st.session_state.indexing_task_id
            if task_id:
                try:
                    resp = requests.get(f"{API_BASE_URL}/api/task/{task_id}", timeout=5)
                    resp.raise_for_status()
                    data = resp.json()
                    state = data["state"]
                    if state == "PENDING":
                        st.info("⏳ 任务已提交，等待执行...")
                    elif state == "PROGRESS":
                        progress = data.get("progress", 0)
                        message = data.get("message", f"索引中... {int(progress * 100)}%")
                        st.progress(progress, text=message)
                    elif state == "SUCCESS":
                        num = data["result"].get("num_chunks", 0)
                        st.success(f"✅ 已索引 {num} 个文本块")
                        # 刷新文档列表
                        st.session_state.documents = fetch_documents()
                        st.session_state.indexing_status = "done"
                        st.session_state.indexing_task_id = None
                        st.rerun()
                    elif state == "FAILURE":
                        error = data.get("error", "未知错误")
                        st.error(f"❌ 索引失败: {error}")
                        st.session_state.indexing_status = "error"
                        st.session_state.indexing_task_id = None
                        st.rerun()
                except requests.exceptions.Timeout:
                    st.warning("状态查询超时，请稍后刷新页面查看索引结果")
                except requests.exceptions.ConnectionError:
                    st.error("无法连接到后端服务，请确认 FastAPI 已启动")
                except Exception as e:
                    st.error(f"状态查询失败: {e}")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.indexing_status = "idle"
                st.rerun()
        else:
            if st.session_state.indexing_status == "done":
                st.success("上一次索引已完成，可以开始新的索引。")
            elif st.session_state.indexing_status == "error":
                st.error("上一次索引失败，请修正后重试。")
                if st.button("重置索引状态"):
                    st.session_state.indexing_status = "idle"
                    st.rerun()

        # 已索引文档列表（使用 session_state.documents）
        with st.expander("📄 已索引文档"):
            if st.session_state.documents:
                doc_items = st.session_state.documents
                doc_items.sort(key=lambda x: x["path"])
                for item in doc_items:
                    col1, col2 = st.columns([4, 1])
                    col1.write(os.path.basename(item["path"]))
                    if col2.button("🗑️", key=f"del_{item['hash']}"):
                        try:
                            del_resp = requests.delete(f"{API_BASE_URL}/api/documents/{item['hash']}", timeout=5)
                            if del_resp.status_code == 200:
                                st.session_state.documents = fetch_documents()
                                st.success("文档已删除，请重新构建索引以清理向量数据。")
                                st.rerun()
                            else:
                                st.error("删除失败")
                        except Exception as e:
                            st.error(f"删除出错: {e}")
            else:
                st.caption("暂无已索引文档")

        st.markdown("---")
        st.subheader("配置")
        enable_rerank = st.checkbox("启用重排序 (Reranker)", value=Config.ENABLE_RERANK)
        Config.ENABLE_RERANK = enable_rerank
        if enable_rerank:
            rerank_top_k = st.slider("重排序后保留片段数", 1, 5, Config.RERANK_TOP_K)
            Config.RERANK_TOP_K = rerank_top_k
        top_k = st.slider("检索片段数 (Top-K)", 1, 10, 3)
        alpha = st.slider("关键词权重 (Alpha)", 0.0, 1.0, 0.8)
        score_threshold = st.slider("相似度阈值", 0.0, 1.0, 0.3)
        query_mode = st.radio("问答模式", ["快速模式 (RAG)", "智能体模式 (Agentic)", "图谱工作流 (LangGraph)",
                                           "多模态智能体 (MultiModal)"])
        Config.TOP_K = top_k
        Config.ALPHA = alpha
        Config.SCORE_THRESHOLD = score_threshold

        button_disabled = st.session_state.tuning_in_progress
        if st.button("🔧 参数自动调优 (基于反馈)", disabled=button_disabled):
            st.session_state.tuning_in_progress = True
            st.session_state.tune_process = subprocess.Popen(
                [sys.executable, "tune_parameters.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Config.BASE_DIR
            )
            st.rerun()

        if st.button("清空对话历史"):
            st.session_state.messages = []
            st.rerun()

    # 主区域标签页
    tab_q, tab_g = st.tabs(["💬 问答", "📊 知识图谱"])

    # 问答页
    with tab_q:
        st.header("💬 提问")
        for msg_idx, msg in enumerate(st.session_state.messages):
            avatar = USER_AVATAR if msg["role"] == "user" else ASSISTANT_AVATAR
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])
                if msg["role"] == "assistant":
                    question_text = st.session_state.messages[msg_idx - 1]["content"] if msg_idx > 0 else ""
                    cur_mode = st.session_state.get("query_mode", "快速模式 (RAG)")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("👍 有用", key=f"up_{msg_idx}"):
                            log_feedback(question_text, msg["content"], cur_mode, "positive", "")
                            st.success("感谢反馈！")
                    with col2:
                        if st.button("👎 无用", key=f"down_{msg_idx}"):
                            st.session_state.feedback_expanded[msg_idx] = not st.session_state.feedback_expanded.get(msg_idx, False)
                            st.rerun()

                    if st.session_state.feedback_expanded.get(msg_idx, False):
                        with st.container():
                            st.markdown("#### 📝 反馈详情")
                            comment = st.text_area("请描述问题或提供正确答案（可选）", key=f"comment_{msg_idx}")
                            col_submit, col_cancel = st.columns(2)
                            with col_submit:
                                if st.button("✅ 提交反馈", key=f"submit_{msg_idx}"):
                                    log_feedback(question_text, msg["content"], cur_mode, "negative", comment)
                                    st.success("反馈已记录，感谢您的帮助！")
                                    st.session_state.feedback_expanded[msg_idx] = False
                                    st.rerun()
                            with col_cancel:
                                if st.button("❌ 取消", key=f"cancel_{msg_idx}"):
                                    st.session_state.feedback_expanded[msg_idx] = False
                                    st.rerun()

        if query := st.chat_input("请输入您的问题"):
            st.chat_message("user", avatar=USER_AVATAR).markdown(query)
            st.session_state.messages.append({"role": "user", "content": query})

            with st.spinner("思考中..."):
                history = st.session_state.messages[-Config.MAX_HISTORY_TURNS * 2:]
                st.session_state.query_mode = query_mode
                if query_mode == "快速模式 (RAG)":
                    result = pipeline.query(query, history=history)
                elif query_mode == "智能体模式 (Agentic)":
                    result = pipeline.agentic_query(query, history=history)
                elif query_mode == "图谱工作流 (LangGraph)":
                    result = pipeline.graph_query(query, history=history)
                else:
                    result = pipeline.agentic_multimodal_query(query, history=history)

            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                import re
                answer_with_sup = re.sub(r'\[(\d+)\]', r'<sup>[\1]</sup>', result["answer"])
                st.markdown(answer_with_sup, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": result["answer"]})

            with st.expander("📖 参考片段"):
                for i, chunk in enumerate(result["used_chunks"]):
                    st.text(f"片段 {i + 1}:\n{chunk[:500]}...")
                    images = result.get("used_images", [])[i] if i < len(result.get("used_images", [])) else []
                    for img_path in images:
                        if os.path.exists(img_path):
                            st.image(img_path, caption=os.path.basename(img_path), use_container_width=True)
                        else:
                            st.caption(f"图片不存在: {img_path}")
            if result.get("citations"):
                with st.expander("📌 引用详情"):
                    for ref_num, text in result["citations"].items():
                        st.markdown(f"**[{ref_num}]** {text[:200]}...")
            st.rerun()

    # 知识图谱页
    with tab_g:
        st.header("📊 知识图谱")
        retriever = getattr(pipeline, 'retriever', None)
        graph_obj = None
        if retriever is not None and hasattr(retriever, 'graph_builder') and retriever.graph_builder:
            graph_obj = retriever.graph_builder
        elif hasattr(pipeline, 'graph') and pipeline.graph is not None:
            graph_obj = pipeline.graph
            st.info("图谱数据来自 pipeline.graph（如希望检索器也使用时，请重建索引）")

        if graph_obj is not None and hasattr(graph_obj, 'graph'):
            if graph_obj.graph.number_of_nodes() > 0:
                st.success(f"图谱规模: {graph_obj.graph.number_of_nodes()} 个节点, {graph_obj.graph.number_of_edges()} 条边")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("生成并预览图谱"):
                        html_path = graph_obj.to_html()
                        with open(html_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                        st.components.v1.html(html_content, height=600)
                with col2:
                    if st.button("下载图谱 (HTML)"):
                        html_path = graph_obj.to_html()
                        with open(html_path, "rb") as f:
                            st.download_button("点击下载", f, file_name="knowledge_graph.html", mime="text/html")
            else:
                st.info("当前知识图谱为空，请确保已启用图谱并全量重建索引（取消勾选「增量添加」）。")
        else:
            st.warning("知识图谱未构建或未启用。请在 `config.py` 中设置 `ENABLE_GRAPH = True` 并全量重建索引。")

if __name__ == "__main__":
    main()