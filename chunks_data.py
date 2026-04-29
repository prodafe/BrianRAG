import pickle
import os
path = "index/chunks_data.pkl"
if os.path.exists(path):
    with open(path, "rb") as f:
        chunks, images = pickle.load(f)
    print(f"成功加载 {len(chunks)} 个文本块")
    if chunks:
        print("第一个文本块预览:", chunks[0][:200])
else:
    print("文件不存在")