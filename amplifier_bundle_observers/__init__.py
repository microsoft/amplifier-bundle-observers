"""
Amplifier Observer Bundle

Provides automated code and conversation review through specialized AI observers.

Modules (installed separately via git URLs):
    - hooks-observations: Hook-driven observer orchestration
    - hooks-observations-display: Optional visualization of observations
    - tool-observations: State management for observations (CRUD operations)

This package exports shared models used across modules.
"""

from amplifier_bundle_observers.models import (
    ExecutionConfig,
    HookConfig,
    Observation,
    ObservationsModuleConfig,
    ObserverConfig,
    Severity,
    SourceType,
    Status,
    WatchConfig,
    WatchType,
)

__all__ = [
    # Enums
    "Severity",
    "Status",
    "SourceType",
    "WatchType",
    # Models
    "Observation",
    "WatchConfig",
    "ObserverConfig",
    "ExecutionConfig",
    "HookConfig",
    "ObservationsModuleConfig",
]

__version__ = "0.1.1"
