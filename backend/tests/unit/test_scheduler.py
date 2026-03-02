"""
Tests for task scheduler.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import json

from scheduler.task_scheduler import (
    ScheduledTask,
    TaskRunLog,
    TaskScheduler,
    get_scheduler,
)


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_agent_runner():
    """Create a mock agent runner"""
    async def runner(**kwargs):
        return f"Mock response for {kwargs.get('prompt', 'unknown')}"
    return runner


@pytest.fixture
def scheduler(temp_storage, mock_agent_runner):
    """Create a task scheduler with temp storage"""
    return TaskScheduler(
        agent_runner=mock_agent_runner,
        storage_dir=temp_storage
    )


class TestScheduledTask:
    """Tests for ScheduledTask dataclass"""

    def test_create_task(self):
        """Test creating a scheduled task"""
        task = ScheduledTask(
            id="task1",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Test prompt",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        assert task.id == "task1"
        assert task.status == "active"
        assert task.max_retries == 3

    def test_task_serialization(self):
        """Test task to_dict and from_dict"""
        task = ScheduledTask(
            id="task2",
            group_folder="test",
            chat_jid="dc:456",
            prompt="Test",
            schedule_type="cron",
            schedule_value="0 * * * *",
            context_mode="isolated"
        )

        data = task.to_dict()
        restored = ScheduledTask.from_dict(data)

        assert restored.id == task.id
        assert restored.group_folder == task.group_folder
        assert restored.schedule_type == task.schedule_type

    def test_task_with_context_layers(self):
        """Test task with multi-layer context"""
        task = ScheduledTask(
            id="task3",
            group_folder="main",
            chat_jid="dc:789",
            prompt="Test",
            schedule_type="interval",
            schedule_value="300",
            context_mode="group",
            agent_id="assistant-1",
            server_folder="servers/discord",
            category_folder="category/support"
        )

        assert task.agent_id == "assistant-1"
        assert task.server_folder == "servers/discord"
        assert task.category_folder == "category/support"


class TestTaskRunLog:
    """Tests for TaskRunLog dataclass"""

    def test_create_log(self):
        """Test creating a run log"""
        log = TaskRunLog(
            task_id="task1",
            run_at=datetime.now(),
            duration_ms=1500,
            success=True,
            result="Success result"
        )

        assert log.task_id == "task1"
        assert log.success is True
        assert log.result == "Success result"

    def test_log_serialization(self):
        """Test log to_dict"""
        log = TaskRunLog(
            task_id="task2",
            run_at=datetime(2024, 1, 1, 12, 0, 0),
            duration_ms=2000,
            success=False,
            error="Test error"
        )

        data = log.to_dict()
        assert data["task_id"] == "task2"
        assert data["success"] is False
        assert data["error"] == "Test error"


class TestTaskScheduler:
    """Tests for TaskScheduler"""

    @pytest.mark.asyncio
    async def test_initialize_scheduler(self, scheduler):
        """Test scheduler initialization"""
        await scheduler.initialize()
        assert scheduler._initialized is True
        assert scheduler.scheduler.running is True

    @pytest.mark.asyncio
    async def test_shutdown_scheduler(self, scheduler):
        """Test scheduler shutdown"""
        await scheduler.initialize()
        await scheduler.shutdown(wait=True)
        # Give it a moment to fully shutdown
        await asyncio.sleep(0.05)
        # Scheduler should be stopped
        assert not scheduler.scheduler.running

    @pytest.mark.asyncio
    async def test_add_task(self, scheduler):
        """Test adding a task"""
        await scheduler.initialize()

        task = ScheduledTask(
            id="test_task",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Test prompt",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        scheduler.add_task(task)

        assert "test_task" in scheduler._tasks
        assert scheduler.get_task("test_task") == task

    @pytest.mark.asyncio
    async def test_remove_task(self, scheduler):
        """Test removing a task"""
        await scheduler.initialize()

        task = ScheduledTask(
            id="to_remove",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Test",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        scheduler.add_task(task)
        result = scheduler.remove_task("to_remove")

        assert result is True
        assert "to_remove" not in scheduler._tasks

    @pytest.mark.asyncio
    async def test_pause_task(self, scheduler):
        """Test pausing a task"""
        await scheduler.initialize()

        task = ScheduledTask(
            id="pause_test",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Test",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        scheduler.add_task(task)
        result = scheduler.pause_task("pause_test")

        assert result is True
        assert scheduler.get_task("pause_test").status == "paused"

    @pytest.mark.asyncio
    async def test_resume_task(self, scheduler):
        """Test resuming a paused task"""
        await scheduler.initialize()

        task = ScheduledTask(
            id="resume_test",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Test",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        scheduler.add_task(task)
        scheduler.pause_task("resume_test")
        result = scheduler.resume_task("resume_test")

        assert result is True
        assert scheduler.get_task("resume_test").status == "active"

    @pytest.mark.asyncio
    async def test_get_all_tasks(self, scheduler):
        """Test getting all tasks"""
        await scheduler.initialize()

        task1 = ScheduledTask(
            id="all_1",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Test 1",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        task2 = ScheduledTask(
            id="all_2",
            group_folder="main",
            chat_jid="dc:456",
            prompt="Test 2",
            schedule_type="interval",
            schedule_value="120",
            context_mode="group"
        )

        scheduler.add_task(task1)
        scheduler.add_task(task2)

        all_tasks = scheduler.get_all_tasks()
        assert len(all_tasks) == 2
        assert "all_1" in all_tasks
        assert "all_2" in all_tasks

    @pytest.mark.asyncio
    async def test_get_active_tasks(self, scheduler):
        """Test getting only active tasks"""
        await scheduler.initialize()

        active_task = ScheduledTask(
            id="active_1",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Active",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        paused_task = ScheduledTask(
            id="paused_1",
            group_folder="main",
            chat_jid="dc:456",
            prompt="Paused",
            schedule_type="interval",
            schedule_value="120",
            context_mode="group"
        )
        paused_task.status = "paused"

        scheduler.add_task(active_task)
        scheduler.add_task(paused_task)

        active_tasks = scheduler.get_active_tasks()
        assert len(active_tasks) == 1
        assert "active_1" in active_tasks
        assert "paused_1" not in active_tasks

    @pytest.mark.asyncio
    async def test_task_persistence(self, scheduler, temp_storage):
        """Test that tasks are persisted to disk"""
        await scheduler.initialize()

        task = ScheduledTask(
            id="persist_test",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Persist",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        scheduler.add_task(task)

        # Wait for async persistence
        await asyncio.sleep(0.1)

        # Check file exists
        task_file = temp_storage / "tasks" / "persist_test.json"
        assert task_file.exists()

        # Verify content
        data = json.loads(task_file.read_text())
        assert data["id"] == "persist_test"

    @pytest.mark.asyncio
    async def test_task_logs_written(self, scheduler, temp_storage):
        """Test that task logs are written to disk"""
        await scheduler.initialize()

        # Manually write a log to test the mechanism
        log = TaskRunLog(
            task_id="log_test",
            run_at=datetime.now(),
            duration_ms=100,
            success=True,
            result="Test result"
        )

        await scheduler._write_log("log_test", log)

        log_file = temp_storage / "logs" / "log_test.jsonl"
        assert log_file.exists()

    @pytest.mark.asyncio
    async def test_get_task_logs(self, scheduler, temp_storage):
        """Test retrieving task logs"""
        await scheduler.initialize()

        # Write multiple logs
        for i in range(5):
            log = TaskRunLog(
                task_id="logs_test",
                run_at=datetime.now(),
                duration_ms=100 * i,
                success=True,
                result=f"Result {i}"
            )
            await scheduler._write_log("logs_test", log)

        logs = scheduler.get_task_logs("logs_test", limit=3)
        assert len(logs) == 3

    @pytest.mark.asyncio
    async def test_duplicate_task_raises(self, scheduler):
        """Test that adding duplicate task raises"""
        await scheduler.initialize()

        task = ScheduledTask(
            id="dup_test",
            group_folder="main",
            chat_jid="dc:123",
            prompt="Test",
            schedule_type="interval",
            schedule_value="60",
            context_mode="group"
        )

        scheduler.add_task(task)

        with pytest.raises(ValueError):
            scheduler.add_task(task)


class TestGetScheduler:
    """Tests for get_scheduler helper"""

    def test_get_scheduler_requires_runner_first_time(self):
        """Test that first call requires agent_runner"""
        from scheduler import task_scheduler
        original = task_scheduler._default_scheduler
        task_scheduler._default_scheduler = None

        try:
            with pytest.raises(ValueError):
                get_scheduler()
        finally:
            task_scheduler._default_scheduler = original

    def test_get_scheduler_singleton(self, mock_agent_runner):
        """Test that get_scheduler returns same instance"""
        from scheduler import task_scheduler
        original = task_scheduler._default_scheduler
        task_scheduler._default_scheduler = None

        try:
            s1 = get_scheduler(mock_agent_runner)
            s2 = get_scheduler()
            assert s1 is s2
        finally:
            task_scheduler._default_scheduler = original
