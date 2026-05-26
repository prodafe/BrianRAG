import logging
import os
import time
from threading import Thread

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import Config

logger = logging.getLogger(__name__)


class KnowledgeBaseHandler(FileSystemEventHandler):
    def __init__(self, debounce_seconds: int = 2):
        self.debounce_seconds = debounce_seconds
        self.pending: set[str] = set()
        self.last_event: float = 0

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._handle_deletion(event.src_path)

    def _handle_event(self, path: str) -> None:
        now = time.time()
        self.pending.add(path)
        if now - self.last_event > self.debounce_seconds:
            self._process_pending()
        else:
            Thread(target=self._delayed_process).start()

    def _delayed_process(self) -> None:
        time.sleep(self.debounce_seconds)
        self._process_pending()

    def _process_pending(self) -> None:
        if not self.pending:
            return
        paths = list(self.pending)
        self.pending.clear()
        self.last_event = time.time()
        logger.info(f"检测到文件变化: {paths}")
        try:
            from core.rag_pipeline import RAGPipeline

            pipeline = RAGPipeline()
            pipeline.index_documents(paths, incremental=True)
            logger.info(f"增量索引完成: {len(paths)} 个文件")
        except Exception as e:
            logger.error(f"增量索引失败: {e}")

    def _handle_deletion(self, path: str) -> None:
        logger.info(f"文件已删除: {path}，请手动点击构建索引以清理向量数据。")


def start_watcher():
    """启动目录监控，返回 Observer 对象"""
    watch_dir = os.path.join(Config.DATA_DIR, "uploads")
    os.makedirs(watch_dir, exist_ok=True)
    event_handler = KnowledgeBaseHandler()
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()
    logger.info(f"已启动目录监控: {watch_dir}")
    return observer
