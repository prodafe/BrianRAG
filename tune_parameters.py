import os
import sys
import json
import itertools
import fcntl
import portalocker
import time
from config import Config
from evaluation.ragas_evaluator import evaluate_params

TEST_DATA_PATH = "evaluation/test_data.jsonl"
LOCK_FILE = "/tmp/brianrag_tune.lock"          # Linux/macOS
# 对于 Windows，可使用 msvcrt 或 portalocker，这里简单使用文件锁模拟（仅支持Unix）
# 若在 Windows 下运行，请安装 portalocker 并替换下述 fcntl 代码

def acquire_lock():
    try:
        lock_fd = open(LOCK_FILE, 'w')
        portalocker.lock(lock_fd, portalocker.LOCK_EX | portalocker.LOCK_NB)
        return lock_fd
    except portalocker.LockException:
        print("另一个调优任务正在运行，请稍后再试。")
        sys.exit(1)

def release_lock(lock_fd):
    portalocker.unlock(lock_fd)
    lock_fd.close()
    os.remove(LOCK_FILE)

def update_config(params):
    top_k, alpha, threshold = params
    config_path = os.path.join(os.path.dirname(__file__), "config.py")
    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(config_path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.startswith("TOP_K"):
                f.write(f"TOP_K = {top_k}\n")
            elif line.startswith("ALPHA"):
                f.write(f"ALPHA = {alpha}\n")
            elif line.startswith("SCORE_THRESHOLD"):
                f.write(f"SCORE_THRESHOLD = {threshold}\n")
            else:
                f.write(line)

def tune():
    # 获取进程锁，防止重复运行
    lock_fd = acquire_lock()
    try:
        if not os.path.exists(TEST_DATA_PATH):
            print(f"测试数据集不存在: {TEST_DATA_PATH}")
            print("请确保在 evaluation 目录下创建 test_data.jsonl 文件，包含 question 和 ground_truth 字段。")
            sys.exit(1)

        # 参数搜索范围
        top_k_values = [3, 5, 7]
        alpha_values = [0.3, 0.5, 0.7, 0.9]
        threshold_values = [0.2, 0.3, 0.4]

        best_score = -1
        best_params = None
        total = len(top_k_values) * len(alpha_values) * len(threshold_values)
        print(f"开始参数调优，共 {total} 组组合，预计耗时较长...")

        # 记录已测试的组合（避免重复，可选）
        tested = set()
        for top_k, alpha, thr in itertools.product(top_k_values, alpha_values, threshold_values):
            key = (top_k, alpha, thr)
            if key in tested:
                continue
            tested.add(key)
            print(f"\nTesting: top_k={top_k}, alpha={alpha}, threshold={thr}")
            try:
                score = evaluate_params(top_k, alpha, thr, TEST_DATA_PATH)
                print(f"  Score: {score:.4f}")
                if score > best_score:
                    best_score = score
                    best_params = key
                    print(f"  *** New best ***")
            except Exception as e:
                print(f"  Evaluation failed: {e}")

        if best_params:
            print(f"\n最优参数: top_k={best_params[0]}, alpha={best_params[1]}, threshold={best_params[2]}, score={best_score:.4f}")
            update_config(best_params)
            print("配置文件已更新，请重启应用使新参数生效。")
        else:
            print("未找到更优参数。")
    finally:
        release_lock(lock_fd)

if __name__ == "__main__":
    tune()