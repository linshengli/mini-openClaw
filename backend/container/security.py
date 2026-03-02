"""
Mount security validation.
Migrated from OmniClaw's src/mount-security.ts and src/path-security.ts

Provides security validation for volume mounts.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class MountSecurity:
    """
    Security validator for volume mounts.

    Prevents:
    - Path traversal attacks
    - Mounting sensitive directories
    - Unauthorized access to system files
    """

    # Default blocked patterns (regex)
    DEFAULT_BLOCKED_PATTERNS = [
        r".*\.ssh.*",
        r".*\.gnupg.*",
        r".*\.aws.*",
        r".*\.git.*",
        r"/etc/passwd.*",
        r"/etc/shadow.*",
        r"/etc/sudoers.*",
        r"/root/.*",
        r"/var/root/.*",
    ]

    def __init__(
        self,
        allowed_roots: Optional[List[str]] = None,
        blocked_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize mount security validator.

        Args:
            allowed_roots: List of allowed root directories
            blocked_patterns: List of regex patterns for blocked paths
        """
        self.allowed_roots: Set[Path] = set()
        self.blocked_patterns: List[re.Pattern] = []

        # Set allowed roots
        if allowed_roots:
            for root in allowed_roots:
                self.add_allowed_root(root)

        # Set blocked patterns
        patterns = blocked_patterns or self.DEFAULT_BLOCKED_PATTERNS
        for pattern in patterns:
            self.blocked_patterns.append(re.compile(pattern))

    def add_allowed_root(self, path: str) -> None:
        """Add an allowed root directory"""
        resolved = Path(path).expanduser().resolve()
        self.allowed_roots.add(resolved)

    def remove_allowed_root(self, path: str) -> bool:
        """Remove an allowed root directory"""
        resolved = Path(path).expanduser().resolve()
        if resolved in self.allowed_roots:
            self.allowed_roots.remove(resolved)
            return True
        return False

    def add_blocked_pattern(self, pattern: str) -> None:
        """Add a blocked path pattern"""
        self.blocked_patterns.append(re.compile(pattern))

    def validate_mount(self, host_path: str) -> bool:
        """
        Validate if a path can be mounted.

        Args:
            host_path: Path to validate

        Returns:
            True if path is allowed, False otherwise
        """
        # Check for path traversal
        if self._has_path_traversal(host_path):
            return False

        # Resolve the path
        try:
            resolved = Path(host_path).expanduser().resolve()
        except (OSError, ValueError):
            return False

        # Check against blocked patterns
        if self._is_blocked_pattern(str(resolved)):
            return False

        # Check against allowed roots (if any specified)
        if self.allowed_roots:
            if not self._is_under_allowed_roots(resolved):
                return False

        return True

    def _has_path_traversal(self, path: str) -> bool:
        """Check for path traversal attempts"""
        # Check for .. components
        parts = Path(path).parts
        if ".." in parts:
            return True

        # Check for encoded traversal
        if "%2e%2e" in path.lower():
            return True

        # Check for symlink traversal
        try:
            resolved = Path(path).resolve()
            # Check if resolved path escapes allowed roots
            if self.allowed_roots:
                for root in self.allowed_roots:
                    try:
                        resolved.relative_to(root)
                        break
                    except ValueError:
                        continue
                else:
                    return True
        except (OSError, ValueError):
            return True

        return False

    def _is_blocked_pattern(self, path: str) -> bool:
        """Check if path matches any blocked pattern"""
        for pattern in self.blocked_patterns:
            if pattern.match(path):
                return True
        return False

    def _is_under_allowed_roots(self, path: Path) -> bool:
        """Check if path is under any allowed root"""
        for root in self.allowed_roots:
            try:
                path.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def get_allowed_roots(self) -> List[str]:
        """Get list of allowed root paths"""
        return [str(root) for root in self.allowed_roots]

    def get_blocked_patterns(self) -> List[str]:
        """Get list of blocked patterns"""
        return [p.pattern for p in self.blocked_patterns]


class PathSecurity:
    """
    Path security utilities.

    Provides additional security checks for file paths.
    """

    @staticmethod
    def is_safe_path(path: str, base_dir: Path) -> bool:
        """
        Check if a path is safely within a base directory.

        Args:
            path: Path to check
            base_dir: Base directory that should contain the path

        Returns:
            True if path is safe, False otherwise
        """
        try:
            resolved_path = Path(path).resolve()
            resolved_base = base_dir.resolve()
            resolved_path.relative_to(resolved_base)
            return True
        except (ValueError, OSError):
            return False

    @staticmethod
    def sanitize_path(path: str) -> str:
        """
        Sanitize a path by removing dangerous components.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path string
        """
        # Remove null bytes
        path = path.replace("\x00", "")

        # Remove URL encoding
        path = path.replace("%2e", ".").replace("%2F", "/")

        # Normalize path separators
        path = path.replace("\\", "/")

        return path

    @staticmethod
    def get_safe_relative_path(path: str, base_dir: Path) -> Optional[Path]:
        """
        Get a safe relative path within a base directory.

        Args:
            path: Path to resolve
            base_dir: Base directory

        Returns:
            Safe relative path or None if unsafe
        """
        try:
            resolved = Path(path).resolve()
            resolved_base = base_dir.resolve()
            relative = resolved.relative_to(resolved_base)
            return relative
        except (ValueError, OSError):
            return None
