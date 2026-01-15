"""
Observations Display Hooks Module

Optional visualization module for rendering observation status
with progress bar, table, and compact display styles.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DisplayConfig:
    """Configuration for observation display."""

    def __init__(
        self,
        style: str = "compact",
        show_on_create: bool = True,
        show_on_resolve: bool = True,
        show_on_change: bool = True,
    ) -> None:
        """
        Initialize display configuration.

        Args:
            style: Display style ("compact", "table", "progress_bar")
            show_on_create: Show display when observations created
            show_on_resolve: Show display when observations resolved
            show_on_change: Show display when observations change
        """
        self.style = style
        self.show_on_create = show_on_create
        self.show_on_resolve = show_on_resolve
        self.show_on_change = show_on_change

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DisplayConfig":
        """Create config from dictionary."""
        return cls(
            style=data.get("style", "compact"),
            show_on_create=data.get("show_on_create", True),
            show_on_resolve=data.get("show_on_resolve", True),
            show_on_change=data.get("show_on_change", True),
        )


class ObservationDisplayHooks:
    """
    Hook handlers for observation visualization.

    Renders observation status in various formats for display.
    """

    def __init__(self, config: DisplayConfig, coordinator: Any) -> None:
        """
        Initialize display hooks.

        Args:
            config: Display configuration
            coordinator: Orchestrator coordinator
        """
        self.config = config
        self.coordinator = coordinator
        self._last_observation_count: int = 0

    async def on_observations_change(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Handle observation changes and render display.

        Args:
            event: Hook event data

        Returns:
            HookResult dict
        """
        # Get current observations
        observations = await self._get_observations()

        if not observations:
            return {"action": "continue"}

        current_count = len(observations)

        # Check if we should display
        should_display = False
        if self.config.show_on_create and current_count > self._last_observation_count:
            should_display = True
        elif self.config.show_on_change and current_count != self._last_observation_count:
            should_display = True

        self._last_observation_count = current_count

        if not should_display:
            return {"action": "continue"}

        # Render display
        display = self._render_observations(observations)

        return {
            "action": "display",
            "content": display,
        }

    async def _get_observations(self) -> list[dict[str, Any]]:
        """Get observations from tool."""
        try:
            tool = self.coordinator.get_tool("observations")
            if tool:
                result = await tool({"operation": "list"})
                return result.get("observations", [])
        except Exception as e:
            logger.debug(f"Could not get observations: {e}")
        return []

    def _render_observations(self, observations: list[dict[str, Any]]) -> str:
        """Render observations based on configured style."""
        if self.config.style == "progress_bar":
            return self._render_progress_bar(observations)
        elif self.config.style == "table":
            return self._render_table(observations)
        else:
            return self._render_compact(observations)

    def _render_compact(self, observations: list[dict[str, Any]]) -> str:
        """Render compact single-line display."""
        by_status = self._count_by_status(observations)
        by_severity = self._count_by_severity(observations)

        open_count = by_status.get("open", 0)
        ack_count = by_status.get("acknowledged", 0)
        resolved_count = by_status.get("resolved", 0)

        critical = by_severity.get("critical", 0)
        high = by_severity.get("high", 0)

        severity_str = ""
        if critical > 0:
            severity_str = f" ({critical} critical)"
        elif high > 0:
            severity_str = f" ({high} high)"

        return (
            f"Observations: {open_count} open, {ack_count} ack, {resolved_count} done{severity_str}"
        )

    def _render_progress_bar(self, observations: list[dict[str, Any]]) -> str:
        """Render progress bar style display."""
        if not observations:
            return "Observations: [No observations]"

        by_status = self._count_by_status(observations)
        total = len(observations)

        ack_count = by_status.get("acknowledged", 0)
        resolved_count = by_status.get("resolved", 0)

        # Build progress bar
        bar_width = 20
        resolved_width = int((resolved_count / total) * bar_width)
        ack_width = int((ack_count / total) * bar_width)
        open_width = max(0, bar_width - resolved_width - ack_width)

        bar = "=" * resolved_width + "~" * ack_width + " " * open_width

        # Add severity indicators
        by_severity = self._count_by_severity(observations)
        severity_markers = []
        if by_severity.get("critical", 0) > 0:
            severity_markers.append(f"!{by_severity['critical']}")
        if by_severity.get("high", 0) > 0:
            severity_markers.append(f"^{by_severity['high']}")

        severity_str = " ".join(severity_markers)
        if severity_str:
            severity_str = f" {severity_str}"

        return f"Observations: [{bar}] {resolved_count}/{total}{severity_str}"

    def _render_table(self, observations: list[dict[str, Any]]) -> str:
        """Render table style display."""
        lines = ["Observations:"]
        lines.append("-" * 60)
        lines.append(f"{'Severity':<10} {'Observer':<20} {'Status':<12} {'Content':<30}")
        lines.append("-" * 60)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_obs = sorted(
            observations, key=lambda x: severity_order.get(x.get("severity", "info"), 5)
        )

        for obs in sorted_obs[:10]:  # Limit to 10 rows
            severity = obs.get("severity", "info")[:10]
            observer = obs.get("observer", "unknown")[:20]
            status = obs.get("status", "open")[:12]
            content = obs.get("content", "")[:30]
            if len(obs.get("content", "")) > 30:
                content = content[:27] + "..."

            lines.append(f"{severity:<10} {observer:<20} {status:<12} {content}")

        if len(observations) > 10:
            lines.append(f"... and {len(observations) - 10} more")

        lines.append("-" * 60)

        return "\n".join(lines)

    def _count_by_status(self, observations: list[dict[str, Any]]) -> dict[str, int]:
        """Count observations by status."""
        counts: dict[str, int] = {}
        for obs in observations:
            status = obs.get("status", "open")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _count_by_severity(self, observations: list[dict[str, Any]]) -> dict[str, int]:
        """Count observations by severity."""
        counts: dict[str, int] = {}
        for obs in observations:
            severity = obs.get("severity", "info")
            counts[severity] = counts.get(severity, 0) + 1
        return counts


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """
    Mount the observations display hooks module.

    Args:
        coordinator: Orchestrator coordinator instance
        config: Module configuration
    """
    # Parse configuration
    display_config = DisplayConfig.from_dict(config or {})

    # Create hooks handler
    hooks = ObservationDisplayHooks(display_config, coordinator)

    # Register display hook using standard Amplifier pattern
    coordinator.hooks.register(
        "observations:change",
        hooks.on_observations_change,
        priority=100,  # Low priority, runs last
        name="hooks-observations-display",
    )

    logger.info(f"Mounted hooks-observations-display module (style: {display_config.style})")
