"""
Tests for container isolation system.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from container.base import (
    ContainerBackend,
    ContainerConfig,
    ContainerResult,
    VolumeMount,
    BackendType,
    AgentRuntime,
)
from container.local import LocalContainerBackend
from container.security import MountSecurity, PathSecurity


class TestVolumeMount:
    """Tests for VolumeMount dataclass"""

    def test_create_mount(self):
        """Test creating a volume mount"""
        mount = VolumeMount(
            host_path="/home/user/data",
            container_path="/data",
            read_only=True,
        )
        assert mount.host_path == "/home/user/data"
        assert mount.container_path == "/data"
        assert mount.read_only is True

    def test_mount_defaults_to_basename(self):
        """Test that container_path defaults to basename"""
        mount = VolumeMount(host_path="/home/user/mydata")
        assert mount.container_path == "mydata"


class TestContainerConfig:
    """Tests for ContainerConfig dataclass"""

    def test_create_config(self):
        """Test creating a container config"""
        config = ContainerConfig(
            timeout_ms=60000,
            memory_mb=2048,
            network_mode="full",
        )
        assert config.timeout_ms == 60000
        assert config.memory_mb == 2048
        assert config.network_mode == "full"

    def test_config_defaults(self):
        """Test config default values"""
        config = ContainerConfig()
        assert config.timeout_ms == 300000
        assert config.memory_mb == 4096
        assert config.network_mode == "none"


class TestContainerResult:
    """Tests for ContainerResult dataclass"""

    def test_create_result(self):
        """Test creating a container result"""
        result = ContainerResult(
            success=True,
            output="Hello, World!",
            duration_ms=1500,
        )
        assert result.success is True
        assert result.output == "Hello, World!"
        assert result.duration_ms == 1500


class TestMountSecurity:
    """Tests for MountSecurity"""

    def test_allowed_root(self):
        """Test adding allowed root"""
        security = MountSecurity(allowed_roots=["/home/user"])
        assert security.validate_mount("/home/user/data") is True
        assert security.validate_mount("/home/user/projects/code") is True

    def test_path_traversal_blocked(self):
        """Test that path traversal is blocked"""
        security = MountSecurity(allowed_roots=["/home/user"])
        assert security.validate_mount("/home/user/../etc/passwd") is False
        assert security.validate_mount("/home/user/../../root") is False

    def test_blocked_patterns(self):
        """Test blocked patterns"""
        security = MountSecurity()
        assert security.validate_mount("/home/user/.ssh/id_rsa") is False
        assert security.validate_mount("/home/user/.gnupg/secring.gpg") is False

    def test_custom_blocked_pattern(self):
        """Test adding custom blocked pattern"""
        security = MountSecurity(allowed_roots=["/home/user"])
        security.add_blocked_pattern(r".*\.env.*")
        assert security.validate_mount("/home/user/project/.env") is False

    def test_empty_allowed_roots_allows_all(self):
        """Test that empty allowed roots allows all non-blocked paths"""
        security = MountSecurity(allowed_roots=[])
        # Should allow anything that's not blocked
        assert security.validate_mount("/any/path") is True
        # But still block sensitive paths
        assert security.validate_mount("/root/.ssh") is False


class TestPathSecurity:
    """Tests for PathSecurity"""

    def test_is_safe_path(self):
        """Test safe path detection"""
        base = Path("/safe/base")
        assert PathSecurity.is_safe_path("/safe/base/file.txt", base) is True
        assert PathSecurity.is_safe_path("/safe/base/subdir/file.txt", base) is True
        assert PathSecurity.is_safe_path("/unsafe/path", base) is False

    def test_sanitize_path(self):
        """Test path sanitization"""
        assert PathSecurity.sanitize_path("file\x00.txt") == "file.txt"
        assert PathSecurity.sanitize_path("%2e%2e/parent") == "../parent"
        assert PathSecurity.sanitize_path("path\\to\\file") == "path/to/file"


class TestLocalContainerBackend:
    """Tests for LocalContainerBackend"""

    @pytest.fixture
    def backend(self):
        """Create a backend for testing"""
        return LocalContainerBackend(project_root=Path.cwd())

    @pytest.mark.asyncio
    async def test_initialize(self, backend):
        """Test backend initialization"""
        await backend.initialize()
        assert backend._initialized is True

    @pytest.mark.asyncio
    async def test_build_environment(self, backend):
        """Test environment building"""
        env = backend._build_environment("test_group")
        assert "GROUP_FOLDER" in env
        assert "PYTHONPATH" in env
        assert "AGENT_ISOLATED" in env

    @pytest.mark.asyncio
    async def test_build_mounts(self, backend):
        """Test mount building"""
        mounts = backend._build_mounts("test_group")
        assert len(mounts) >= 2  # At least group and workspace mounts

    @pytest.mark.asyncio
    async def test_shutdown(self, backend):
        """Test backend shutdown"""
        await backend.initialize()
        await backend.shutdown()
        assert backend._initialized is False
