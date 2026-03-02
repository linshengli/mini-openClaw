"""
Task scheduler for mini-openClaw.
Migrated from OmniClaw's task-scheduler.ts

Supports:
- Cron, interval, and once scheduling
- Task run logging
- Context isolation for scheduled tasks
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from core.paths import STORAGE_DIR


logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """
    A scheduled task definition.

    Migrated from OmniClaw's ScheduledTask interface.
    """
    id: str
    group_folder: str
    chat_jid: str
    prompt: str
    schedule_type: str  # "cron" | "interval" | "once"
    schedule_value: str  # cron expression or interval seconds
    context_mode: str  # "group" | "isolated"
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_result: Optional[str] = None
    status: str = "active"  # "active" | "paused" | "completed"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Multi-layer context support (OmniClaw migration)
    agent_id: Optional[str] = None
    server_folder: Optional[str] = None
    category_folder: Optional[str] = None
    channel_folder: Optional[str] = None

    # Error handling
    max_retries: int = 3
    retry_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage"""
        return {
            "id": self.id,
            "group_folder": self.group_folder,
            "chat_jid": self.chat_jid,
            "prompt": self.prompt,
            "schedule_type": self.schedule_type,
            "schedule_value": self.schedule_value,
            "context_mode": self.context_mode,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_result": self.last_result,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "agent_id": self.agent_id,
            "server_folder": self.server_folder,
            "category_folder": self.category_folder,
            "channel_folder": self.channel_folder,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        """Deserialize from dictionary"""
        return cls(
            id=data["id"],
            group_folder=data["group_folder"],
            chat_jid=data["chat_jid"],
            prompt=data["prompt"],
            schedule_type=data["schedule_type"],
            schedule_value=data["schedule_value"],
            context_mode=data["context_mode"],
            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None,
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            last_result=data.get("last_result"),
            status=data.get("status", "active"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            agent_id=data.get("agent_id"),
            server_folder=data.get("server_folder"),
            category_folder=data.get("category_folder"),
            channel_folder=data.get("channel_folder"),
            max_retries=data.get("max_retries", 3),
            retry_count=data.get("retry_count", 0),
            last_error=data.get("last_error"),
        )


@dataclass
class TaskRunLog:
    """
    Log entry for a task execution.
    """
    task_id: str
    run_at: datetime
    duration_ms: int
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "run_at": self.run_at.isoformat(),
            "duration_ms": self.duration_ms,
            "success": self.success,
            "result": self.result,
            "error": self.error,
        }


class TaskScheduler:
    """
    Task scheduler with OmniClaw-compatible interface.

    Features:
    - Cron, interval, and once scheduling
    - Task run logging
    - Multi-layer context support
    - Error handling and retries
    """

    def __init__(
        self,
        agent_runner: Callable,
        storage_dir: Path = STORAGE_DIR / "scheduler"
    ):
        """
        Initialize the task scheduler.

        Args:
            agent_runner: Async callable that runs an agent task
            storage_dir: Directory for task storage
        """
        self.agent_runner = agent_runner
        self.storage_dir = storage_dir
        self.tasks_dir = storage_dir / "tasks"
        self.logs_dir = storage_dir / "logs"

        # Initialize APScheduler
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {"coalesce": True, "max_instances": 1}

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC"
        )

        self._tasks: Dict[str, ScheduledTask] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the scheduler and load persisted tasks"""
        if self._initialized:
            return

        # Create storage directories
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Load persisted tasks
        await self._load_tasks()

        # Start scheduler
        self.scheduler.start()
        self._initialized = True

        logger.info("Task scheduler initialized")

    async def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Task scheduler shutdown")

    async def _load_tasks(self) -> None:
        """Load tasks from disk"""
        if not self.tasks_dir.exists():
            return

        for task_file in self.tasks_dir.glob("*.json"):
            try:
                data = json.loads(task_file.read_text())
                task = ScheduledTask.from_dict(data)

                # Restore active tasks to scheduler
                if task.status == "active":
                    self._add_to_scheduler(task)

                self._tasks[task.id] = task
                logger.info(f"Loaded task: {task.id}")
            except Exception as e:
                logger.error(f"Failed to load task from {task_file}: {e}")

    def _add_to_scheduler(self, task: ScheduledTask) -> None:
        """Add a task to the APScheduler"""
        trigger = self._create_trigger(task)

        self.scheduler.add_job(
            self._run_task,
            trigger,
            args=[task.id],
            id=task.id,
            replace_existing=True,
            name=task.id,
        )

        # Update next run time
        job = self.scheduler.get_job(task.id)
        if job and job.next_run_time:
            task.next_run = job.next_run_time

    def _create_trigger(self, task: ScheduledTask):
        """Create APScheduler trigger from task config"""
        if task.schedule_type == "cron":
            # Parse cron expression: "minute hour day month day_of_week"
            parts = task.schedule_value.split()
            if len(parts) >= 5:
                return CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
            else:
                # Default to every minute if invalid
                return CronTrigger()

        elif task.schedule_type == "interval":
            seconds = int(task.schedule_value)
            return IntervalTrigger(seconds=seconds)

        elif task.schedule_type == "once":
            run_at = datetime.fromisoformat(task.schedule_value)
            return DateTrigger(run_date=run_at)

        else:
            raise ValueError(f"Unknown schedule type: {task.schedule_type}")

    async def _run_task(self, task_id: str) -> None:
        """Execute a scheduled task"""
        task = self._tasks.get(task_id)
        if not task or task.status != "active":
            return

        start_time = datetime.now()
        success = False
        result = None
        error = None

        try:
            logger.info(f"Running scheduled task: {task_id}")

            # Run the agent with the task prompt
            # Build context from layers if specified
            result = await self.agent_runner(
                group_folder=task.group_folder,
                prompt=task.prompt,
                agent_id=task.agent_id,
                server_folder=task.server_folder,
                category_folder=task.category_folder,
                channel_folder=task.channel_folder,
            )

            success = True
            task.last_result = result
            task.retry_count = 0

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            error = str(e)
            task.last_error = error
            task.retry_count += 1

            logger.error(f"Task {task_id} failed: {error}")

            # Handle retries
            if task.retry_count >= task.max_retries:
                task.status = "paused"
                logger.warning(f"Task {task_id} paused after {task.retry_count} retries")

        finally:
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Update task state
            task.last_run = end_time
            task.updated_at = end_time

            # Update next run time
            if task.status == "active" and task.schedule_type != "once":
                job = self.scheduler.get_job(task_id)
                if job and job.next_run_time:
                    task.next_run = job.next_run_time

            # Persist task state
            await self._persist_task(task)

            # Write run log
            log_entry = TaskRunLog(
                task_id=task_id,
                run_at=start_time,
                duration_ms=duration_ms,
                success=success,
                result=result,
                error=error,
            )
            await self._write_log(task_id, log_entry)

    async def _persist_task(self, task: ScheduledTask) -> None:
        """Persist task state to disk"""
        task_file = self.tasks_dir / f"{task.id}.json"
        task_file.write_text(json.dumps(task.to_dict(), indent=2))

    async def _write_log(self, task_id: str, log: TaskRunLog) -> None:
        """Write a task run log"""
        log_file = self.logs_dir / f"{task_id}.jsonl"

        # Append to log file
        with open(log_file, "a") as f:
            f.write(json.dumps(log.to_dict()) + "\n")

    # Public API

    def add_task(self, task: ScheduledTask) -> None:
        """
        Add a new scheduled task.

        Args:
            task: Task definition
        """
        if task.id in self._tasks:
            raise ValueError(f"Task {task.id} already exists")

        self._tasks[task.id] = task

        if task.status == "active":
            self._add_to_scheduler(task)

        # Persist immediately
        asyncio.create_task(self._persist_task(task))

        logger.info(f"Added task: {task.id}")

    def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.

        Args:
            task_id: Task identifier

        Returns:
            True if task was removed
        """
        if task_id not in self._tasks:
            return False

        # Remove from scheduler
        if self.scheduler.get_job(task_id):
            self.scheduler.remove_job(task_id)

        # Remove from memory
        del self._tasks[task_id]

        # Remove from disk
        task_file = self.tasks_dir / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()

        logger.info(f"Removed task: {task_id}")
        return True

    def pause_task(self, task_id: str) -> bool:
        """Pause a task"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = "paused"
        task.updated_at = datetime.now()

        # Remove from scheduler
        if self.scheduler.get_job(task_id):
            self.scheduler.remove_job(task_id)

        asyncio.create_task(self._persist_task(task))
        return True

    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task"""
        task = self._tasks.get(task_id)
        if not task or task.status != "paused":
            return False

        task.status = "active"
        task.updated_at = datetime.now()

        # Re-add to scheduler
        self._add_to_scheduler(task)
        return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, ScheduledTask]:
        """Get all tasks"""
        return self._tasks.copy()

    def get_active_tasks(self) -> Dict[str, ScheduledTask]:
        """Get only active tasks"""
        return {k: v for k, v in self._tasks.items() if v.status == "active"}

    def get_task_logs(self, task_id: str, limit: int = 100) -> List[TaskRunLog]:
        """
        Get run logs for a task.

        Args:
            task_id: Task identifier
            limit: Maximum number of logs to return

        Returns:
            List of log entries (most recent first)
        """
        log_file = self.logs_dir / f"{task_id}.jsonl"
        if not log_file.exists():
            return []

        logs = []
        with open(log_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    logs.append(TaskRunLog(
                        task_id=data["task_id"],
                        run_at=datetime.fromisoformat(data["run_at"]),
                        duration_ms=data["duration_ms"],
                        success=data["success"],
                        result=data.get("result"),
                        error=data.get("error"),
                    ))
                except:
                    continue

        # Return most recent first
        logs.reverse()
        return logs[:limit]


# Default scheduler instance
_default_scheduler: Optional[TaskScheduler] = None


def get_scheduler(agent_runner: Callable = None) -> TaskScheduler:
    """Get or create the default scheduler instance"""
    global _default_scheduler
    if _default_scheduler is None:
        if agent_runner is None:
            raise ValueError("agent_runner required for first call")
        _default_scheduler = TaskScheduler(agent_runner)
    return _default_scheduler
