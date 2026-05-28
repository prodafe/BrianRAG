"""Tests for core/tools.py — safe math evaluator"""

import pytest

from core.tools import _safe_math_eval


class TestSafeMathEval:
    def test_basic_arithmetic(self):
        assert abs(_safe_math_eval("2+3*4") - 14.0) < 0.001

    def test_sqrt(self):
        assert abs(_safe_math_eval("sqrt(16)") - 4.0) < 0.001

    def test_sin(self):
        assert abs(_safe_math_eval("sin(pi/2)") - 1.0) < 0.001

    def test_nested_expr(self):
        assert abs(_safe_math_eval("sqrt(3*3+4*4)") - 5.0) < 0.001

    def test_rejects_import(self):
        with pytest.raises(ValueError):
            _safe_math_eval("__import__('os')")

    def test_rejects_attribute_access(self):
        with pytest.raises(ValueError):
            _safe_math_eval("math.sqrt.__class__")

    def test_rejects_unknown_function(self):
        with pytest.raises(ValueError):
            _safe_math_eval("exec('hello')")

    def test_negative_number(self):
        assert abs(_safe_math_eval("-5") - (-5.0)) < 0.001

    def test_floor_div(self):
        assert abs(_safe_math_eval("7//2") - 3.0) < 0.001


class TestCalcTool:
    def test_calc_returns_string(self):
        from core.tools import tool_calc
        result = tool_calc("2+3")
        assert isinstance(result, str)
        assert "5" in result

    def test_calc_error_message(self):
        from core.tools import tool_calc
        result = tool_calc("__import__('os')")
        assert "Error" in result or "错误" in result


class TestTimeTool:
    def test_now_returns_date(self):
        from core.tools import tool_time
        result = tool_time("now")
        assert len(result) > 5

    def test_unknown_arg_defaults_to_now(self):
        from core.tools import tool_time
        result = tool_time("??")
        # Unknown args default to current time
        assert "202" in result  # contains year
