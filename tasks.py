import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import time
import logging
from celery import Celery
from kombu import Queue, Exchange
import redis
import os

sys.path.insert(0, os.path.dirname(__file__))

celery_app = Celery(
    "brianrag",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# 定义队列（必须包含 name 属性）
default_queue = Queue("default", Exchange("default"), routing_key="default")
indexing_queue = Queue("indexing", Exchange("indexing"), routing_key="indexing")
priority_queue = Queue("priority", Exchange("priority"), routing_key="priority")

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    # 指定任务队列（必须为 Queue 实例列表，不能包含 None）
    task_queues=(default_queue, indexing_queue, priority_queue),
    task_default_queue="default",
    task_default_routing_key="default",
    # 路由配置：根据任务名分配队列
    task_routes={
        "tasks.index_documents_task": {"queue": "indexing"},
        "tasks.*_priority": {"queue": "priority"},
    },
)

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def index_documents_task(self, file_paths, incremental=True):
    from core.rag_pipeline import RAGPipeline
    import traceback

    def progress_callback(progress):
        self.update_state(
            state="PROGRESS",
            meta={"progress": progress, "message": f"索引中 {int(progress*100)}%"}
        )

    try:
        pipeline = RAGPipeline()
        num = pipeline.index_documents(file_paths, progress_callback=progress_callback, incremental=incremental)

        # ---------- 任务成功：更新 Redis 变更标志 ----------
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.set("docs:last_updated", time.time())
        r.publish("docs:changed", "update")   # 可选，用于 pub/sub


        return {"status": "success", "num_chunks": num}
    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        print(f"索引任务失败:\n{tb}")
        self.update_state(
            state="FAILURE",
            meta={"error": error_msg, "traceback": tb}
        )
        return {"status": "failure", "error": error_msg, "traceback": tb}