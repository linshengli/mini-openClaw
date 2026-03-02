"""
Local process isolation backend.
Migrated from OmniClaw's src/backends/local-backend.ts

Provides process-level isolation using subprocess execution.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .base import (
    ContainerBackend,
    ContainerConfig,
    ContainerResult,
    VolumeMount,
)
from .security import MountSecurity


class LocalContainerBackend(ContainerBackend):
    """
    Local process isolation backend.

    Runs agents in isolated subprocesses with restricted filesystem access.
    This is a simpler alternative to full container isolation.
    """

    def __init__(
        self,
        config: Optional[ContainerConfig] = None,
        project_root: Optional[Path] = None,
    ):
        super().__init__(config)
        self.project_root = project_root or Path.cwd()
        self.security = MountSecurity(
            allowed_roots=[str(self.project_root)],
            blocked_patterns=[
                r".*\.ssh.*",
                r".*\.gnupg.*",
                r".*\.aws.*",
                r"/etc/passwd",
                r"/etc/shadow",
            ]
        )
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def initialize(self) -> None:
        """Initialize the local backend"""
        self._initialized = True

    def _build_environment(
        self,
        group_folder: str,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Build isolated environment for subprocess"""
        # Start with minimal environment
        isolated_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": str(self.project_root),
            "GROUP_FOLDER": str(self.project_root / "groups" / group_folder),
            "AGENT_ISOLATED": "1",
        }

        # Add custom environment variables
        if env:
            # Filter out dangerous variables
            dangerous = ["SUDO_", "SSH_", "AWS_", "GOOGLE_"]
            for key, value in env.items():
                if not any(key.startswith(d) for d in dangerous):
                    isolated_env[key] = value

        return isolated_env

    def _build_mounts(
        self,
        group_folder: str,
    ) -> List[VolumeMount]:
        """Build mount list for isolation"""
        mounts = [
            VolumeMount(
                host_path=str(self.project_root / "groups" / group_folder),
                container_path="/workspace/group",
                read_only=False,
            ),
            VolumeMount(
                host_path=str(self.project_root / "workspace"),
                container_path="/workspace",
                read_only=True,
            ),
        ]

        # Add additional mounts from config
        for mount in self.config.additional_mounts:
            # Validate mount security
            if not self.security.validate_mount(mount.host_path):
                raise ValueError(f"Mount not allowed: {mount.host_path}")
            mounts.append(mount)

        return mounts

    async def run_agent(
        self,
        group_folder: str,
        prompt: str,
        env: Optional[Dict[str, str]] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> ContainerResult:
        """
        Run an agent in an isolated subprocess.

        Args:
            group_folder: Group workspace folder
            prompt: User prompt to process
            env: Environment variables
            on_output: Optional callback for streaming output

        Returns:
            ContainerResult with execution output
        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()

        # Build isolated environment
        isolated_env = self._build_environment(group_folder, env)

        # Build command to run agent
        # This runs the current Python interpreter with agent_runtime module
        cmd = [
            sys.executable,
            "-c",
            f"""
import sys
sys.path.insert(0, '{self.project_root}')
from core.agent_runtime import MiniOpenClawRuntime
import os

group_folder = os.environ.get('GROUP_FOLDER', 'main')
runtime = MiniOpenClawRuntime(
    model='claude-sonnet-4-6',
    project_root='{self.project_root}',
    group_folder='{group_folder}'
)
result = runtime.chat_once('local-session', '''{prompt}''')
print(result)
""",
        ]

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=isolated_env,
                cwd=str(self.project_root),
            )

            self._processes[group_folder] = process

            # Wait for output with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_ms / 1000,
                )
            except asyncio.TimeoutError:
                process.kill()
                stdout, stderr = b"", b"Process timed out"

            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""

            # Call output callback if provided
            if on_output and output:
                on_output(output)

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return ContainerResult(
                success=process.returncode == 0,
                output=output,
                error=error,
                return_code=process.returncode or 0,
                duration_ms=duration_ms,
            )

        except Exception as e:
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return ContainerResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

        finally:
            if group_folder in self._processes:
                del self._processes[group_folder]

    async def shutdown(self) -> None:
        """Shutdown the local backend"""
        # Kill any running processes
        for folder, process in self._processes.items():
            try:
                process.kill()
            except Exception:
                pass
        self._processes.clear()
        self._initialized = False
