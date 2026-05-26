# 贡献指南

欢迎为 BrianRAG 做贡献！无论是报告 bug、建议新功能还是提交代码，都非常感谢。

## 开发环境

```bash
git clone https://github.com/your-org/brianrag.git
cd brianrag
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 代码规范

- Python 3.10+
- 类型注解：所有公共方法需标注参数和返回值类型
- 命名：`snake_case` 变量/函数，`PascalCase` 类名
- 行宽：120 字符

运行检查：

```bash
ruff check .           # lint
ruff format --check .  # 格式检查
mypy core/             # 类型检查
```

## 运行测试

```bash
pytest                              # 全部（不含慢测试）
pytest -m "not integration"         # 跳过集成测试
pytest tests/test_generator.py -v   # 单个文件
```

## 提交规范

- `feat: 新增功能描述`
- `fix: 修复问题描述`
- `docs: 文档更新`
- `refactor: 重构描述`
- `test: 测试相关`

## Pull Request 流程

1. Fork 仓库并创建功能分支
2. 编写代码 + 测试
3. 运行 `ruff check . && pytest`
4. 提交 PR，描述改动内容和原因

CI 会自动运行 lint + typecheck + test，全部通过后才能合并。
