"""
Amplifier Observer Bundle

Provides automated code and conversation review through specialized AI observers.

Modules:
    - tool_observations: State management for observations (CRUD operations)
    - hooks_observations: Hook-driven observer orchestration
    - hooks_observations_display: Optional visualization of observations
"""

from amplifier_bundle_observers.hooks_observations import (
    ObservationHooks,
)
from amplifier_bundle_observers.hooks_observations import (
    mount as mount_hooks,
)
from amplifier_bundle_observers.hooks_observations_display import (
    ObservationDisplayHooks,
)
from amplifier_bundle_observers.hooks_observations_display import (
    mount as mount_display,
)
from amplifier_bundle_observers.models import (
    Observation,
    ObserverConfig,
    WatchConfig,
)
from amplifier_bundle_observers.tool_observations import (
    ObservationsTool,
)
from amplifier_bundle_observers.tool_observations import (
    mount as mount_tool,
)

__all__ = [
    # Models
    "Observation",
    "ObserverConfig",
    "WatchConfig",
    # Tool
    "ObservationsTool",
    "mount_tool",
    # Hooks
    "ObservationHooks",
    "mount_hooks",
    # Display
    "ObservationDisplayHooks",
    "mount_display",
]

__version__ = "0.1.0"
