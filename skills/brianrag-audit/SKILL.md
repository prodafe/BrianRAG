---
name: brianrag-audit
description: "BrianRAG 代码审计 — 全面检查 bugs、性能、安全、资源泄漏。当用户说"检查一下"、"有没有bug"、"审计代码"、"全面检查"、"audit"、"review"时自动触发。Use when user asks to audit code, find bugs, review quality, or check for issues."
---

# BrianRAG 代码审计

对 BrianRAG 项目（`C:\Users\86153\PycharmProjects\PythonProject2`）进行全面的代码质量和安全审计。

---

## 审计清单

### 1. 安全问题
- [ ] 裸 `except:` 使用
- [ ] SQL 注入风险（f-string 拼接 SQL）
- [ ] XSS 风险（innerHTML 未转义用户输入）
- [ ] 路径穿越（文件上传/读取路径未净化）
- [ ] 命令注入（os.system/subprocess 未过滤输入）
- [ ] 硬编码密钥/密码
- [ ] AST eval 安全性

### 2. 资源管理
- [ ] ThreadPoolExecutor 是否 shutdown
- [ ] `fitz.open()` / `open()` 是否用 with 语句
- [ ] Redis 连接池是否正确复用
- [ ] psycopg 连接是否正确关闭
- [ ] requestAnimationFrame/setInterval 是否取消

### 3. 错误处理
- [ ] `except Exception: pass` 静默吞错误
- [ ] API 端点是否有统一错误响应
- [ ] 流式响应错误是否正确终止
- [ ] 检索失败是否有降级策略
- [ ] 模型加载失败是否优雅降级

### 4. 并发安全
- [ ] 全局状态是否有锁保护
- [ ] 文件写入是否线程安全（pickle dump）
- [ ] Redis 操作是否原子
- [ ] 懒加载是否有竞态条件

### 5. 前端问题
- [ ] DOM 查询是否有 null 检查
- [ ] innerHTML 用户数据是否经过 `esc()` 转义（XSS）
- [ ] onclick 属性中的动态值是否转义
- [ ] fetch 请求是否有错误处理
- [ ] `catch(e){}` 是否有日志（禁止静默）
- [ ] 事件监听是否正确清理
- [ ] 快速点击是否有防抖
- [ ] SSE 流断开是否正确恢复

### 6. 配置一致性
- [ ] `_Settings` 和 `_Config` 字段是否一致
- [ ] 环境变量前缀 `BRIAN_` 是否正确
- [ ] 默认值是否合理

## 审计脚本

```bash
# 裸 except
grep -rn "except\s*:" --include="*.py" . --exclude-dir=.venv

# 静默 pass
grep -rn "except.*:\s*\n\s*pass" --include="*.py" . --exclude-dir=.venv

# ThreadPoolExecutor 未 shutdown
grep -rn "ThreadPoolExecutor" --include="*.py" . --exclude-dir=.venv

# 文件未用 with
grep -rn "= open\|= fitz.open" --include="*.py" . --exclude-dir=.venv

# f-string SQL
grep -rn "f\".*DROP\|f\".*SELECT\|f\".*INSERT\|f\".*DELETE" --include="*.py" . --exclude-dir=.venv

# print 残留
grep -rn "^[^#]*\bprint(" --include="*.py" . --exclude-dir=.venv

# innerHTML XSS (前端)
grep -rn "innerHTML" --include="*.html" --include="*.js" . --exclude-dir=.venv --exclude-dir=lib

# 静默 catch(e){} (前端)
grep -rn "catch\s*(e)\s*{\s*}" --include="*.js" . --exclude-dir=lib
```

## 审计报告格式

```markdown
| 严重度 | 文件:行 | 问题 | 修复 |
|--------|---------|------|------|
| 🔴高 | core/xxx.py:42 | ... | ... |
| 🟡中 | api/xxx.py:15 | ... | ... |
| 🟢低 | utils/xxx.py:8 | ... | ... |
```
