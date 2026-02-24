# mini-openClaw 第二阶段多审查汇总文档

## 功能审查员1（实现完整性）

### 审查范围
- `backend/app.py`
- `backend/core/agent_runtime.py`
- `backend/core/sessions.py`
- `backend/core/skills.py`

### 主要发现
1. `/api/chat` 缺少请求约束，空消息与非法 `session_id` 没有在入口层拦截。
2. 文件路径安全校验使用字符串 `startswith`，存在前缀绕过风险。
3. 关键行为（模型降级、会话落盘）缺少自动回归测试，后续改动容易引入回归。

### 结论
- 核心链路可运行，但完整性与安全边界不足，需要补齐输入校验和可验证保障。

## 测试审查员2（测试充分性）

### 现状
- 仓库无 `pytest` 测试集，单元/集成/端到端测试均缺失。

### 要求
1. 单元测试：覆盖 `sessions` 与 `skills` 核心逻辑。
2. 集成测试：覆盖 FastAPI 关键 API（chat/files）。
3. 端到端测试：覆盖 runtime 模型降级 + 会话持久化全链路。

### 结论
- 测试体系不达标，必须建立三层测试基线。

## 汇总优化方案

### 优先级 P0
1. 在 API 入参层增加 `message/session_id` 校验。
2. 修复路径安全校验，改为 `Path.relative_to` 语义校验。
3. 建立测试体系并跑通：
   - 单元测试
   - 集成测试
   - 端到端测试

### 实施结果
1. 已完成：`backend/app.py` 增加 `Field` 约束（`message` 长度、`session_id` 正则）。
2. 已完成：`backend/app.py` 路径校验改为 `relative_to(PROJECT_ROOT)`。
3. 已完成：新增 `backend/tests/` 三层测试与 `pytest` 依赖。
