import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import Config
from core.graph_builder import GraphBuilder

# 准备一段包含实体关系的文本
text = """雷达是一种用于探测目标的电子设备。雷达的工作原理是利用电磁波反射。
雷达由天线、发射机、接收机等部分组成。"""

gb = GraphBuilder()   # 此时会使用 qwen2.5:7b
triples = gb.extract_triples(text)
print("提取到的三元组:")
for t in triples:
    print(t)