import asyncio
import json
import logging
import os
import shutil
import sys
import time
import uuid
import zipfile
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import Config
from core.metrics import metrics_endpoint
from core.rag_pipeline import RAGPipeline
from core.redis_client import close_all as close_redis
from core.redis_client import get_redis
from core.telemetry import setup_telemetry
from utils.dir_watcher import start_watcher
from utils.history_manager import HistoryManager
from utils.hot_question_tracker import get_hot_questions

logger = logging.getLogger(__name__)

tags_metadata = [
    {"name": "Query", "description": "核心问答接口 — RAG/Agentic/Graph/Multimodal 四种模式"},
    {"name": "Index & Documents", "description": "文档上传、索引构建与检索管理"},
    {"name": "Knowledge Graph", "description": "知识图谱可视化数据导出"},
    {"name": "Health & Status", "description": "服务健康检查与系统状态"},
    {"name": "Evaluation", "description": "RAGAS 评估与结果查询"},
    {"name": "History & Feedback", "description": "对话历史与用户反馈"},
    {"name": "Sessions & Auth", "description": "租户/会话多用户隔离"},
    {"name": "Prewarm", "description": "预训练缓存管理"},
    {"name": "GitHub Sync", "description": "GitHub 数据源同步"},
]

# ---------- Lifespan (FastAPI 推荐方式，替代弃用的 on_event) ----------
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _history_manager, _scheduler, _watcher_observer, _bg_executor
    try:
        _history_manager = HistoryManager()
        logger.info("历史管理器初始化成功")
    except Exception as e:
        logger.warning(f"历史管理器初始化失败: {e}")

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(prewarm_hot_questions, "interval", seconds=Config.HOT_QUESTION_PREWARM_INTERVAL)

    github_interval = getattr(Config, "GITHUB_SYNC_INTERVAL", 0)
    if github_interval > 0:
        _scheduler.add_job(_github_auto_sync, "interval", seconds=github_interval, id="github_sync")
        _scheduler.add_job(_github_auto_sync, "date", run_date=__import__("datetime").datetime.now())
        logger.info(f"GitHub 自动同步已启动（每 {github_interval}s）")

    _scheduler.start()
    logger.info("后台调度器已启动")

    try:
        _watcher_observer = start_watcher()
        logger.info("目录监控已启动")
    except Exception as e:
        logger.warning(f"目录监控启动失败: {e}")

    yield

    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("调度器已停止")
    if _watcher_observer:
        _watcher_observer.stop()
        _watcher_observer.join()
        logger.info("目录监控已停止")
    if _bg_executor:
        _bg_executor.shutdown(wait=True)
        logger.info("后台线程池已关闭")
    close_redis()
    logger.info("Redis 连接池已关闭")


app = FastAPI(title="BrianRAG API", version="2.3.0", lifespan=lifespan, openapi_tags=tags_metadata,
              description="Enterprise Knowledge Engine — 本地优先 RAG 知识库问答系统。支持混合检索、知识图谱、多模态。")

# ── API Key 鉴权（可选，通过环境变量 BRIAN_API_KEY 启用）──
_API_KEY = os.getenv("BRIAN_API_KEY", "")
_TENANT_MODE = os.getenv("BRIAN_TENANT_MODE", "") == "true"

if _API_KEY or _TENANT_MODE:

    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method != "OPTIONS":
            if request.url.path in ("/api/health", "/api/ocr_status"):
                return await call_next(request)
            key = request.headers.get("X-API-Key", "")
            if _TENANT_MODE:
                from utils.auth import get_required_permissions, has_permission

                action = get_required_permissions(request.url.path, request.method)
                ok, tenant = has_permission(key, action)
                if not ok:
                    from fastapi.responses import JSONResponse

                    return JSONResponse({"detail": "无效的 API Key 或权限不足"}, status_code=401)
            elif key != _API_KEY:
                from fastapi.responses import JSONResponse

                return JSONResponse({"detail": "无效的 API Key"}, status_code=401)
        return await call_next(request)


images_dir = os.path.join(Config.DATA_DIR, "images")
os.makedirs(images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=images_dir), name="images")

setup_telemetry(app)
app.add_route("/metrics", metrics_endpoint)
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 请求/响应模型 ----------
class IndexRequest(BaseModel):
    file_paths: list[str]
    incremental: bool = True


class IndexResponse(BaseModel):
    task_id: str


# 全局变量
_watcher_observer = None
_history_manager = None  # 历史管理器实例
_scheduler = None


# ---------- 预热函数 ----------
def prewarm_hot_questions():
    questions = get_hot_questions()
    if not questions:
        return
    pipeline = RAGPipeline()
    for q in questions:
        try:
            pipeline.query(q, history=None)
            logger.info(f"预热成功: {q}")
        except Exception as e:
            logger.error(f"预热失败 {q}: {e}")




# ---------- 历史相关 API ----------
@app.post("/api/history/add", tags=["History & Feedback"], summary="记录用户提问")
async def add_history(question: str):
    """记录用户提问"""
    global _history_manager
    if _history_manager is None:
        raise HTTPException(500, "历史管理器未就绪")
    _history_manager.add_question(question)
    return {"status": "ok"}


@app.get("/api/history/recommend", tags=["History & Feedback"], summary="基于历史推荐问题")
async def recommend_questions(question: str, top_k: int = 3):
    """获取相似历史问题推荐"""
    global _history_manager
    if _history_manager is None:
        raise HTTPException(500, "历史管理器未就绪")
    recs = _history_manager.recommend(question, top_k)
    return {"recommendations": recs}


# ── 会话管理 API ──
from utils.session_manager import get_session_manager


@app.post("/api/sessions", tags=["Sessions & Auth"], summary="创建/列出会话")
async def create_session(name: str = ""):
    mgr = get_session_manager()
    session = mgr.create_session(name)
    return session


@app.get("/api/sessions", tags=["Sessions & Auth"], summary="创建/列出会话")
async def list_sessions():
    mgr = get_session_manager()
    return {"sessions": mgr.list_sessions()}


@app.get("/api/sessions/{sid}", tags=["Sessions & Auth"], summary="创建/列出会话")
async def get_session(sid: str):
    mgr = get_session_manager()
    session = mgr.get_session(sid)
    if not session:
        raise HTTPException(404, "会话不存在")
    history = mgr.get_history(sid)
    return {"session": session, "history": history}


@app.delete("/api/sessions/{sid}", tags=["Sessions & Auth"], summary="创建/列出会话")
async def delete_session(sid: str):
    mgr = get_session_manager()
    mgr.delete_session(sid)
    return {"status": "ok"}


# ── 多租户管理 API ──
from utils.auth import create_tenant, create_user, delete_tenant, delete_user, get_tenant, list_tenants, list_users


@app.post("/api/tenants", tags=["Sessions & Auth"], summary="创建/列出租户")
async def api_create_tenant(name: str, email: str = ""):
    return create_tenant(name, email)


@app.get("/api/tenants", tags=["Sessions & Auth"], summary="创建/列出租户")
async def api_list_tenants():
    return {"tenants": list_tenants()}


@app.get("/api/tenants/{tid}", tags=["Sessions & Auth"], summary="创建/列出租户")
async def api_get_tenant(tid: str):
    t = get_tenant(tid)
    if not t:
        raise HTTPException(404, "租户不存在")
    return {"tenant": t, "users": list_users(tid)}


@app.delete("/api/tenants/{tid}", tags=["Sessions & Auth"], summary="创建/列出租户")
async def api_delete_tenant(tid: str):
    delete_tenant(tid)
    return {"status": "ok"}


@app.post("/api/tenants/{tid}/users", tags=["Sessions & Auth"], summary="创建/列出租户")
async def api_create_user(tid: str, username: str, role: str = "viewer"):
    try:
        return create_user(tid, username, role)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/tenants/{tid}/users", tags=["Sessions & Auth"], summary="创建/列出租户")
async def api_list_users(tid: str):
    return {"users": list_users(tid)}


@app.delete("/api/users/{uid}")
async def api_delete_user(uid: str):
    delete_user(uid)
    return {"status": "ok"}


# ── WebSocket 实时索引进度 ──
from fastapi import WebSocket, WebSocketDisconnect


@app.websocket("/ws/progress/{task_id}")
async def ws_indexing_progress(ws: WebSocket, task_id: str):
    await ws.accept()
    try:
        while True:
            task = _bg_tasks.get(task_id, {})
            await ws.send_json(task)
            if task.get("state") in ("SUCCESS", "FAILURE"):
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        await ws.close()


# ── 后台任务系统（替代 Celery）──
_bg_tasks: dict[str, dict] = {}
_bg_executor = ThreadPoolExecutor(max_workers=2)


@app.post("/api/index", response_model=IndexResponse, tags=["Index & Documents"], summary="触发文档索引构建")
async def start_indexing(req: IndexRequest):
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="文件路径列表不能为空")
    task_id = str(uuid.uuid4())
    _bg_tasks[task_id] = {"state": "PENDING", "progress": 0, "message": "排队中"}
    loop = asyncio.get_event_loop()

    def _run():
        try:

            def progress_cb(p):
                _bg_tasks[task_id].update(state="PROGRESS", progress=p, message=f"索引中 {int(p * 100)}%")

            pipeline = RAGPipeline()
            num = pipeline.index_documents(req.file_paths, progress_callback=progress_cb, incremental=req.incremental)
            r = get_redis(db=0)
            r.set("docs:last_updated", time.time())
            r.publish("docs:changed", "update")
            _bg_tasks[task_id].update(state="SUCCESS", result={"status": "success", "num_chunks": num})
        except Exception as e:
            import traceback

            _bg_tasks[task_id].update(state="FAILURE", error=str(e), traceback=traceback.format_exc())

    loop.run_in_executor(_bg_executor, _run)
    return IndexResponse(task_id=task_id)


@app.get("/api/task/{task_id}", tags=["Index & Documents"], summary="查询索引任务进度")
async def get_task_status(task_id: str):
    task = _bg_tasks.get(task_id)
    if not task:
        raise HTTPException(404, detail="任务不存在或已过期")
    return task


_health_cache = {"ts": 0, "data": None}
_health_cache_ttl = 5  # 缓存 5 秒，避免高负载下频繁建连


@app.get("/api/health", tags=["Health & Status"], summary="服务健康检查")
@limiter.limit("5/second")
async def health(request: Request):
    now = time.time()
    if now - _health_cache["ts"] < _health_cache_ttl and _health_cache["data"]:
        return _health_cache["data"]

    status = {"status": "ok", "services": {}}

    # Redis（复用连接池）
    try:
        r = get_redis(db=0, socket_connect_timeout=2)
        r.ping()
        status["services"]["redis"] = "ok"
    except Exception:
        status["services"]["redis"] = "unavailable"
        status["status"] = "degraded"

    # PostgreSQL
    try:
        import psycopg

        with psycopg.connect(
            Config.DATABASE_URL.replace("+psycopg://", "://").replace("+asyncpg://", "://"), connect_timeout=3
        ) as conn:
            conn.execute("SELECT 1")
        status["services"]["postgresql"] = "ok"
    except Exception:
        status["services"]["postgresql"] = "unavailable"
        status["status"] = "degraded"

    # Ollama
    ollama_models = {}
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{Config.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                status["services"]["ollama"] = "ok"
                ollama_models = {m["name"]: True for m in resp.json().get("models", [])}
            else:
                status["services"]["ollama"] = "unavailable"
    except Exception:
        status["services"]["ollama"] = "unavailable"
        status["status"] = "degraded"

    # Model availability
    status["models"] = {
        "llm": Config.LLM_MODEL in ollama_models if ollama_models else "unknown",
        "embedding": Config.EMBEDDING_MODEL in ollama_models if ollama_models else "unknown",
        "vision": Config.VISION_MODEL in ollama_models if ollama_models else "unknown",
        "reranker": "configured" if Config.ENABLE_RERANK else "disabled",
        "multimodal": "configured" if Config.ENABLE_MULTIMODAL else "disabled",
    }

    _health_cache["ts"] = now
    _health_cache["data"] = status
    return status


@app.post("/api/index/images", tags=["Index & Documents"], summary="批量索引图片到多模态检索器")
async def index_images(batch_size: int = 50):
    """扫描 data/ 目录下的图片文件，批量嵌入 CLIP 索引"""
    pipeline = get_pipeline()
    retriever = pipeline.retriever
    if not retriever or not retriever._init_success:
        raise HTTPException(500, "检索器未初始化")
    if not retriever.clip_retriever or not retriever.clip_retriever.is_available:
        raise HTTPException(503, "多模态检索器不可用（CLIP 模型未加载）")

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    all_images = []
    for root, _dirs, files in os.walk(Config.DATA_DIR):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in image_extensions:
                all_images.append(os.path.join(root, f))

    if not all_images:
        return {"message": "没有找到图片文件", "indexed": 0}

    indexed = 0
    total = len(all_images)
    for i in range(0, total, batch_size):
        batch = all_images[i : i + batch_size]
        for img_path in batch:
            try:
                from PIL import Image

                Image.open(img_path).verify()
                retriever.clip_retriever.add_image(img_path, {"source": img_path, "type": "image"})
                indexed += 1
            except Exception as e:
                logger.warning(f"索引图片失败 {img_path}: {e}")
        retriever.clip_retriever.save_index()
        logger.info(f"图片索引进度: {min(i + batch_size, total)}/{total}")

    return {"message": "图片索引完成", "indexed": indexed, "total": total}


@app.post("/api/upload", tags=["Index & Documents"], summary="上传文档文件")
async def upload_files(files: list[UploadFile] = File(...)):
    saved_paths = []
    upload_dir = os.path.join(Config.DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        safe_name = os.path.basename(file.filename)  # 防止路径穿越
        is_zip = safe_name.lower().endswith(".zip") or file.content_type == "application/zip"
        if is_zip:
            temp_zip = os.path.join(upload_dir, f"temp_{safe_name}")
            with open(temp_zip, "wb") as f:
                content = await file.read()
                f.write(content)
            extract_dir = os.path.join(upload_dir, os.path.splitext(safe_name)[0])
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(temp_zip, "r") as zip_ref:
                # 防御 Zip Slip 路径穿越
                extract_base = os.path.normpath(extract_dir) + os.sep
                for member in zip_ref.infolist():
                    member_path = os.path.normpath(os.path.join(extract_dir, member.filename))
                    if not member_path.startswith(extract_base):
                        logger.warning(f"Zip Slip 攻击检测: {member.filename}")
                        raise HTTPException(400, f"Zip 包含非法路径: {member.filename}")
                    if member.is_dir():
                        os.makedirs(member_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(member_path), exist_ok=True)
                        with zip_ref.open(member) as source, open(member_path, "wb") as target:
                            shutil.copyfileobj(source, target)
            os.remove(temp_zip)
            for root, _dirs, files_in_extract in os.walk(extract_dir):
                for fname in files_in_extract:
                    full_path = os.path.join(root, fname)
                    saved_paths.append(full_path)
        else:
            save_path = os.path.join(upload_dir, safe_name)
            with open(save_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_paths.append(save_path)

    return {"file_paths": saved_paths}


@app.get("/api/documents", tags=["Index & Documents"], summary="已索引文档列表")
async def get_documents():
    meta_path = os.path.join(Config.INDEX_DIR, "doc_meta.json")
    if not os.path.exists(meta_path):
        return {"documents": []}
    with open(meta_path, encoding="utf-8") as f:
        doc_meta = json.load(f)
    docs = [{"hash": h, "path": info.get("path", "")} for h, info in doc_meta.items()]
    return {"documents": docs}


@app.delete("/api/documents/{file_hash}", tags=["Index & Documents"], summary="已索引文档列表")
async def delete_document(file_hash: str):
    try:
        meta_path = os.path.join(Config.INDEX_DIR, "doc_meta.json")
        if not os.path.exists(meta_path):
            raise HTTPException(404, "文档列表不存在")
        with open(meta_path, encoding="utf-8") as f:
            doc_meta = json.load(f)
        if file_hash not in doc_meta:
            raise HTTPException(404, "文档未找到")
        del doc_meta[file_hash]
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(doc_meta, f, indent=2)
        return {"status": "deleted"}
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(500, f"删除失败: {str(e)}")


@app.get("/api/documents/last_updated", tags=["Index & Documents"], summary="文档最后更新时间")
async def get_last_updated():
    try:
        r = get_redis(db=0, socket_connect_timeout=2)
        ts = r.get("docs:last_updated")
        return {"last_updated": float(ts) if ts else 0}
    except Exception:
        return {"last_updated": 0}


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    feedback: str  # "positive" or "negative"
    comment: str = ""


@app.post("/api/feedback", tags=["History & Feedback"], summary="提交用户反馈（正/负面）")
async def record_feedback(req: FeedbackRequest):
    """记录用户反馈，negative 反馈用于改进后续检索"""
    import json
    from datetime import datetime

    entry = {
        "timestamp": datetime.now().isoformat(),
        "question": req.question,
        "answer": req.answer[:500],
        "feedback": req.feedback,
        "comment": req.comment,
    }

    # 追加到 JSONL
    feedback_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "feedback.jsonl")
    with open(feedback_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # negative 反馈存入 Redis 用于实时增强
    if req.feedback == "negative":
        r = get_redis(db=0, decode_responses=True)
        r.hset("feedback:negative", req.question, req.comment or "需要更详细的回答")
        r.expire("feedback:negative", Config.HOT_QUESTION_TTL)

    return {"status": "ok"}


# ---------- 查询接口 ----------


class QueryRequest(BaseModel):
    question: str
    mode: str = "rag"  # "rag" | "agentic" | "graph" | "multimodal"
    history: list[dict] = []


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


@app.post("/api/query", tags=["Query"], summary="知识库问答查询（支持 rag/agentic/graph/multimodal）")
@limiter.limit("10/minute")
async def query(request: Request, req: QueryRequest):
    """同步查询接口"""
    pipeline = get_pipeline()
    loop = asyncio.get_event_loop()

    def _run():
        if req.mode == "agentic":
            return pipeline.agentic_query(req.question, history=req.history)
        elif req.mode == "graph":
            return pipeline.graph_query(req.question, history=req.history)
        elif req.mode == "multimodal":
            return pipeline.agentic_multimodal_query(req.question, history=req.history)
        else:
            return pipeline.query(req.question, history=req.history)

    try:
        result = await loop.run_in_executor(None, _run)
        return {
            "answer": result.get("answer", ""),
            "used_chunks": result.get("used_chunks", []),
            "used_images": result.get("used_images", []),
            "citations": result.get("citations", {}),
            "suggestion": result.get("suggestion"),
            "highlight_terms": result.get("highlight_terms", []),
        }
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


@app.get("/api/query/stream", tags=["Query"], summary="SSE 流式问答")
async def query_stream(question: str, mode: str = "rag", history: str = "[]"):
    """SSE 流式查询接口。history 为 JSON 编码的对话历史列表。"""
    pipeline = get_pipeline()
    try:
        history_list = json.loads(history) if history else []
    except Exception:
        history_list = []

    async def event_stream():
        loop = asyncio.get_event_loop()

        if mode in ("agentic", "graph", "multimodal"):
            yield f"data: {json.dumps({'phase': 'processing'}, ensure_ascii=False)}\n\n"

            def _run():
                if mode == "agentic":
                    return pipeline.agentic_query(question)
                elif mode == "graph":
                    return pipeline.graph_query(question)
                else:
                    return pipeline.agentic_multimodal_query(question)

            result = await loop.run_in_executor(None, _run)
            answer = result.get("answer", "")
            chunk_size = 10
            for i in range(0, len(answer), chunk_size):
                yield f"data: {json.dumps({'token': answer[i : i + chunk_size]}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'citations': result.get('citations', {}), 'used_chunks': result.get('used_chunks', [])}, ensure_ascii=False)}\n\n"
        else:
            # RAG 模式：真正的流式
            try:
                gen = pipeline.query_stream(question, history=history_list or None)
                for chunk in gen:
                    # 检查是否为元数据/阶段 token
                    if chunk.startswith("{") and ('"__meta__"' in chunk or '"__phase__"' in chunk):
                        try:
                            meta = json.loads(chunk)
                            if '"__phase__"' in chunk:
                                yield f"data: {json.dumps({'phase': meta.get('__phase__', 'searching')}, ensure_ascii=False)}\n\n"
                            else:
                                yield f"data: {json.dumps({'done': True, 'citations': meta.get('citations', {}), 'used_chunks': meta.get('used_chunks', [])}, ensure_ascii=False)}\n\n"
                        except Exception:
                            yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'token': f'[查询出错: {str(e)}]'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------- 预训练缓存 ----------

from core.prewarm import PrewarmEngine

_prewarm_engine = None


def get_prewarm_engine():
    global _prewarm_engine
    if _prewarm_engine is None:
        _prewarm_engine = PrewarmEngine()
    return _prewarm_engine


@app.get("/api/graph", tags=["Knowledge Graph"], summary="知识图谱节点与边数据")
async def get_graph(node_limit: int = 200):
    """导出知识图谱节点与边，供前端可视化。"""
    from core.retriever import _get_shared

    try:
        gb = _get_shared("graph_builder")
        if gb is None or not hasattr(gb, "graph") or gb.graph.number_of_nodes() == 0:
            return {"nodes": [], "edges": [], "stats": {"node_count": 0, "edge_count": 0}}

        graph = gb.graph
        e2c = getattr(gb, "entity_to_chunks", {})

        # 按度数排序取 top-N 节点
        degrees = dict(graph.degree())
        top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:node_limit]
        top_ids = {n for n, _ in top_nodes}

        nodes = [
            {
                "id": n,
                "label": n[:50],
                "degree": d,
                "chunks": list(e2c.get(n, set()))[:10],
            }
            for n, d in top_nodes
        ]

        edges = [
            {"from": u, "to": v, "label": data.get("relation", "")[:30]}
            for u, v, data in graph.edges(data=True)
            if u in top_ids and v in top_ids
        ]

        return {
            "nodes": nodes,
            "edges": edges[:5000],
            "stats": {
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges(),
                "displayed_nodes": len(nodes),
                "displayed_edges": len(edges),
            },
        }
    except Exception as e:
        logger.error(f"图谱导出失败: {e}")
        return {"nodes": [], "edges": [], "stats": {"node_count": 0, "edge_count": 0}}


@app.get("/api/graph/communities", tags=["Knowledge Graph"], summary="知识图谱社区检测与摘要（GraphRAG）")
async def get_graph_communities(max_communities: int = 10):
    """检测知识图谱社区并生成 LLM 摘要（GraphRAG 风格）"""
    from core.retriever import _get_shared

    gb = _get_shared("graph_builder")
    if gb is None:
        try:
            from core.graph_builder import GraphBuilder
            gb = GraphBuilder()
            gb.load()
        except Exception:
            return {"communities": [], "stats": {"node_count": 0}}

    communities = gb.detect_communities()
    summaries = gb.summarize_communities(max_communities=max_communities)
    stats = gb.get_stats()

    return {
        "communities": summaries,
        "community_count": len(communities),
        "stats": stats,
    }


# ── 工作流 + 多 Agent API ──


@app.get("/api/workflow/templates", tags=["Query"], summary="获取内置工作流模板")
async def list_workflow_templates():
    from core.workflow_engine import BUILTIN_TEMPLATES
    return {"templates": list(BUILTIN_TEMPLATES.values())}


@app.post("/api/workflow/run", tags=["Query"], summary="执行工作流")
async def run_workflow(req: dict):
    from core.workflow_engine import Workflow, WorkflowEngine

    workflow = Workflow.from_dict(req)
    pipeline = get_pipeline()
    engine = WorkflowEngine(pipeline=pipeline)
    from core.tools import _registry
    for name, info in _registry.items():
        engine.register_tool(name, info["func"])

    result = engine.run(workflow, {"question": req.get("input", {}).get("question", "")})
    return {"workflow_id": workflow.id, "result": result["result"], "history": result["state"]["history"]}


@app.post("/api/agent/multi", tags=["Query"], summary="多 Agent 协作查询（Planner+Retriever+Critic）")
async def multi_agent_query(req: dict):
    from core.multi_agent import run_multi_agent

    pipeline = get_pipeline()
    result = run_multi_agent(req.get("question", ""), pipeline=pipeline)
    return result


class PlaygroundRequest(BaseModel):
    question: str
    mode: str = "rag"
    top_k: int | None = None
    alpha: float | None = None
    score_threshold: float | None = None
    enable_rerank: bool | None = None
    enable_mmr: bool | None = None


@app.post("/api/playground/query", tags=["Query"], summary="RAG 调试（全流程 trace）")
async def playground_query(req: PlaygroundRequest):
    """RAG 调试端点 — 返回全流程 trace 信息。"""
    import time

    pipeline = get_pipeline()
    trace = {"steps": [], "timing_ms": {}}

    try:
        # Step 1: 意图分类
        t0 = time.perf_counter()
        intent = pipeline._classify_intent(req.question)
        trace["timing_ms"]["intent"] = round((time.perf_counter() - t0) * 1000, 1)
        trace["steps"].append({"step": "intent", "result": intent})

        # Step 2: 检索
        t0 = time.perf_counter()
        if pipeline.retriever is None:
            return {"answer": "检索器未初始化", "trace": trace}
        candidate = pipeline.retriever.hybrid_search(req.question, top_k=req.top_k or 20)
        trace["timing_ms"]["retrieval"] = round((time.perf_counter() - t0) * 1000, 1)
        trace["steps"].append({
            "step": "retrieval",
            "candidate_count": len(candidate[0]) if candidate else 0,
            "top_snippets": [c[:100] for c in (candidate[0] or [])[:3]],
        })

        # Step 3: 重排序（如果启用且在参数中请求）
        rerank_scores = []
        if req.enable_rerank is not False and pipeline.reranker and candidate and candidate[0]:
            t0 = time.perf_counter()
            try:
                reranked = pipeline.reranker.rerank(req.question, candidate[0][:10], top_k=req.top_k or 5)
                rerank_scores = [(text[:60], round(score, 3)) for score, _, text in reranked[:3]]
                trace["timing_ms"]["rerank"] = round((time.perf_counter() - t0) * 1000, 1)
            except Exception as e:
                logger.warning(f"Playground reranker failed: {e}")
        trace["steps"].append({"step": "rerank", "top_scores": rerank_scores})

        # Step 4: 生成
        t0 = time.perf_counter()
        context = candidate[0][: req.top_k or 5] if candidate else []
        answer, citations = pipeline.generator.generate(req.question, context, intent=intent)
        trace["timing_ms"]["generation"] = round((time.perf_counter() - t0) * 1000, 1)
        trace["steps"].append({
            "step": "generation",
            "model": Config.llm_model,
            "context_chunks": len(context),
            "citation_count": len(citations),
        })

        trace["timing_ms"]["total"] = round(sum(trace["timing_ms"].values()), 1)

        return {
            "answer": answer,
            "citations": citations,
            "used_chunks": context,
            "trace": trace,
        }
    except Exception as e:
        logger.error(f"Playground 查询失败: {e}")
        return {"answer": f"查询失败: {e}", "trace": trace}


class PrewarmResponse(BaseModel):
    status: str = "ok"
    count: int = 0
    message: str = ""


@app.post("/api/prewarm", response_model=PrewarmResponse, tags=["Prewarm"], summary="构建预训练缓存")
async def start_prewarm():
    """触发预训练：基于已索引文档生成问答对并缓存"""
    engine = get_prewarm_engine()
    loop = asyncio.get_event_loop()

    def _run():
        return engine.run()

    try:
        count = await loop.run_in_executor(None, _run)
        return PrewarmResponse(count=count, message=f"已生成并缓存 {count} 个问答对")
    except Exception as e:
        return PrewarmResponse(status="error", message=str(e))


@app.get("/api/prewarm/status", tags=["Health & Status"], summary="预训练缓存状态")
async def prewarm_status():
    engine = get_prewarm_engine()
    return engine.get_status()


# ---------- 评估接口 ----------

_eval_running = False
_eval_last_result = None


@app.post("/api/eval", tags=["Evaluation"], summary="触发 RAGAS 评估")
async def run_evaluation(limit: int = 20, mode: str = "rag"):
    """触发 RAGAS 评估，使用独立的评估模型避免循环论证"""
    global _eval_running, _eval_last_result
    if _eval_running:
        raise HTTPException(409, "评估任务正在运行中，请稍后再试")

    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from evaluation.evaluate import run_evaluation as _run_eval

    test_data = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evaluation", "test_data.jsonl"
    )
    if not os.path.exists(test_data):
        raise HTTPException(404, f"测试数据文件不存在: {test_data}")

    mode_map = {"rag": "快速模式 (RAG)", "agentic": "智能体模式 (Agentic)", "graph": "图谱工作流 (LangGraph)"}
    query_mode = mode_map.get(mode, "快速模式 (RAG)")

    _eval_running = True
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_eval(
                test_data,
                query_mode=query_mode,
                limit=limit,
                output_dir=os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "evaluation"
                ),
            ),
        )
        _eval_last_result = {
            "mode": mode,
            "num_samples": limit,
            "scores": {k: float(v) for k, v in result.items() if hasattr(v, "__float__")},
            "timestamp": __import__("time").time(),
        }
        return {"status": "ok", "result": _eval_last_result}
    except Exception as e:
        raise HTTPException(500, f"评估失败: {str(e)}")
    finally:
        _eval_running = False


@app.get("/api/eval/results", tags=["Evaluation"], summary="获取评估结果")
async def get_eval_results():
    """获取最近一次评估结果"""
    if _eval_last_result is None:
        # 尝试从文件读取
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "evaluation", "report.json"
        )
        if os.path.exists(report_path):
            import json

            with open(report_path, encoding="utf-8") as f:
                return {"status": "ok", "result": json.load(f)}
        return {"status": "ok", "result": None, "message": "尚未运行评估"}
    return {"status": "ok", "result": _eval_last_result}


@app.get("/api/eval/status", tags=["Evaluation"], summary="评估任务状态")
async def eval_status():
    """检查评估是否正在运行"""
    return {"running": _eval_running}


# ---------- GitHub 数据源 ----------


@app.post("/api/github/clone")
async def github_clone():
    """克隆 GitHub 仓库到本地并索引所有文档"""
    from utils.github_sync import get_github_sync

    sync = get_github_sync()
    if not sync.configured:
        raise HTTPException(400, "未配置 GitHub 仓库，请在 config.py 中设置 GITHUB_REPO_URL")

    ok, msg = sync.clone()
    if not ok:
        raise HTTPException(500, msg)

    # 克隆成功后自动索引
    files = sync.list_documents()
    if files:
        try:
            from core.retriever import HybridRetriever

            retriever = HybridRetriever()
            retriever.load_documents(files, incremental=True)
        except Exception as e:
            logger.warning(f"自动索引失败 (不影响克隆): {e}")

    return {"status": "ok", "message": msg, "files_found": len(files)}


@app.post("/api/github/sync")
async def github_sync():
    """拉取 GitHub 仓库最新变更并增量索引"""
    from utils.github_sync import get_github_sync

    sync = get_github_sync()
    if not sync.configured:
        raise HTTPException(400, "未配置 GitHub 仓库")

    if not sync.cloned:
        raise HTTPException(400, "仓库尚未克隆，请先调用 /api/github/clone")

    ok, msg, changed = sync.pull()
    if not ok:
        raise HTTPException(500, msg)

    # 增量索引变更文件
    indexed = 0
    if changed:
        try:
            from core.retriever import HybridRetriever

            retriever = HybridRetriever()
            doc_files = [
                f for f in changed if any(f.lower().endswith(p.lstrip("*")) for p in Config.GITHUB_DOC_PATTERNS)
            ]
            retriever.load_documents(doc_files, incremental=True)
            indexed = len(doc_files)
        except Exception as e:
            logger.warning(f"增量索引失败: {e}")

    return {"status": "ok", "message": msg, "changed_files": len(changed), "indexed_files": indexed}


@app.get("/api/github/status")
async def github_status():
    """获取 GitHub 数据源状态"""
    from utils.github_sync import get_github_sync

    return get_github_sync().get_status()


@app.get("/api/github/documents")
async def github_documents():
    """列出 GitHub 仓库中的所有文档文件"""
    from utils.github_sync import get_github_sync

    sync = get_github_sync()
    if not sync.cloned:
        return {"documents": [], "message": "仓库尚未克隆"}
    return {"documents": sync.list_documents()}


# ---------- GitHub 定时同步 ----------


def _github_auto_sync():
    """定时检查 GitHub 仓库更新并自动索引"""
    from utils.github_sync import get_github_sync

    sync = get_github_sync()
    if not sync.configured or not sync.cloned:
        return
    try:
        ok, msg, changed = sync.pull()
        if ok and changed:
            logger.info(f"GitHub 自动同步: {msg}, {len(changed)} 文件变更")
            doc_files = [
                f for f in changed if any(f.lower().endswith(p.lstrip("*")) for p in Config.GITHUB_DOC_PATTERNS)
            ]
            if doc_files:
                from core.retriever import HybridRetriever

                retriever = HybridRetriever()
                retriever.load_documents(doc_files, incremental=True)
                logger.info(f"GitHub 自动索引: {len(doc_files)} 文件")
    except Exception as e:
        logger.warning(f"GitHub 自动同步失败: {e}")


# ---------- 前端静态文件 ----------
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
