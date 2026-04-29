# utils/logger.py
import logging
import os
from config import Config

def setup_logger(name="BrianRAG", log_file="Brianrag.log"):
    """配置日志记录器，同时输出到控制台和文件"""
    os.makedirs(Config.LOG_DIR, exist_ok=True)  # 需要在 Config 中添加 LOG_DIR
    log_path = os.path.join(Config.LOG_DIR, log_file)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 文件处理器
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger