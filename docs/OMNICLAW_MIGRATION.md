# OmniClaw 功能迁移指南

本文档详述了将 OmniClaw 的核心功能迁移到 mini-openClaw 的完整方案。

## 目录

1. [架构对比](#架构对比)
2. [功能迁移清单](#功能迁移清单)
3. [详细实现文档](#详细实现文档)

---

## 架构对比

### OmniClaw 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    OmniClaw (Bun/Node.js)                    │
├─────────────────────────────────────────────────────────────┤
│  Channels (WhatsApp, Discord, Telegram, Slack)              │
│       ↓                                                      │
│  Message Router → Group Queue → Container Backend           │
│       ↓                                                      │
│  Claude Agent SDK (spawned as subprocess)                   │
│       ↓                                                      │
│  Isolated Container (Apple Container / Docker)              │
└─────────────────────────────────────────────────────────────┘
```

**关键特性：**
- 单一 Bun 进程协调所有消息和 agent
- Agent 运行在隔离的 Linux 容器中
- 每个 group 有独立的 filesystem 和内存
- IPC 通过文件系统进行通信
- 多 agent 团队支持（teammates）

### mini-openClaw 架构（当前）

```
┌─────────────────────────────────────────────────────────────┐
│              mini-openClaw (Python/FastAPI)                  │
├─────────────────────────────────────────────────────────────┤
│  REST API → LangChain Agent → Skills                        │
│       ↓                                                      │
│  Session Storage (JSON)                                     │
└─────────────────────────────────────────────────────────────┘
```

**当前状态：**
- FastAPI 后端提供聊天接口
- LangChain 作为 agent 框架
- 基础的 session 管理
- 无容器隔离
- 无多渠道支持

---

## 功能迁移清单

### 1. 沙盒/容器隔离系统 🔲

**OmniClaw 实现：**
- `src/backends/` - 后端抽象层
- `src/mount-security.ts` - 挂载安全验证
- `src/path-security.ts` - 路径遍历防护
- Container isolation via Apple Container / Docker

**迁移目标：**
- [ ] 设计 Python 容器运行时抽象层
- [ ] 实现卷挂载安全管理
- [ ] 实现 per-group 隔离文件系统
- [ ] 添加路径遍历防护

**实现优先级：** 高（安全基础）

---

### 2. Multi-Agent 系统 🔲

**OmniClaw 实现：**
- Agent-Channel decoupling (`types.ts: Agent`, `ChannelSubscription`)
- IPC 通信系统 (`src/ipc.ts`)
- Share requests between agents (`src/ipc.ts: PendingShareRequest`)
- Agent teams via Claude Agent SDK teammate system

**迁移目标：**
- [ ] 设计 agent 注册和发现系统
- [ ] 实现 IPC 通信机制（推荐 Redis 或 SQLite queue）
- [ ] 实现 agent 间消息路由
- [ ] 集成 LangChain 多 agent 协作

**实现优先级：** 高（核心架构）

---

### 3. Discord 集成 🔲

**OmniClaw 实现：**
- `src/channels/discord.ts` - Discord.js 实现
- Multi-bot support (`DISCORD_BOTS` config)
- Server/guild context isolation
- Thread support for streaming intermediate output

**迁移目标：**
- [ ] 使用 `discord.py` 实现 channel 接口
- [ ] 实现多 bot 支持
- [ ] 实现 server 级别的 context 隔离
- [ ] 添加 thread 支持用于流式输出

**实现优先级：** 中

---

### 4. WhatsApp 集成 🔲

**OmniClaw 实现：**
- `src/channels/whatsapp.ts` - Baileys 实现
- QR code authentication flow
- Group metadata sync
- Voice message transcription (via Whisper API)
- Circuit breaker for reconnect loops

**迁移目标：**
- [ ] 使用 `whatsapp-business-sdk` 或 `pywhatkit` 实现
- [ ] 实现 QR 认证流程
- [ ] 实现群组元数据同步
- [ ] 添加语音消息转录支持

**实现优先级：** 中

---

### 5. Telegram 集成 🔲

**OmniClaw 实现：**
- `src/channels/telegram.ts` - Grammy 实现
- Command handling (`/chatid`, `/ping`)
- Group chat support
- Reaction support (emoji)
- Markdown formatting via `telegramify-markdown`

**迁移目标：**
- [ ] 使用 `python-telegram-bot` 或 `aiogram` 实现
- [ ] 实现命令处理
- [ ] 支持群组聊天
- [ ] 添加反应支持

**实现优先级：** 中

---

### 6. RAG/上下文管理 ✅

**OmniClaw 实现：**
- Per-group context (`groups/{name}/CLAUDE.md`)
- Session management (`src/db.ts: sessions table`)
- Context layers: agent/server/category/channel
- Message history in SQLite
- User registry for mentions (`src/ipc.ts: updateUserRegistry`)

**迁移目标：**
- [x] 实现 per-group 上下文存储
- [x] 增强 session 管理（支持 fork/merge）
- [x] 实现多层上下文系统
- [x] 消息历史持久化
- [ ] 用户提及注册表

**实现状态：** 已完成核心功能
- `backend/context/layers.py` - 多层上下文管理
- `backend/context/rag.py` - RAG 检索
- `backend/core/prompt.py` - 支持上下文的系统提示
- `backend/core/agent_runtime.py` - 支持上下文的 agent 运行时
- `backend/tests/unit/test_context_layers.py` - 上下文测试
- `backend/tests/unit/test_rag.py` - RAG 测试

**实现优先级：** 高（已完成）

---

### 7. 任务调度系统 ✅

**OmniClaw 实现：**
- `src/task-scheduler.ts` - 调度器
- Cron/interval/once scheduling
- Task run logging (`task_run_logs` table)
- Streaming intermediate results to threads
- IPC-based task management

**迁移目标：**
- [x] 实现调度器（推荐 APScheduler）
- [x] 支持 cron/interval/once
- [x] 任务执行日志
- [ ] 流式输出支持（需要渠道集成后实现）
- [ ] IPC 任务管理接口（需要 Multi-Agent 系统后实现）

**实现状态：** 已完成核心功能
- `backend/scheduler/task_scheduler.py` - 任务调度器
- `backend/scheduler/__init__.py` - 包导出
- `backend/tests/unit/test_scheduler.py` - 调度器测试
- 支持 cron/interval/once 调度
- 支持任务持久化
- 支持执行日志
- 支持错误重试

**实现优先级：** 中（已完成）

---

## 详细实现文档

### 一、容器隔离系统设计

#### 1.1 架构设计

```python
# backend/container/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class VolumeMount:
    host_path: str
    container_path: str
    read_only: bool = False

@dataclass
class ContainerConfig:
    image: str
    command: List[str]
    mounts: List[VolumeMount]
    memory_mb: int = 4096
    network_mode: str = "none"  # "none" | "bridge" | "host"
    timeout_ms: int = 300000

class ContainerBackend(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the container runtime"""
        pass

    @abstractmethod
    async def run_agent(
        self,
        config: ContainerConfig,
        env: dict,
        on_output: callable
    ) -> ContainerResult:
        """Run an agent in an isolated container"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the container runtime"""
        pass
```

#### 1.2 Docker 后端实现

```python
# backend/container/docker_backend.py
import asyncio
from aiodocker import Docker
from .base import ContainerBackend, ContainerConfig, ContainerResult

class DockerContainerBackend(ContainerBackend):
    def __init__(self, image: str = "omniclaw-agent:latest"):
        self.docker = Docker()
        self.image = image

    async def initialize(self) -> None:
        # Ensure image is pulled
        try:
            await self.docker.images.inspect(self.image)
        except:
            await self.docker.images.pull(self.image)

    async def run_agent(
        self,
        config: ContainerConfig,
        env: dict,
        on_output: callable
    ) -> ContainerResult:
        container = await self.docker.containers.create_or_replace(
            name=f"agent-{env['AGENT_ID']}",
            config={
                "Image": self.image,
                "Cmd": config.command,
                "Env": [f"{k}={v}" for k, v in env.items()],
                "HostConfig": {
                    "Binds": [
                        f"{m.host_path}:{m.container_path}:"
                        f"{'ro' if m.read_only else 'rw'}"
                        for m in config.mounts
                    ],
                    "Memory": config.memory_mb * 1024 * 1024,
                    "NetworkMode": config.network_mode,
                },
            }
        )
        # ... stream output
```

#### 1.3 安全挂载验证

```python
# backend/container/security.py
from pathlib import Path
import re

class MountSecurity:
    def __init__(self, allowed_roots: List[str], blocked_patterns: List[str]):
        self.allowed_roots = [Path(r).expanduser().resolve() for r in allowed_roots]
        self.blocked_patterns = blocked_patterns

    def validate_mount(self, host_path: str) -> bool:
        """Validate a path can be mounted"""
        resolved = Path(host_path).expanduser().resolve()

        # Check for path traversal
        if ".." in host_path:
            return False

        # Check against allowed roots
        if not any(str(resolved).startswith(str(root)) for root in self.allowed_roots):
            return False

        # Check blocked patterns
        for pattern in self.blocked_patterns:
            if re.match(pattern, str(resolved)):
                return False

        return True
```

---

### 二、Multi-Agent 系统设计

#### 2.1 Agent 注册和发现

```python
# backend/agents/registry.py
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

class BackendType(Enum):
    LOCAL = "local"
    DOCKER = "docker"
    APPLE_CONTAINER = "apple-container"

class AgentRuntime(Enum):
    LANGCHAIN = "langchain"
    CLAUDE_SDK = "claude-sdk"
    OPENCODE = "opencode"

@dataclass
class Agent:
    id: str
    name: str
    description: Optional[str]
    folder: str
    backend: BackendType
    runtime: AgentRuntime
    is_admin: bool = False
    server_folder: Optional[str] = None

class AgentRegistry:
    def __init__(self, db):
        self.db = db

    def register_agent(self, agent: Agent) -> None:
        """Register a new agent"""
        pass

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        pass

    def get_all_agents(self) -> Dict[str, Agent]:
        """Get all registered agents"""
        pass
```

#### 2.2 IPC 通信系统

```python
# backend/ipc/manager.py
import asyncio
import json
from dataclasses import dataclass
from typing import Dict, Callable, Any

@dataclass
class IpcMessage:
    type: str
    source_agent: str
    target_agent: Optional[str]
    payload: Dict[str, Any]
    timestamp: str

class IPCManager:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.handlers: Dict[str, Callable] = {}
        self.queues: Dict[str, asyncio.Queue] = {}

    def register_handler(self, msg_type: str, handler: Callable):
        """Register a message handler"""
        self.handlers[msg_type] = handler

    async def send_message(
        self,
        message: IpcMessage,
        target_agent: str
    ) -> None:
        """Send a message to an agent"""
        queue = self.queues.get(target_agent)
        if queue:
            await queue.put(message)

    async def process_messages(self, agent_id: str) -> None:
        """Process messages for an agent"""
        queue = self.queues.get(agent_id)
        if not queue:
            return

        while True:
            msg = await queue.get()
            handler = self.handlers.get(msg.type)
            if handler:
                await handler(msg)
```

#### 2.3 消息路由

```python
# backend/ipc/router.py
from typing import Dict, List, Optional

class ChannelSubscription:
    def __init__(
        self,
        channel_jid: str,
        agent_id: str,
        trigger: str,
        requires_trigger: bool = True,
        priority: int = 100
    ):
        self.channel_jid = channel_jid
        self.agent_id = agent_id
        self.trigger = trigger
        self.requires_trigger = requires_trigger
        self.priority = priority

class MessageRouter:
    def __init__(self):
        self.subscriptions: Dict[str, List[ChannelSubscription]] = {}

    def route_message(
        self,
        channel_jid: str,
        content: str,
        mentions: List[str]
    ) -> List[str]:
        """
        Route a message to the appropriate agents.
        Returns list of agent IDs that should process this message.
        """
        target_agents = []

        # Check for trigger mentions
        for sub in self.subscriptions.get(channel_jid, []):
            if sub.trigger in content or sub.trigger in mentions:
                if sub.requires_trigger or sub.trigger in mentions:
                    target_agents.append(sub.agent_id)

        return target_agents
```

---

### 三、多渠道集成

#### 3.1 Channel 抽象接口

```python
# backend/channels/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable

@dataclass
class InboundMessage:
    id: str
    chat_jid: str
    sender: str
    sender_name: str
    content: str
    timestamp: str
    is_from_me: bool = False
    mentions: list = None

@dataclass
class ChatMetadata:
    jid: str
    name: str
    platform: str
    discord_guild_id: Optional[str] = None

class Channel(ABC):
    name: str
    prefix_assistant_name: bool = True

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the platform"""
        pass

    @abstractmethod
    async def send_message(
        self,
        jid: str,
        text: str,
        reply_to_message_id: Optional[str] = None
    ) -> Optional[str]:
        """Send a message, returns the platform message ID"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if channel is connected"""
        pass

    @abstractmethod
    def owns_jid(self, jid: str) -> bool:
        """Check if this channel handles this JID"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform"""
        pass

    # Optional capabilities
    async def set_typing(self, jid: str, is_typing: bool) -> None:
        """Show typing indicator"""
        pass

    async def create_thread(self, jid: str, message_id: str, name: str):
        """Create a thread for streaming output"""
        pass

    async def send_to_thread(self, thread, text: str) -> None:
        """Send message to a thread"""
        pass
```

#### 3.2 Discord 实现示例

```python
# backend/channels/discord_channel.py
import discord
from discord.ext import commands
from typing import Optional, Callable
from .base import Channel, InboundMessage, ChatMetadata

class DiscordChannel(Channel):
    name = "discord"
    prefix_assistant_name = False

    def __init__(
        self,
        bot_id: str,
        token: str,
        on_message: Callable,
        intents: Optional[discord.Intents] = None
    ):
        self.bot_id = bot_id
        self.token = token
        self.on_message = on_message
        self.on_chat_metadata = None

        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True

        self.bot = commands.Bot(command_prefix="!", intents=intents)

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return
            await self._handle_message(message)

    async def connect(self) -> None:
        await self.bot.start(self.token)

    async def send_message(
        self,
        jid: str,
        text: str,
        reply_to_message_id: Optional[str] = None
    ) -> Optional[str]:
        # Parse JID: dc:<channel_id> or dc:<guild_id>:<channel_id>
        parts = jid.replace("dc:", "").split(":")
        channel_id = int(parts[-1])

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return None

        if reply_to_message_id:
            # Reply to specific message
            pass

        msg = await channel.send(text)
        return str(msg.id)

    async def _handle_message(self, message: discord.Message):
        # Process message and route to agent
        inbound = InboundMessage(
            id=str(message.id),
            chat_jid=f"dc:{message.channel.id}",
            sender=str(message.author.id),
            sender_name=message.author.display_name,
            content=message.content,
            timestamp=message.created_at.isoformat(),
            is_from_me=message.author.id == self.bot.user.id,
            mentions=[
                {"id": str(u.id), "name": u.display_name, "platform": "discord"}
                for u in message.mentions
            ]
        )
        await self.on_message(inbound)
```

---

### 四、RAG/上下文管理

#### 4.1 多层上下文系统

```python
# backend/context/layers.py
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class ContextLayer:
    """A layer of context with its own storage"""
    name: str
    path: Path
    read_only: bool = False
    description: str = ""

class ContextManager:
    """
    Manages multi-layer context:
    - agent: Personal identity and notes (RW)
    - category: Team workspace (RW)
    - channel: Specific channel context (RW)
    - server: Shared server context (RO)
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def get_context_for_agent(
        self,
        agent_id: str,
        channel_jid: Optional[str] = None,
        server_id: Optional[str] = None
    ) -> List[ContextLayer]:
        """Get all context layers for an agent"""
        layers = []

        # Agent context (always RW)
        agent_dir = self.base_dir / "agents" / agent_id
        if agent_dir.exists():
            layers.append(ContextLayer(
                name="agent",
                path=agent_dir,
                read_only=False,
                description="Personal identity and notes"
            ))

        # Category context (RW if set)
        if channel_jid:
            category_dir = self._get_category_dir(channel_jid)
            if category_dir:
                layers.append(ContextLayer(
                    name="category",
                    path=category_dir,
                    read_only=False,
                    description="Team workspace"
                ))

        # Server context (RO)
        if server_id:
            server_dir = self.base_dir / "servers" / server_id
            if server_dir.exists():
                layers.append(ContextLayer(
                    name="server",
                    path=server_dir,
                    read_only=True,
                    description="Shared server context"
                ))

        return layers

    def build_system_prompt(self, layers: List[ContextLayer]) -> str:
        """Build system prompt from context layers"""
        prompt_parts = []

        for layer in layers:
            claude_md = layer.path / "CLAUDE.md"
            if claude_md.exists():
                prompt_parts.append(f"# {layer.name.capitalize()} Context\n")
                prompt_parts.append(claude_md.read_text())

        return "\n\n".join(prompt_parts)
```

#### 4.2 Session 管理

```python
# backend/context/sessions.py
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.messages import BaseMessage, messages_to_dict, messages_from_dict

class SessionManager:
    def __init__(
        self,
        sessions_dir: Path,
        max_age_hours: int = 24
    ):
        self.sessions_dir = sessions_dir
        self.max_age = timedelta(hours=max_age_hours)

    def get_session(self, group_folder: str) -> Optional[str]:
        """Get session ID for a group"""
        session_file = self.sessions_dir / f"{group_folder}.json"
        if not session_file.exists():
            return None

        data = json.loads(session_file.read_text())
        created_at = datetime.fromisoformat(data["created_at"])

        if datetime.now() - created_at > self.max_age:
            session_file.unlink()
            return None

        return data["session_id"]

    def set_session(self, group_folder: str, session_id: str) -> None:
        """Set session ID for a group"""
        session_file = self.sessions_dir / f"{group_folder}.json"
        data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat()
        }
        session_file.write_text(json.dumps(data, indent=2))

    def load_messages(self, session_id: str) -> List[BaseMessage]:
        """Load message history for a session"""
        message_file = self.sessions_dir / f"{session_id}_messages.json"
        if not message_file.exists():
            return []

        data = json.loads(message_file.read_text())
        return messages_from_dict(data)

    def save_messages(
        self,
        session_id: str,
        messages: List[BaseMessage]
    ) -> None:
        """Save message history for a session"""
        message_file = self.sessions_dir / f"{session_id}_messages.json"
        data = messages_to_dict(messages)
        message_file.write_text(json.dumps(data, indent=2))
```

---

### 五、任务调度系统

#### 5.1 调度器实现

```python
# backend/scheduler/task_scheduler.py
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

@dataclass
class ScheduledTask:
    id: str
    group_folder: str
    chat_jid: str
    prompt: str
    schedule_type: str  # "cron" | "interval" | "once"
    schedule_value: str  # cron expression or interval seconds
    context_mode: str  # "group" | "isolated"
    next_run: Optional[datetime]
    last_run: Optional[datetime]
    last_result: Optional[str]
    status: str  # "active" | "paused" | "completed"
    created_at: datetime

class TaskScheduler:
    def __init__(self, agent_runner: Callable):
        self.scheduler = AsyncIOScheduler()
        self.agent_runner = agent_runner
        self.tasks: Dict[str, ScheduledTask] = {}

    def add_task(self, task: ScheduledTask) -> None:
        """Add a scheduled task"""
        trigger = self._create_trigger(task)

        self.scheduler.add_job(
            self._run_task,
            trigger,
            args=[task.id],
            id=task.id,
            replace_existing=True
        )

        self.tasks[task.id] = task
        self.scheduler.start()

    def _create_trigger(self, task: ScheduledTask):
        """Create APScheduler trigger from task config"""
        if task.schedule_type == "cron":
            # Parse cron expression: "minute hour day month day_of_week"
            parts = task.schedule_value.split()
            return CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
            )
        elif task.schedule_type == "interval":
            seconds = int(task.schedule_value)
            return IntervalTrigger(seconds=seconds)
        elif task.schedule_type == "once":
            run_at = datetime.fromisoformat(task.schedule_value)
            return DateTrigger(run_date=run_at)

    async def _run_task(self, task_id: str) -> None:
        """Execute a scheduled task"""
        task = self.tasks.get(task_id)
        if not task or task.status != "active":
            return

        try:
            # Run the agent with the task prompt
            result = await self.agent_runner(
                group_folder=task.group_folder,
                prompt=task.prompt,
                isolated=(task.context_mode == "isolated")
            )

            # Update task state
            task.last_run = datetime.now()
            task.last_result = result

            # Calculate next run
            if task.schedule_type == "once":
                task.status = "completed"
            else:
                task.next_run = self._calculate_next_run(task)

        except Exception as e:
            task.last_result = f"Error: {str(e)}"
            task.next_run = self._calculate_next_run(task)

    def _calculate_next_run(self, task: ScheduledTask) -> Optional[datetime]:
        """Calculate next run time for a task"""
        job = self.scheduler.get_job(task.id)
        if job:
            return job.next_run_time
        return None
```

---

## 迁移顺序建议

1. **阶段 1：基础架构**（1-2 周）
   - 容器隔离系统
   - 上下文管理系统
   - Session 管理

2. **阶段 2：核心功能**（2-3 周）
   - Multi-Agent 系统
   - IPC 通信
   - 任务调度器

3. **阶段 3：渠道集成**（2-3 周）
   - Discord 集成
   - WhatsApp 集成
   - Telegram 集成

4. **阶段 4：优化和测试**（1-2 周）
   - 性能优化
   - 安全审计
   - 集成测试

---

## 关键技术决策

### 容器运行时选择

| 方案 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| Docker | 成熟、跨平台 | 重量级 | Linux 服务器 |
| Apple Container | 轻量、Apple Silicon | 仅 macOS | macOS 本地开发 |
| 本地进程 | 最简单 | 隔离性差 | 开发/测试环境 |

### IPC 通信选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| Redis | 高性能、支持发布订阅 | 需要额外服务 |
| SQLite Queue | 简单、无额外依赖 | 并发性能较低 |
| 文件系统 | 简单、可调试 | 轮询延迟 |

**推荐：** 开发环境使用文件系统，生产环境使用 Redis

### Agent 框架选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| LangChain | 成熟、生态丰富 | 较重 |
| Claude Agent SDK | 原生支持、最强 | 仅限 Claude |
| 自定义 | 灵活、轻量 | 需要自己实现 |

**推荐：** 继续使用 LangChain，保持与 mini-openClaw 一致

---

## 迁移进度总结

### 已完成功能 ✅

| 功能 | 状态 | 文件 |
|------|------|------|
| RAG/上下文管理 | ✅ 已完成 | `backend/context/` |
| 任务调度系统 | ✅ 已完成 | `backend/scheduler/` |
| 多层上下文系统 | ✅ 已完成 | `backend/context/layers.py` |
| Session 管理 | ✅ 已完成 | `backend/core/sessions.py` |
| Agent 运行时集成 | ✅ 已完成 | `backend/core/agent_runtime.py` |

### 待迁移功能 🔲

| 功能 | 优先级 | 预计工作量 |
|------|--------|------------|
| 容器隔离系统 | 高 | 3-4 天 |
| Multi-Agent 系统 | 高 | 4-5 天 |
| Discord 集成 | 中 | 2-3 天 |
| WhatsApp 集成 | 中 | 3-4 天 |
| Telegram 集成 | 中 | 2-3 天 |
| IPC 通信 | 中 | 2-3 天 |

### 下一步建议

1. **容器隔离系统** - 这是安全基础，建议优先实现
   - 先实现本地进程隔离（最简单）
   - 再实现 Docker 后端（生产环境）
   - 最后实现 Apple Container（macOS 特定）

2. **Multi-Agent 系统** - 这是核心架构
   - 先实现 Agent Registry
   - 再实现 IPC 通信（基于 Redis 或 SQLite）
   - 最后实现消息路由

3. **渠道集成** - 可以并行实现
   - Discord (discord.py)
   - Telegram (python-telegram-bot)
   - WhatsApp (需要 WhatsApp Business API)

---

## 参考资料

- [OmniClaw GitHub](https://github.com/omniaura/omniclaw)
- [OmniClaw SDK Deep Dive](../omniclaw/docs/SDK_DEEP_DIVE.md)
- [OmniClaw Security Model](../omniclaw/docs/SECURITY.md)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
