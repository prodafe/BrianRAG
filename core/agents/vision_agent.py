import ollama
from config import Config
import os

def generate_image_caption(image_path: str) -> str:
    """使用 Qwen2.5-VL 生成图片描述"""
    try:
        import base64
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")
        response = ollama.chat(
            model="qwen2.5-vl:7b",   # 确保你已经拉取该模型
            messages=[{
                "role": "user",
                "content": "请用中文详细描述这张图片的内容，只输出描述，不要额外解释。",
                "images": [img_base64]
            }]
        )
        return response["message"]["content"]
    except Exception as e:
        print(f"图片描述生成失败: {e}")
        return f"[图片: {os.path.basename(image_path)}]"

def describe_chart(chart_image_path: str) -> str:
    """专用图表描述（可复用上述函数）"""
    return generate_image_caption(chart_image_path)