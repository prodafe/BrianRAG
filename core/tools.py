"""工具调用模块 — 给 Agent 提供实时计算/搜索/时间能力"""

import ast
import logging
import math
import operator as _op
import re
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── 安全的数学表达式求值器（替代 eval）──

_SAFE_OPS = {
    ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
    ast.Div: _op.truediv, ast.Pow: _op.pow, ast.USub: _op.neg,
    ast.Mod: _op.mod, ast.FloorDiv: _op.floordiv,
}

_SAFE_FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "pi": lambda: math.pi, "e": lambda: math.e,
    "abs": abs, "round": round, "pow": pow, "ceil": math.ceil, "floor": math.floor,
}


def _safe_eval_node(node):
    """递归求值 AST 节点，只允许安全的数学操作。"""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"不支持的常量: {node.value}")
    elif isinstance(node, ast.BinOp):
        op = _SAFE_OPS.get(type(node.op))
        if not op:
            raise ValueError(f"不安全的运算符: {type(node.op).__name__}")
        return op(_safe_eval_node(node.left), _safe_eval_node(node.right))
    elif isinstance(node, ast.UnaryOp):
        op = _SAFE_OPS.get(type(node.op))
        if not op:
            raise ValueError(f"不安全的一元运算符: {type(node.op).__name__}")
        return op(_safe_eval_node(node.operand))
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("不支持属性调用")
        func = _SAFE_FUNCS.get(node.func.id)
        if not func:
            raise ValueError(f"不支持的函数: {node.func.id}")
        args = [_safe_eval_node(a) for a in node.args]
        return func(*args)
    elif isinstance(node, ast.Name):
        func = _SAFE_FUNCS.get(node.id)
        if func is not None:
            val = func()
            if isinstance(val, (int, float)):
                return val
        raise ValueError(f"不支持的变量: {node.id}")
    raise ValueError(f"不支持的表达式节点: {type(node).__name__}")


def _safe_math_eval(expr: str) -> float:
    """安全地求值数学表达式，仅允许白名单运算符和函数。"""
    tree = ast.parse(expr.strip(), mode="eval")
    return _safe_eval_node(tree.body)

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
    try:
        result = _safe_math_eval(expr)
    except Exception as e:
        return f"计算错误: {e}"
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
        delta_map = {
            "天": timedelta(days=num),
            "小时": timedelta(hours=num),
            "分钟": timedelta(minutes=num),
            "周": timedelta(weeks=num),
        }
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


# ── Web Search 工具 ──


@register("search", "网络搜索，参数为搜索关键词。例如 `search:Python asyncio 用法`")
def tool_search(query: str) -> str:
    """使用 DuckDuckGo 匿名搜索，返回摘要。无需 API Key。"""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query.strip(), max_results=5):
                results.append(f"- {r['title']}: {r['body'][:200]}")
        if results:
            return "\n".join(results)
        return "未找到相关搜索结果。"
    except ImportError:
        return "搜索功能不可用（缺少 duckduckgo_search 包）。pip install duckduckgo-search"
    except Exception as e:
        logger.warning(f"搜索失败: {e}")
        return f"搜索出错: {e}"


# ── 代码执行沙箱工具 ──


@register("code", "安全执行 Python 代码并返回结果。参数为 Python 表达式或语句，例如 `code:3+5*2` 或 `code:sorted([3,1,2])`")
def tool_code(code: str) -> str:
    """受限的 Python 代码沙箱。仅允许安全的内置函数和白名单模块。"""
    import ast as _ast
    import json as _json
    import math as _math

    safe_builtins = {
        "abs": abs, "all": all, "any": any, "bool": bool, "chr": chr,
        "dict": dict, "divmod": divmod, "enumerate": enumerate, "filter": filter,
        "float": float, "format": format, "frozenset": frozenset, "hash": hash,
        "hex": hex, "int": int, "isinstance": isinstance, "issubclass": issubclass,
        "iter": iter, "len": len, "list": list, "map": map, "max": max,
        "min": min, "next": next, "oct": oct, "ord": ord, "pow": pow,
        "range": range, "repr": repr, "reversed": reversed, "round": round,
        "set": set, "slice": slice, "sorted": sorted, "str": str,
        "sum": sum, "tuple": tuple, "type": type, "zip": zip,
        "True": True, "False": False, "None": None,
        "json": _json, "math": _math,
        "datetime": __import__("datetime"),
        "collections": __import__("collections"),
        "itertools": __import__("itertools"),
    }
    safe_builtins["__builtins__"] = {k: safe_builtins[k] for k in ["abs", "all", "any", "bool",
        "dict", "enumerate", "filter", "float", "int", "isinstance", "len", "list",
        "map", "max", "min", "range", "repr", "round", "set", "sorted", "str",
        "sum", "tuple", "type", "zip", "True", "False", "None"]}

    try:
        tree = _ast.parse(code.strip(), mode="exec")
        # Basic safety: reject import statements, exec, eval, __
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import | _ast.ImportFrom) and not any(
                alias.name in ("datetime", "collections", "itertools", "math", "json")
                for alias in (node.names if isinstance(node, _ast.Import) else [node])
            ):
                return "代码执行被拒绝：不允许导入外部模块"
            if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name) and node.func.id in ("exec", "eval", "compile", "__import__"):
                return "代码执行被拒绝：不允许调用危险函数"

        # Try eval() first for simple expressions (captures return value)
        try:
            expr_tree = _ast.parse(code.strip(), mode="eval")
            result = eval(compile(expr_tree, "<sandbox>", "eval"), safe_builtins)
            return str(result)
        except SyntaxError:
            pass  # Not an expression, fall through to exec

        local_ns = {}
        exec(compile(tree, "<sandbox>", "exec"), safe_builtins, local_ns)
        # Return the last assigned value
        for k in reversed(list(local_ns.keys())):
            if not k.startswith("_"):
                return str(local_ns[k])
        return "执行成功（无返回值）"
    except Exception as e:
        return f"代码执行错误: {e}"


@register("api", "调用外部 HTTP API。参数格式为 `GET|https://api.example.com` 或 `POST|url|body`")
def tool_api(arg: str) -> str:
    """调用 HTTP API 获取实时数据"""
    try:
        import json as _json
        import urllib.error
        import urllib.request

        parts = arg.strip().split("|", 2)
        method = parts[0].upper() if parts else "GET"
        url = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) > 2 else None

        if not url:
            return "API 调用错误: 缺少 URL"

        if not url.startswith(("http://", "https://")):
            return "API 调用错误: 仅支持 HTTP/HTTPS"

        req = urllib.request.Request(url, method=method)
        req.add_header("User-Agent", "BrianRAG/2.1")
        req.add_header("Accept", "application/json")

        if body and method in ("POST", "PUT", "PATCH"):
            req.add_header("Content-Type", "application/json")
            req.data = body.encode()

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode()
            # 截断过长响应
            if len(data) > 4000:
                try:
                    obj = _json.loads(data)
                    return _json.dumps(obj, indent=2, ensure_ascii=False)[:4000]
                except Exception:
                    return data[:4000] + "...(truncated)"
            return data
    except urllib.error.HTTPError as e:
        return f"API 错误: HTTP {e.code}"
    except Exception as e:
        return f"API 调用失败: {e}"


@register("file_read", "读取已索引文档的内容。参数为文件名或路径片段")
def tool_file_read(path: str) -> str:
    """安全读取 data/ 目录下的文件"""
    import os

    from config import Config

    clean = os.path.basename(path.strip())
    target = os.path.join(Config.DATA_DIR, clean)
    if not os.path.isfile(target):
        # 尝试递归搜索
        for root, _dirs, files in os.walk(Config.DATA_DIR):
            for f in files:
                if f == clean or clean in f:
                    target = os.path.join(root, f)
                    break
    if not os.path.isfile(target):
        return f"文件未找到: {clean}"

    try:
        with open(target, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if len(content) > 5000:
            content = content[:5000] + f"\n...(共 {len(content)} 字符，已截断)"
        return content
    except Exception as e:
        return f"文件读取错误: {e}"


# ── 初始化 ──
logger.info(f"工具模块已加载: {list(_registry.keys())}")
