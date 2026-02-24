# mini-openClaw

基于 PRD 的本地 Agent 系统（后端 + 前端）。

## 后端
```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

环境变量说明：
- `OPENAI_API_KEY`：OpenAI 兼容接口的 Key
- `OPENAI_BASE_URL`：兼容接口地址（默认可用 `https://api.openai.com/v1`）
- `OPENCLAW_MODELS`：默认模型链路（当前默认 `openai:qwen3,openai:deepseek-chat`）
- `OPENCLAW_MODEL`：可选，强制指定主模型

## 前端
```bash
cd frontend
cp .env.example .env.local
npm run dev
```

访问：`http://localhost:3000`

## Git Workflow
```bash
# 1) 新建功能分支
git checkout -b feat/your-change

# 2) 开发完成后仅提交源码（.gitignore 已过滤本地产物）
git add .
git commit -m "feat: your change"

# 3) 推送并发起 PR（会触发 .github/workflows/ci.yml）
git push -u origin feat/your-change
```

如果你之前已经把 `node_modules`、`.next`、`__pycache__`、`.env` 这类文件加入过 Git，需要先从索引中移除（不删除本地文件）：
```bash
git rm -r --cached frontend/node_modules frontend/.next backend/__pycache__ backend/core/__pycache__ backend/orchestration/__pycache__ backend/tools/__pycache__ backend/sessions/*.json backend/.env
```

## Testing
```bash
cd backend
pip install -r requirements.txt
pytest tests -q
```

## 已实现能力
- FastAPI 接口：`/api/chat`、`/api/files`、`/api/sessions`
- 本地会话存储与 System Prompt 拼接
- Skills 扫描与 `SKILLS_SNAPSHOT.md` 生成
- 三栏 IDE 风格前端：Sidebar / Chat Stage / Inspector(Monaco)
- 前端已对接后端 8002 API
