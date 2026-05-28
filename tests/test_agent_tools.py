"""Agent 工具测试 — calc/time/unit/search/code/api/file"""



class TestCalcTool:
    def test_basic_math(self):
        from core.tools import tool_calc
        r = tool_calc("2+3*4")
        assert "14" in r

    def test_function(self):
        from core.tools import tool_calc
        r = tool_calc("sqrt(16)")
        assert "4" in r

    def test_error(self):
        from core.tools import tool_calc
        r = tool_calc("1/0")
        assert "错误" in r.lower() or "error" in r.lower()


class TestTimeTool:
    def test_now_returns_date(self):
        from core.tools import tool_time
        r = tool_time("now")
        assert "202" in r  # year

    def test_unknown_arg(self):
        from core.tools import tool_time
        r = tool_time("abc")
        assert "202" in r  # falls back to now


class TestUnitTool:
    def test_km_to_m(self):
        from core.tools import tool_unit
        r = tool_unit("10km->m")
        assert "10000" in r

    def test_invalid(self):
        from core.tools import tool_unit
        r = tool_unit("invalid")
        assert "格式错误" in r


class TestSearchTool:
    def test_search_returns_string(self):
        from core.tools import tool_search
        r = tool_search("Python programming")
        assert isinstance(r, str)
        assert len(r) > 0


class TestCodeTool:
    def test_simple_expression(self):
        from core.tools import tool_code
        r = tool_code("3 + 5")
        assert "8" in r

    def test_list_operation(self):
        from core.tools import tool_code
        r = tool_code("sorted([3, 1, 2])")
        assert "[1, 2, 3]" in r

    def test_rejected_import(self):
        from core.tools import tool_code
        r = tool_code("import os\nos.getcwd()")
        assert "拒绝" in r or "拒绝" in r

    def test_rejected_eval(self):
        from core.tools import tool_code
        r = tool_code("eval('1+1')")
        assert "拒绝" in r

    def test_error(self):
        from core.tools import tool_code
        r = tool_code("undefined_variable + 1")
        assert "错误" in r.lower()


class TestAPITool:
    def test_missing_url(self):
        from core.tools import tool_api
        r = tool_api("GET|")
        assert "缺少 URL" in r or "error" in r.lower()

    def test_non_http(self):
        from core.tools import tool_api
        r = tool_api("GET|ftp://example.com")
        assert "仅支持" in r or "HTTP" in r


class TestFileReadTool:
    def test_nonexistent_file(self):
        from core.tools import tool_file_read
        r = tool_file_read("nonexistent_file.txt")
        assert "未找到" in r


class TestToolRegistry:
    def test_all_tools_registered(self):
        from core.tools import _registry
        names = list(_registry.keys())
        assert "calc" in names
        assert "time" in names
        assert "unit" in names
        assert "search" in names
        assert "code" in names
        assert "api" in names
        assert "file_read" in names

    def test_execute_known_tool(self):
        from core.tools import execute_tool_call
        r = execute_tool_call("[TOOL:calc:2+2]")
        assert r is not None
        assert "4" in r

    def test_execute_unknown_tool(self):
        from core.tools import execute_tool_call
        r = execute_tool_call("[TOOL:nonexistent:arg]")
        assert "未知" in r

    def test_no_tool_in_text(self):
        from core.tools import execute_tool_call
        r = execute_tool_call("No tool here")
        assert r is None
