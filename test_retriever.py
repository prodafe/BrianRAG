import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from core.retriever import HybridRetriever

ret = HybridRetriever()
print("初始化成功")