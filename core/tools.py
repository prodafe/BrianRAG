"""工具调用模块 — 给 Agent 提供实时计算/搜索/时间能力"""
import math
import re
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── 工具注册表 ──
_registry: dict[str, dict[str, Any]] = {}


def register(name: str, description: str):
    """装饰器：注册工具函数"""

    def decorator(func):
        _registry[name] = {"func": func, "description": description, "name": name}
        return func

    return decorator


def get_tools_prompt() -> str:
    """生成工具列表描述，嵌入 LLM 提示词"""
    lines = ["## 可用工具", "你可以通过以下格式调用工具：`[TOOL:工具名:参数]`", ""]
    for name, info in _registry.items():
        lines.append(f"- **{name}**: {info['description']}")
    lines.append("")
    lines.append("调用后系统会返回工具结果，你应基于结果继续回答。")
    return "\n".join(lines)


def execute_tool_call(text: str) -> str | None:
    """解析 LLM 输出中的工具调用并执行"""
    pattern = r"\[TOOL:(\w+):([^\]]+)\]"
    match = re.search(pattern, text)
    if not match:
        return None
    name, arg = match.group(1), match.group(2).strip()
    tool = _registry.get(name)
    if not tool:
        return f"未知工具: {name}"
    try:
        result = tool["func"](arg)
        return str(result)
    except Exception as e:
        return f"工具调用失败: {e}"


# ── 内置工具 ──


@register("calc", "数学计算，参数为数学表达式，如 `2+3*4` 或 `sqrt(16)`")
def tool_calc(expr: str) -> str:
    allowed = set("0123456789+-*/.()^% sqrtancosintabcdelmpr ")
    safe = "".join(c for c in expr if c in allowed or c.isalpha() or c == "_")
    namespace = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "pi": math.pi,
        "e": math.e,
        "abs": abs,
        "round": round,
        "pow": pow,
        "ceil": math.ceil,
        "floor": math.floor,
    }
    result = eval(safe, {"__builtins__": {}}, namespace)
    if isinstance(result, float):
        return f"{result:.6f}"
    return str(result)


@register("time", "获取当前日期时间或计算时间，参数为 `now` / `today` / `+N天` / `-N小时`")
def tool_time(arg: str) -> str:
    now = datetime.now()
    arg = arg.strip().lower()
    if arg in ("now", "today", ""):
        return now.strftime("%Y-%m-%d %H:%M:%S")
    match = re.match(r"([+-])(\d+)(天|小时|分钟|周)", arg)
    if match:
        sign, num, unit = match.group(1), int(match.group(2)), match.group(3)
        delta_map = {"天": timedelta(days=num), "小时": timedelta(hours=num), "分钟": timedelta(minutes=num), "周": timedelta(weeks=num)}
        delta = delta_map.get(unit, timedelta())
        if sign == "-":
            delta = -delta
        return (now + delta).strftime("%Y-%m-%d %H:%M:%S")
    return now.strftime("%Y-%m-%d %H:%M:%S")


@register("unit", "单位换算，参数格式如 `10km->m` 或 `100°C->°F`")
def tool_unit(arg: str) -> str:
    conversions = {
        ("km", "m"): 1000,
        ("m", "cm"): 100,
        ("cm", "mm"): 10,
        ("kg", "g"): 1000,
        ("g", "mg"): 1000,
        ("h", "min"): 60,
        ("min", "s"): 60,
        ("l", "ml"): 1000,
        ("gb", "mb"): 1024,
        ("mb", "kb"): 1024,
    }
    match = re.match(r"([\d.]+)\s*(\w+)\s*->\s*(\w+)", arg.strip())
    if not match:
        return "格式错误，示例: 10km->m"
    value, from_unit, to_unit = float(match.group(1)), match.group(2).lower(), match.group(3).lower()
    # 温度特殊处理
    if from_unit in ("°c", "c", "℃") and to_unit in ("°f", "f", "℉"):
        return f"{value * 9 / 5 + 32:.1f}°F"
    if from_unit in ("°f", "f", "℉") and to_unit in ("°c", "c", "℃"):
        return f"{(value - 32) * 5 / 9:.1f}°C"
    # 标准转换
    key = (from_unit, to_unit)
    if key in conversions:
        return f"{value * conversions[key]} {to_unit}"
    return f"不支持 {from_unit} -> {to_unit} 的换算"


# ── 初始化 ──
logger.info(f"工具模块已加载: {list(_registry.keys())}")
