import json
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from celery.result import AsyncResult
from tasks import celery_app, index_documents_task
import os
from config import Config
import redis

app = FastAPI(title="BrianRAG API", version="1.0.0")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 请求/响应模型 ----------
class IndexRequest(BaseModel):
    file_paths: List[str]
    incremental: bool = True

class IndexResponse(BaseModel):
    task_id: str

# ---------- API 端点 ----------
@app.post("/api/index", response_model=IndexResponse)
async def start_indexing(req: IndexRequest):
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="文件路径列表不能为空")
    task = index_documents_task.delay(req.file_paths, req.incremental)
    return IndexResponse(task_id=task.id)

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    result = {"task_id": task_id, "state": task.state}
    if task.state == "PROGRESS":
        result.update(progress=task.info.get("progress", 0), message=task.info.get("message", ""))
    elif task.state == "SUCCESS":
        result["result"] = task.result
    elif task.state == "FAILURE":
        error = None
        if task.info and isinstance(task.info, dict):
            error = task.info.get("error") or task.info.get("traceback")
        elif task.result and isinstance(task.result, dict):
            error = task.result.get("error") or task.result.get("traceback")
        result["error"] = error or "未知错误"
    return result

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    saved_paths = []
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    for file in files:
        save_path = os.path.join(Config.DATA_DIR, file.filename)
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)
        saved_paths.append(save_path)
    return {"file_paths": saved_paths}

@app.get("/api/documents")
async def get_documents():
    """返回当前已索引的文档列表（从 doc_meta.json 读取）"""
    meta_path = os.path.join(Config.INDEX_DIR, "doc_meta.json")
    if not os.path.exists(meta_path):
        return {"documents": []}
    with open(meta_path, "r", encoding="utf-8") as f:
        doc_meta = json.load(f)
    docs = [{"hash": h, "path": info.get("path", "")} for h, info in doc_meta.items()]
    return {"documents": docs}

@app.delete("/api/documents/{file_hash}")
async def delete_document(file_hash: str):
    """删除指定文档的元数据（保留向量数据，提示用户重建）"""
    try:
        meta_path = os.path.join(Config.INDEX_DIR, "doc_meta.json")
        if not os.path.exists(meta_path):
            raise HTTPException(404, "文档列表不存在")
        with open(meta_path, "r", encoding="utf-8") as f:
            doc_meta = json.load(f)
        if file_hash not in doc_meta:
            raise HTTPException(404, "文档未找到")
        del doc_meta[file_hash]
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(doc_meta, f, indent=2)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/documents/last_updated")
async def get_last_updated():
    """返回文档列表最后更新时间戳（用于前端自动刷新）"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        ts = r.get('docs:last_updated')
        return {"last_updated": float(ts) if ts else 0}
    except Exception:
        # 如果 Redis 不可用，返回 0（降级）
        return {"last_updated": 0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)