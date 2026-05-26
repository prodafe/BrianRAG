import os
import sys

from sqlalchemy import create_engine, text

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config


def reset_all_data():
    print("正在清除所有 RAG 数据...")

    # 1. 删除 PostgreSQL 向量表
    sync_db_url = Config.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
    engine = create_engine(sync_db_url)
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {Config.VECTOR_TABLE_NAME}"))
            conn.commit()
            print(f"✓ 已删除向量表: {Config.VECTOR_TABLE_NAME}")
    except Exception as e:
        print(f"✗ 删除向量表失败: {e}")

    # 2. 删除本地文件
    files_to_delete = [
        os.path.join(Config.INDEX_DIR, "doc_meta.json"),
        Config.GRAPH_FILE,
    ]
    for filepath in files_to_delete:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"✓ 已删除文件: {filepath}")
        else:
            print(f"文件不存在，跳过: {filepath}")

    print("\n所有数据已清除。")


if __name__ == "__main__":
    confirm = input("此操作将删除所有已索引文档和图谱数据，是否继续？(yes/no): ")
    if confirm.lower() == "yes":
        reset_all_data()
    else:
        print("操作取消。")
