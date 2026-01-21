"""
Shared data models for the Observer Bundle.

This module contains the core data structures used across all observer modules.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Observation severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Status(str, Enum):
    """Observation status values."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class SourceType(str, Enum):
    """Source types for observations."""

    FILE = "file"
    CONVERSATION = "conversation"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class WatchType(str, Enum):
    """Types of sources to watch."""

    FILES = "files"
    CONVERSATION = "conversation"


@dataclass
class Observation:
    """
    Represents a single observation from an observer.

    Observations are findings or issues identified by observers during review.
    They persist in the session transcript and can be acknowledged/resolved.
    """

    id: str
    observer: str
    content: str
    severity: Severity
    status: Status
    created_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source_type: SourceType = SourceType.UNKNOWN
    source_ref: str | None = None

    @classmethod
    def create(
        cls,
        observer: str,
        content: str,
        severity: str | Severity,
        source_type: str | SourceType = SourceType.UNKNOWN,
        source_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Observation":
        """Create a new observation with generated ID and timestamp."""
        if isinstance(severity, str):
            severity = Severity(severity)
        if isinstance(source_type, str):
            source_type = SourceType(source_type)

        return cls(
            id=str(uuid.uuid4()),
            observer=observer,
            content=content,
            severity=severity,
            status=Status.OPEN,
            created_at=datetime.now(),
            source_type=source_type,
            source_ref=source_ref,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert observation to dictionary for serialization."""
        return {
            "id": self.id,
            "observer": self.observer,
            "content": self.content,
            "severity": self.severity.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
            "metadata": self.metadata,
            "source_type": self.source_type.value,
            "source_ref": self.source_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        """Create observation from dictionary."""
        return cls(
            id=data["id"],
            observer=data["observer"],
            content=data["content"],
            severity=Severity(data["severity"]),
            status=Status(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            acknowledged_at=(
                datetime.fromisoformat(data["acknowledged_at"])
                if data.get("acknowledged_at")
                else None
            ),
            resolved_at=(
                datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None
            ),
            resolution_note=data.get("resolution_note"),
            metadata=data.get("metadata", {}),
            source_type=SourceType(data.get("source_type", "unknown")),
            source_ref=data.get("source_ref"),
        )

    def acknowledge(self) -> None:
        """Mark observation as acknowledged."""
        self.status = Status.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()

    def resolve(self, note: str | None = None) -> None:
        """Mark observation as resolved."""
        self.status = Status.RESOLVED
        self.resolved_at = datetime.now()
        if note:
            self.resolution_note = note


@dataclass
class WatchConfig:
    """
    Configuration for what an observer should watch.

    Supports watching files (via glob patterns) or conversation transcripts.
    """

    type: WatchType
    paths: list[str] | None = None  # For file watching (glob patterns)
    include_tool_calls: bool = True  # For conversation watching
    include_reasoning: bool = True  # For conversation watching

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WatchConfig":
        """Create WatchConfig from dictionary."""
        watch_type = data.get("type", "files")
        if isinstance(watch_type, str):
            watch_type = WatchType(watch_type)

        return cls(
            type=watch_type,
            paths=data.get("paths"),
            include_tool_calls=data.get("include_tool_calls", True),
            include_reasoning=data.get("include_reasoning", True),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "paths": self.paths,
            "include_tool_calls": self.include_tool_calls,
            "include_reasoning": self.include_reasoning,
        }


@dataclass
class ObserverConfig:
    """
    Configuration for a single observer.

    Observers are specialized agents that review content and report observations.
    """

    name: str
    role: str
    focus: str
    model: str
    watch: list[WatchConfig]
    timeout: int = 30
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObserverConfig":
        """Create ObserverConfig from dictionary."""
        watch_configs = [
            WatchConfig.from_dict(w) if isinstance(w, dict) else w for w in data.get("watch", [])
        ]

        return cls(
            name=data["name"],
            role=data["role"],
            focus=data["focus"],
            model=data["model"],
            watch=watch_configs,
            timeout=data.get("timeout", 30),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "role": self.role,
            "focus": self.focus,
            "model": self.model,
            "watch": [w.to_dict() for w in self.watch],
            "timeout": self.timeout,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionConfig:
    """Configuration for observer execution behavior."""

    mode: str = "parallel_sync"  # Currently only parallel_sync supported
    max_concurrent: int = 10
    timeout_per_observer: int = 30
    on_timeout: str = "skip"  # "skip" or "fail"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionConfig":
        """Create ExecutionConfig from dictionary."""
        return cls(
            mode=data.get("mode", "parallel_sync"),
            max_concurrent=data.get("max_concurrent", 10),
            timeout_per_observer=data.get("timeout_per_observer", 30),
            on_timeout=data.get("on_timeout", "skip"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mode": self.mode,
            "max_concurrent": self.max_concurrent,
            "timeout_per_observer": self.timeout_per_observer,
            "on_timeout": self.on_timeout,
        }


@dataclass
class HookConfig:
    """Configuration for when hooks trigger."""

    trigger: str  # e.g., "response:complete", "message:received"
    priority: int = 5

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HookConfig":
        """Create HookConfig from dictionary."""
        return cls(
            trigger=data["trigger"],
            priority=data.get("priority", 5),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trigger": self.trigger,
            "priority": self.priority,
        }


@dataclass
class ObservationsModuleConfig:
    """Complete configuration for the hooks-observations module."""

    hooks: list[HookConfig] = field(default_factory=list)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    observers: list[ObserverConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObservationsModuleConfig":
        """Create module config from dictionary."""
        hooks = [HookConfig.from_dict(h) for h in data.get("hooks", [])]

        # Default hook if none specified
        # Note: orchestrator:complete fires at end of each turn
        if not hooks:
            hooks = [HookConfig(trigger="orchestrator:complete", priority=5)]

        execution = ExecutionConfig.from_dict(data.get("execution", {}))

        observers = [ObserverConfig.from_dict(o) for o in data.get("observers", [])]

        return cls(
            hooks=hooks,
            execution=execution,
            observers=observers,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hooks": [h.to_dict() for h in self.hooks],
            "execution": self.execution.to_dict(),
            "observers": [o.to_dict() for o in self.observers],
        }
