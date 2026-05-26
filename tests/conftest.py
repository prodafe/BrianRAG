import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def clean_config():
    """每次测试前重置 Config 到默认值"""
    from config import Config

    defaults = {
        "top_k": 5, "alpha": 0.5, "score_threshold": 0.3,
        "llm_provider": "ollama", "llm_model": "qwen2.5:7b",
        "embedding_model": "bge-m3:latest",
        "enable_self_correction": True, "enable_rerank": True,
        "enable_multimodal": True, "enable_graph": True,
        "enable_cache": True, "enable_hyde": True,
        "enable_mmr": True, "enable_retrieval_gating": True,
        "enable_semantic_chunking": True,
        "chunk_size": 800, "chunk_overlap": 100,
        "gating_score_threshold": 0.35,
    }
    for k, v in defaults.items():
        setattr(Config, k, v)
    yield Config
    for k, v in defaults.items():
        setattr(Config, k, v)


@pytest.fixture
def sample_chunks():
    return [
        "驱动轮与地面的摩擦力公式为 F = μ·N，其中 μ 为摩擦系数，N 为正压力。",
        "弹簧预压力的作用是保证弹簧在初始状态就具有一定的压缩量，防止松动并提高稳定性。",
        "Flex 调试前需要确保编译环境正确配置，包括 SDK 路径和调试器设置。",
        "减震器结构设计需考虑阻尼比、固有频率和最大行程三个核心参数。",
    ]
