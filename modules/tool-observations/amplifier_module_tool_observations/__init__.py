"""
Observations Tool Module

Provides CRUD operations for managing observations in the session state.
Observations are stored in the session transcript using JSONL format.
"""

import json
import logging
from typing import Any

from amplifier_core import ToolResult

from .models import Observation, Severity, Status

logger = logging.getLogger(__name__)


class ObservationsTool:
    """
    Tool for managing observations state.

    Provides create, list, acknowledge, resolve, and clear operations.
    State is persisted via the session's state management capabilities.
    """

    # Tool protocol required attributes
    name: str = "observations"
    description: str = """Manage code and conversation observations from automated reviewers.

Operations:
- list: List observations with optional filters (status, severity, observer)
- get: Get a specific observation by ID
- acknowledge: Mark an observation as acknowledged
- resolve: Mark an observation as resolved with optional note
- clear_resolved: Remove all resolved observations

Examples:
- List open observations: {"operation": "list", "filters": {"status": "open"}}
- List critical/high issues: {"operation": "list", "filters": {"severity": ["critical", "high"]}}
- Acknowledge: {"operation": "acknowledge", "observation_id": "uuid"}
- Resolve: {"operation": "resolve", "observation_id": "uuid", "resolution_note": "Fixed"}
"""

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["list", "get", "acknowledge", "resolve", "clear_resolved"],
                    "description": "Operation to perform",
                },
                "observation_id": {
                    "type": "string",
                    "description": "ID of observation (for get/acknowledge/resolve)",
                },
                "filters": {
                    "type": "object",
                    "description": "Filters for list operation",
                    "properties": {
                        "status": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}},
                            ],
                            "description": "Filter by status(es)",
                        },
                        "severity": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}},
                            ],
                            "description": "Filter by severity(ies)",
                        },
                        "observer": {
                            "type": "string",
                            "description": "Filter by observer name",
                        },
                    },
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["severity", "created_at"],
                    "description": "Sort order for list",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results for list",
                },
                "resolution_note": {
                    "type": "string",
                    "description": "Note when resolving observation",
                },
            },
            "required": ["operation"],
        }

    def __init__(self, state_manager: Any | None = None) -> None:
        """
        Initialize the observations tool.

        Args:
            state_manager: Optional state manager for persistence.
                          If None, uses in-memory storage.
        """
        self._state_manager = state_manager
        self._observations: dict[str, Observation] = {}

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Execute an observations operation.

        Args:
            arguments: Operation arguments including:
                - operation: The operation to perform
                - Additional operation-specific arguments

        Returns:
            ToolResult with operation output
        """
        operation = arguments.get("operation", "list")

        handlers = {
            "create": self._handle_create,
            "create_batch": self._handle_create_batch,
            "list": self._handle_list,
            "get": self._handle_get,
            "acknowledge": self._handle_acknowledge,
            "resolve": self._handle_resolve,
            "clear_resolved": self._handle_clear_resolved,
        }

        handler = handlers.get(operation)
        if not handler:
            return ToolResult(
                success=False,
                error={
                    "message": f"Unknown operation: {operation}",
                    "valid_operations": list(handlers.keys()),
                },
            )

        try:
            result = await handler(arguments)
            return ToolResult(success=True, output=result)
        except Exception as e:
            logger.exception(f"Error in observations operation '{operation}'")
            return ToolResult(
                success=False,
                error={"message": str(e), "operation": operation},
            )

    async def _handle_create(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a single observation."""
        obs_data = arguments.get("observation", arguments)

        observation = Observation.create(
            observer=obs_data.get("observer", "unknown"),
            content=obs_data["content"],
            severity=obs_data.get("severity", "info"),
            source_type=obs_data.get("source_type", "unknown"),
            source_ref=obs_data.get("source_ref"),
            metadata=obs_data.get("metadata"),
        )

        self._observations[observation.id] = observation
        await self._persist_state()

        return {
            "status": "created",
            "observation": observation.to_dict(),
        }

    async def _handle_create_batch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create multiple observations at once."""
        observations_data = arguments.get("observations", [])
        created = []

        for obs_data in observations_data:
            observation = Observation.create(
                observer=obs_data.get("observer", "unknown"),
                content=obs_data["content"],
                severity=obs_data.get("severity", "info"),
                source_type=obs_data.get("source_type", "unknown"),
                source_ref=obs_data.get("source_ref"),
                metadata=obs_data.get("metadata"),
            )
            self._observations[observation.id] = observation
            created.append(observation)

        await self._persist_state()

        return {
            "status": "created",
            "count": len(created),
            "observations": [o.to_dict() for o in created],
            "by_severity": self._count_by_severity(created),
            "by_status": self._count_by_status(created),
        }

    async def _handle_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List observations with optional filtering."""
        filters = arguments.get("filters", {})
        sort_by = arguments.get("sort_by", "severity")
        limit = arguments.get("limit", 50)

        observations = list(self._observations.values())

        # Apply filters
        if "status" in filters:
            status_filter = filters["status"]
            if isinstance(status_filter, str):
                status_filter = [status_filter]
            observations = [o for o in observations if o.status.value in status_filter]

        if "severity" in filters:
            severity_filter = filters["severity"]
            if isinstance(severity_filter, str):
                severity_filter = [severity_filter]
            observations = [o for o in observations if o.severity.value in severity_filter]

        if "observer" in filters:
            observer_filter = filters["observer"]
            observations = [o for o in observations if o.observer == observer_filter]

        # Sort
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }

        if sort_by == "severity":
            observations.sort(key=lambda o: severity_order.get(o.severity, 5))
        elif sort_by == "created_at":
            observations.sort(key=lambda o: o.created_at, reverse=True)

        # Limit
        observations = observations[:limit]

        return {
            "status": "ok",
            "observations": [o.to_dict() for o in observations],
            "count": len(observations),
            "total": len(self._observations),
            "by_severity": self._count_by_severity(observations),
            "by_observer": self._count_by_observer(observations),
        }

    async def _handle_get(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get a single observation by ID."""
        obs_id = arguments.get("observation_id")
        if not obs_id:
            return {"status": "error", "error": "observation_id required"}

        observation = self._observations.get(obs_id)
        if not observation:
            return {"status": "error", "error": f"Observation not found: {obs_id}"}

        return {
            "status": "ok",
            "observation": observation.to_dict(),
        }

    async def _handle_acknowledge(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Acknowledge an observation."""
        obs_id = arguments.get("observation_id")
        if not obs_id:
            return {"status": "error", "error": "observation_id required"}

        observation = self._observations.get(obs_id)
        if not observation:
            return {"status": "error", "error": f"Observation not found: {obs_id}"}

        observation.acknowledge()
        await self._persist_state()

        return {
            "status": "acknowledged",
            "observation": observation.to_dict(),
        }

    async def _handle_resolve(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Resolve an observation."""
        obs_id = arguments.get("observation_id")
        if not obs_id:
            return {"status": "error", "error": "observation_id required"}

        observation = self._observations.get(obs_id)
        if not observation:
            return {"status": "error", "error": f"Observation not found: {obs_id}"}

        resolution_note = arguments.get("resolution_note")
        observation.resolve(resolution_note)
        await self._persist_state()

        return {
            "status": "resolved",
            "observation": observation.to_dict(),
        }

    async def _handle_clear_resolved(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Clear all resolved observations."""
        resolved_ids = [
            obs_id for obs_id, obs in self._observations.items() if obs.status == Status.RESOLVED
        ]

        for obs_id in resolved_ids:
            del self._observations[obs_id]

        await self._persist_state()

        return {
            "status": "cleared",
            "count": len(resolved_ids),
        }

    async def _persist_state(self) -> None:
        """Persist observations state."""
        if self._state_manager:
            state_data = {
                "observations": {
                    obs_id: obs.to_dict() for obs_id, obs in self._observations.items()
                }
            }
            await self._state_manager.set("observations", json.dumps(state_data))

    async def load_state(self) -> None:
        """Load observations state from persistence."""
        if self._state_manager:
            state_json = await self._state_manager.get("observations")
            if state_json:
                state_data = json.loads(state_json)
                self._observations = {
                    obs_id: Observation.from_dict(obs_data)
                    for obs_id, obs_data in state_data.get("observations", {}).items()
                }

    def _count_by_severity(self, observations: list[Observation]) -> dict[str, int]:
        """Count observations by severity."""
        counts: dict[str, int] = {}
        for obs in observations:
            severity = obs.severity.value
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def _count_by_status(self, observations: list[Observation]) -> dict[str, int]:
        """Count observations by status."""
        counts: dict[str, int] = {}
        for obs in observations:
            status = obs.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _count_by_observer(self, observations: list[Observation]) -> dict[str, int]:
        """Count observations by observer."""
        counts: dict[str, int] = {}
        for obs in observations:
            counts[obs.observer] = counts.get(obs.observer, 0) + 1
        return counts


def get_tool_definition() -> dict[str, Any]:
    """Return the tool definition for the observations tool."""
    return {
        "name": "observations",
        "description": """Manage code and conversation observations from automated reviewers.

Operations:
- list: List observations with optional filters (status, severity, observer)
- get: Get a specific observation by ID
- acknowledge: Mark an observation as acknowledged
- resolve: Mark an observation as resolved with optional note
- clear_resolved: Remove all resolved observations

Examples:
- List open observations: {"operation": "list", "filters": {"status": "open"}}
- List critical/high issues: {"operation": "list", "filters": {"severity": ["critical", "high"]}}
- Acknowledge: {"operation": "acknowledge", "observation_id": "uuid"}
- Resolve: {"operation": "resolve", "observation_id": "uuid", "resolution_note": "Fixed"}
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["list", "get", "acknowledge", "resolve", "clear_resolved"],
                    "description": "Operation to perform",
                },
                "observation_id": {
                    "type": "string",
                    "description": "ID of observation (for get/acknowledge/resolve)",
                },
                "filters": {
                    "type": "object",
                    "description": "Filters for list operation",
                    "properties": {
                        "status": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}},
                            ],
                            "description": "Filter by status(es)",
                        },
                        "severity": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}},
                            ],
                            "description": "Filter by severity(ies)",
                        },
                        "observer": {
                            "type": "string",
                            "description": "Filter by observer name",
                        },
                    },
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["severity", "created_at"],
                    "description": "Sort order for list",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results for list",
                },
                "resolution_note": {
                    "type": "string",
                    "description": "Note when resolving observation",
                },
            },
            "required": ["operation"],
        },
    }


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """
    Mount the observations tool.

    Args:
        coordinator: Orchestrator coordinator instance
        config: Optional module configuration
    """
    # Get state manager from coordinator if available
    state_manager = getattr(coordinator, "state_manager", None)

    # Create tool instance
    tool = ObservationsTool(state_manager=state_manager)

    # Load persisted state
    await tool.load_state()

    # Register tool in mount_points (standard Amplifier pattern)
    coordinator.mount_points["tools"][tool.name] = tool

    logger.info("Mounted tool-observations module")
