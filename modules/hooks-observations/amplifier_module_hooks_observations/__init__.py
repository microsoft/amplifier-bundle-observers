"""
Observations Hooks Module

Hook-driven observer orchestration that:
- Detects changes in files and conversation
- Spawns observer agents in parallel
- Aggregates results and writes to observations tool
- Injects observation summaries into context
"""

import asyncio
import hashlib
import json
import logging
import os
from glob import glob
from pathlib import Path
from typing import Any

from amplifier_core import HookResult

from .loader import LoadedObserver, load_observer
from .models import (
    ObservationsModuleConfig,
    ObserverReference,
    WatchType,
)

logger = logging.getLogger(__name__)


class ObservationHooks:
    """
    Hook handlers for observer orchestration.

    Manages the lifecycle of observers:
    1. Change detection (file/conversation hashing)
    2. Parallel observer spawning
    3. Result aggregation
    4. Context injection
    """

    def __init__(
        self,
        config: ObservationsModuleConfig,
        coordinator: Any,
        base_path: Path | None = None,
    ) -> None:
        """
        Initialize observation hooks.

        Args:
            config: Module configuration
            coordinator: Orchestrator coordinator for spawning sessions
            base_path: Base path for resolving relative observer references
        """
        self.config = config
        self.coordinator = coordinator
        self.base_path = base_path or Path.cwd()
        self._last_state_hash: str | None = None
        self._loaded_observers: dict[str, LoadedObserver] = {}
        self._protocol_instructions: str | None = None

    async def trigger_observers(self, event_name: str, event_data: dict[str, Any]) -> HookResult:
        """
        Main hook handler triggered by orchestrator events.

        Detects changes, spawns observers, and writes results.

        Args:
            event_name: Name of the event (e.g., "prompt:complete")
            event_data: Hook event data from orchestrator

        Returns:
            HookResult dict with action
        """
        logger.info(f"trigger_observers called: {event_name}")
        logger.info(f"Configured observers: {len(self.config.observers)}")

        # Use event_data instead of event for the rest of the method
        event = event_data

        # Skip if no observers configured
        if not self.config.observers:
            logger.warning("No observers configured - skipping")
            return HookResult(action="continue")

        # Get only enabled observers
        enabled_observers = [o for o in self.config.observers if o.enabled]
        if not enabled_observers:
            return HookResult(action="continue")

        # Change detection
        current_hash = await self._compute_state_hash(enabled_observers, event)

        if current_hash == self._last_state_hash:
            logger.debug("No changes detected, skipping observation")
            return HookResult(action="continue")

        logger.info(f"Changes detected, triggering {len(enabled_observers)} observer(s)")

        try:
            # Spawn observers in parallel
            results = await self._run_observers_parallel(enabled_observers, event)
            logger.info(f"Observer results: {len(results)} results")

            # Aggregate observations and resolutions
            observations, resolved = self._aggregate_results(results)
            logger.info(
                f"Aggregated: {len(observations)} new observations, {len(resolved)} resolved"
            )

            if observations:
                # Write new observations to tool
                await self._write_observations(observations)
                logger.info(f"Created {len(observations)} observation(s)")

            if resolved:
                # Resolve fixed observations
                await self._resolve_observations(resolved)
                logger.info(f"Resolved {len(resolved)} observation(s)")

            # Update state hash
            self._last_state_hash = current_hash

            return HookResult(action="continue")
        except Exception as e:
            logger.exception(f"Error in trigger_observers: {e}")
            return HookResult(action="continue")

    async def inject_observations(self, event_name: str, event_data: dict[str, Any]) -> HookResult:
        """
        Inject observation summary into context after response.

        Args:
            event_name: Name of the event
            event_data: Hook event data

        Returns:
            HookResult with context injection if observations exist
        """
        # Get open observations from tool
        observations = await self._get_open_observations()

        if not observations:
            return HookResult(action="continue")

        # Format summary
        summary = self._format_observations_summary(observations)

        return HookResult(
            action="inject_context",
            context_injection=f"""<system-reminder source="observers">
{summary}

Please review and address these observations in your response.
</system-reminder>""",
            context_injection_role="system",
        )

    async def _ensure_observers_loaded(self) -> None:
        """Load all observer definitions if not already loaded."""
        if self._loaded_observers:
            return

        sources = self._get_bundle_sources()

        for ref in self.config.observers:
            if not ref.enabled:
                continue

            try:
                observer = await load_observer(
                    ref.observer,
                    sources=sources,
                    base_path=self.base_path,
                )

                # Apply overrides from hook config
                if ref.model:
                    observer.model = ref.model
                if ref.timeout:
                    observer.timeout = ref.timeout

                self._loaded_observers[ref.observer] = observer
                logger.info(f"Loaded observer: {observer.name} from {ref.observer}")

            except Exception as e:
                logger.error(f"Failed to load observer {ref.observer}: {e}")

    def _get_bundle_sources(self) -> dict[str, str]:
        """Get bundle sources for observer resolution.

        Sources can come from:
        1. Explicit config.sources mapping (preferred)
        2. Coordinator's bundle registry (auto-discovery)

        Returns:
            Mapping of bundle names to their base paths
        """
        sources: dict[str, str] = {}

        # 1. Start with explicitly configured sources
        if self.config.sources:
            sources.update(self.config.sources)

        # 2. Try to auto-discover from coordinator's bundle registry
        try:
            bundles = self.coordinator.get("bundles")
            if bundles:
                for name, bundle in bundles.items():
                    if name not in sources:  # Don't override explicit config
                        bundle_base = getattr(bundle, "base_path", None)
                        if bundle_base:
                            sources[name] = str(bundle_base)
        except Exception as e:
            logger.debug(f"Could not get bundles from coordinator: {e}")

        return sources

    async def _load_protocol_instructions(self) -> str:
        """Load the observer protocol instructions from context file."""
        if self._protocol_instructions:
            return self._protocol_instructions

        # Try to load from bundle context
        protocol_path = self.base_path / "context" / "observer-protocol.md"
        if protocol_path.exists():
            self._protocol_instructions = protocol_path.read_text(encoding="utf-8")
        else:
            # Fallback to embedded protocol
            self._protocol_instructions = self._get_default_protocol()

        return self._protocol_instructions

    def _get_default_protocol(self) -> str:
        """Return default observer protocol if context file not found."""
        return """## Output Format

Respond with valid JSON only:

```json
{
  "observations": [
    {
      "content": "Description of the NEW issue",
      "severity": "critical|high|medium|low|info",
      "source_ref": "file:line or context reference",
      "metadata": {
        "category": "security|quality|logic|performance",
        "suggestion": "How to fix (optional)"
      }
    }
  ],
  "resolved": [
    {
      "id": "id of issue that is now fixed",
      "reason": "Brief explanation"
    }
  ]
}
```

If no new issues and nothing resolved: `{"observations": [], "resolved": []}`
"""

    async def _compute_state_hash(
        self,
        observer_refs: list[ObserverReference],
        event: dict[str, Any],
    ) -> str:
        """Compute hash of current state for change detection."""
        state_parts = []

        for ref in observer_refs:
            for watch in ref.watch:
                if watch.type == WatchType.FILES:
                    file_state = self._get_file_state(watch.paths or [])
                    state_parts.append(file_state)
                elif watch.type == WatchType.CONVERSATION:
                    conv_state = self._get_conversation_state(event)
                    state_parts.append(conv_state)

        combined = "|".join(state_parts)
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_file_state(self, paths: list[str]) -> str:
        """Compute hash of file metadata for change detection."""
        file_info = []

        for pattern in paths:
            for file_path in glob(pattern, recursive=True):
                if os.path.isfile(file_path):
                    try:
                        stat = os.stat(file_path)
                        file_info.append((file_path, stat.st_mtime, stat.st_size))
                    except OSError:
                        continue

        file_info.sort()
        return hashlib.md5(json.dumps(file_info).encode()).hexdigest()

    def _get_conversation_state(self, event: dict[str, Any]) -> str:
        """Compute hash of conversation state."""
        messages = event.get("messages", [])

        # Filter to relevant messages
        relevant = [
            {"role": m.get("role"), "content": m.get("content", "")[:500]}
            for m in messages
            if m.get("role") in ("user", "assistant", "tool")
        ]

        return hashlib.md5(json.dumps(relevant, sort_keys=True).encode()).hexdigest()

    async def _run_observers_parallel(
        self,
        observer_refs: list[ObserverReference],
        event: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Run all observers in parallel with timeout."""
        max_concurrent = self.config.execution.max_concurrent

        # Ensure all observers are loaded
        await self._ensure_observers_loaded()

        # Fetch existing observations ONCE for all observers (deduplication context)
        existing_observations = await self._get_open_observations()
        if existing_observations:
            logger.debug(f"Passing {len(existing_observations)} existing observations to observers")

        # Load protocol instructions
        protocol = await self._load_protocol_instructions()

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(ref: ObserverReference) -> dict[str, Any]:
            async with semaphore:
                loaded = self._loaded_observers.get(ref.observer)
                if not loaded:
                    logger.warning(f"Observer not loaded: {ref.observer}")
                    return {"observations": [], "resolved": []}
                return await self._spawn_observer(
                    loaded, ref, event, existing_observations, protocol
                )

        # Create tasks
        tasks = [run_with_semaphore(ref) for ref in observer_refs]

        # Run with global timeout
        global_timeout = self.config.execution.timeout_per_observer * 2
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=global_timeout,
            )
        except TimeoutError:
            logger.warning("Global observer timeout reached")
            results = []

        return [r for r in results if isinstance(r, dict)]

    async def _spawn_observer(
        self,
        observer: LoadedObserver,
        ref: ObserverReference,
        event: dict[str, Any],
        existing_observations: list[dict[str, Any]] | None = None,
        protocol: str | None = None,
    ) -> dict[str, Any]:
        """Spawn a single observer using loaded definition."""
        try:
            # Build content to review based on watch config
            content = await self._build_review_content(ref, event)

            # Build the full prompt with observer instructions, content, and protocol
            prompt = self._build_observer_prompt(observer, content, existing_observations, protocol)

            # Check if observer has tools - use spawn capability if so
            if observer.tools:
                return await self._spawn_with_tools(observer, prompt)

            # Otherwise use direct provider call (faster for simple observers)
            return await self._spawn_direct(observer, prompt)

        except TimeoutError:
            logger.warning(f"Observer '{observer.name}' timed out")
            if self.config.execution.on_timeout == "fail":
                raise
            return {"observations": [], "resolved": [], "error": "timeout"}

        except Exception as e:
            logger.exception(f"Observer '{observer.name}' failed: {e}")
            return {"observations": [], "resolved": [], "error": str(e)}

    async def _spawn_with_tools(
        self,
        observer: LoadedObserver,
        prompt: str,
    ) -> dict[str, Any]:
        """Spawn observer using session.spawn capability with tools."""
        # Get spawn capability from coordinator
        spawn = self.coordinator.get("capabilities", "spawn")
        if not spawn:
            logger.warning(
                f"Spawn capability not available, falling back to direct for {observer.name}"
            )
            return await self._spawn_direct(observer, prompt)

        try:
            # Build system instruction from observer definition
            system_instruction = observer.get_full_instruction()

            result = await asyncio.wait_for(
                spawn(
                    instruction=prompt,
                    system=system_instruction,
                    model=observer.model,
                    tools=observer.tools,
                ),
                timeout=observer.timeout,
            )

            # Parse the result - spawn returns a string response
            if isinstance(result, str):
                return self._parse_observer_result(result, observer.name)
            elif isinstance(result, dict):
                return result
            else:
                logger.warning(f"Unexpected spawn result type: {type(result)}")
                return {"observations": [], "resolved": []}

        except Exception as e:
            logger.exception(f"Spawn failed for observer '{observer.name}': {e}")
            return {"observations": [], "resolved": [], "error": str(e)}

    async def _spawn_direct(
        self,
        observer: LoadedObserver,
        prompt: str,
    ) -> dict[str, Any]:
        """Spawn observer using direct provider call (no tools)."""
        from amplifier_core import ChatRequest, Message

        # Get provider from coordinator
        providers = self.coordinator.get("providers")
        if not providers:
            logger.warning(f"No providers available for observer '{observer.name}'")
            return {"observations": [], "resolved": []}

        # Get first available provider
        provider = list(providers.values())[0]
        logger.debug(f"Using direct provider for observer '{observer.name}'")

        # Build system message from observer definition
        system_content = observer.get_full_instruction()

        # Create request
        messages = [
            Message(role="system", content=system_content),
            Message(role="user", content=prompt),
        ]

        # model is passed as extra field (ChatRequest has extra="allow")
        request = ChatRequest(messages=messages, model=observer.model)  # type: ignore[call-arg]

        # Make the LLM call
        response = await asyncio.wait_for(
            provider.complete(request),
            timeout=observer.timeout,
        )

        # Extract text from response content blocks
        text_result = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_result += block.text

        logger.debug(f"Observer '{observer.name}' response length: {len(text_result)}")
        return self._parse_observer_result(text_result, observer.name)

    async def _build_review_content(
        self,
        ref: ObserverReference,
        event: dict[str, Any],
    ) -> str:
        """Build the content for an observer to review."""
        content_parts = []

        for watch in ref.watch:
            if watch.type == WatchType.FILES:
                file_content = await self._get_file_content(watch.paths or [])
                if file_content:
                    content_parts.append("## Files\n\n" + file_content)

            elif watch.type == WatchType.CONVERSATION:
                conv_content = self._get_conversation_content(
                    event,
                    include_tool_calls=watch.include_tool_calls,
                    include_reasoning=watch.include_reasoning,
                )
                if conv_content:
                    content_parts.append("## Conversation\n\n" + conv_content)

        return "\n\n---\n\n".join(content_parts)

    async def _get_file_content(self, paths: list[str], max_size: int = 50000) -> str:
        """Read file contents for review."""
        content_parts = []
        total_size = 0

        for pattern in paths:
            for file_path in glob(pattern, recursive=True):
                if not os.path.isfile(file_path):
                    continue

                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()

                    # Truncate if too large
                    remaining = max_size - total_size
                    if len(file_content) > remaining:
                        file_content = file_content[:remaining] + "\n... [truncated]"

                    content_parts.append(f"### {file_path}\n```\n{file_content}\n```")
                    total_size += len(file_content)

                    if total_size >= max_size:
                        break

                except Exception as e:
                    logger.debug(f"Could not read {file_path}: {e}")

            if total_size >= max_size:
                break

        return "\n\n".join(content_parts)

    def _get_conversation_content(
        self,
        event: dict[str, Any],
        include_tool_calls: bool = True,
        include_reasoning: bool = True,
    ) -> str:
        """Extract conversation content for review."""
        messages = event.get("messages", [])
        content_parts = []

        for msg in messages[-20:]:  # Last 20 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "tool" and not include_tool_calls:
                continue

            # Truncate long content
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"

            content_parts.append(f"**{role}**: {content}")

        return "\n\n".join(content_parts)

    def _build_observer_prompt(
        self,
        observer: LoadedObserver,
        content: str,
        existing_observations: list[dict[str, Any]] | None = None,
        protocol: str | None = None,
    ) -> str:
        """Build the prompt for an observer agent.

        The prompt combines:
        1. Content to review
        2. Existing observations (for deduplication/resolution)
        3. Protocol instructions (output format)
        """
        # Build existing observations section
        existing_section = ""
        if existing_observations:
            existing_list = "\n".join(
                f"- id=`{obs.get('id', 'unknown')}` [{obs.get('severity', 'info')}] "
                f"{obs.get('source_ref', 'unknown')}: {obs.get('content', '')[:150]}"
                for obs in existing_observations
            )
            existing_section = f"""
## Previously Reported Issues

The following issues were previously reported. Review them against the current content:

{existing_list}

**Your tasks:**
1. Do NOT report these again if they still exist
2. If an issue has been FIXED (no longer present in the content), mark it as resolved

"""

        # Use provided protocol or default
        protocol_section = protocol or self._get_default_protocol()

        # Replace placeholder in protocol with actual existing observations
        if "{{existing_observations}}" in protocol_section:
            if existing_observations:
                obs_text = existing_section
            else:
                obs_text = "No previously reported issues."
            protocol_section = protocol_section.replace("{{existing_observations}}", obs_text)

        return f"""## Content to Review

{content}
{existing_section}
{protocol_section}
"""

    def _parse_observer_result(
        self, result: str | dict[str, Any], observer_name: str
    ) -> dict[str, Any]:
        """Parse observer agent response into structured observations."""
        # Log the raw result for debugging
        logger.debug(f"Observer '{observer_name}' raw result type: {type(result)}")
        if isinstance(result, dict):
            logger.debug(f"Observer '{observer_name}' result keys: {result.keys()}")

        # Extract text from dict result (from spawn_capability)
        text_result: str = ""
        if isinstance(result, dict):
            # Try multiple possible keys for the response content
            # The spawn capability may return different structures
            for key in ["output", "result", "response", "content", "text"]:
                if key in result and result[key]:
                    text_result = str(result[key])
                    logger.debug(f"Found result in key '{key}'")
                    break

            # If still empty, try to stringify the whole dict
            if not text_result:
                # Check if it's a nested structure
                if "data" in result and isinstance(result["data"], dict):
                    text_result = str(result["data"].get("output", ""))
                elif not text_result:
                    # Last resort: convert whole result to string
                    text_result = json.dumps(result) if result else ""
                    logger.debug(f"Using stringified result: {text_result[:200]}")
        else:
            text_result = str(result)

        logger.debug(
            f"Observer '{observer_name}' extracted text (first 500 chars): {text_result[:500]}"
        )

        # Try to extract JSON from response
        try:
            json_text = text_result

            # Handle case where result might be wrapped in markdown code blocks
            if "```json" in json_text:
                start = json_text.find("```json") + 7
                end = json_text.find("```", start)
                if end > start:
                    json_text = json_text[start:end].strip()
            elif "```" in json_text:
                start = json_text.find("```") + 3
                end = json_text.find("```", start)
                if end > start:
                    json_text = json_text[start:end].strip()

            # Try to find JSON object in the text if not already valid JSON
            if not json_text.strip().startswith("{"):
                # Look for JSON object pattern
                import re

                json_match = re.search(
                    r"\{[^{}]*\"observations\"[^{}]*\[.*?\]\s*\}", json_text, re.DOTALL
                )
                if json_match:
                    json_text = json_match.group(0)
                    logger.debug(f"Extracted JSON via regex: {json_text[:200]}")

            data = json.loads(json_text)
            logger.debug(
                f"Successfully parsed JSON with keys: {data.keys() if isinstance(data, dict) else 'N/A'}"
            )

            if "observations" in data:
                for obs in data["observations"]:
                    obs["observer"] = observer_name
                    obs.setdefault("status", "open")
                    obs.setdefault("source_type", "mixed")
                    obs.setdefault("metadata", {})

                # Ensure resolved array exists (may be empty)
                data.setdefault("resolved", [])
                return data

        except json.JSONDecodeError:
            # Fallback: treat as plain text observation if it seems important
            if len(text_result.strip()) > 50 and not text_result.startswith("No issues"):
                return {
                    "observations": [
                        {
                            "observer": observer_name,
                            "content": text_result[:500],
                            "severity": "info",
                            "status": "open",
                            "source_type": "unknown",
                            "metadata": {"parse_error": True},
                        }
                    ]
                }

        return {"observations": []}

    def _aggregate_results(
        self, results: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Aggregate observations and resolutions from all observer results.

        Returns:
            Tuple of (new_observations, resolved_items)
        """
        observations = []
        resolved = []
        seen_obs_keys: set[str] = set()
        seen_resolved_ids: set[str] = set()

        for result in results:
            if not isinstance(result, dict):
                continue

            # Aggregate new observations
            for obs in result.get("observations", []):
                key = self._observation_key(obs)
                if key not in seen_obs_keys:
                    seen_obs_keys.add(key)
                    observations.append(obs)
                else:
                    logger.debug(f"Skipping duplicate observation: {key[:50]}...")

            # Aggregate resolved items
            for res in result.get("resolved", []):
                res_id = res.get("id", "")
                if res_id and res_id not in seen_resolved_ids:
                    seen_resolved_ids.add(res_id)
                    resolved.append(res)

        return observations, resolved

    def _observation_key(self, obs: dict[str, Any]) -> str:
        """Generate a deduplication key for an observation.

        Strategy varies by source type:
        - File-based with source_ref: observer + source_ref + severity
        - Conversation/other: observer + category + severity (+ content hash fallback)

        Does NOT use raw LLM content since wording varies between runs.
        """
        observer = obs.get("observer", "")
        source_ref = obs.get("source_ref", "")
        severity = obs.get("severity", "")
        source_type = obs.get("source_type", "unknown")
        metadata = obs.get("metadata", {}) or {}
        category = metadata.get("category", "")

        # File-based with specific location: dedupe on location
        if source_ref and source_type == "file":
            return f"{observer}:file:{source_ref}:{severity}"

        # Has category (conversation or file): use category for stability
        if category:
            # Include source_ref if available (might be "turn:5" etc)
            return f"{observer}:{category}:{severity}:{source_ref}"

        # Fallback: normalized content hash (handles edge cases)
        content = obs.get("content", "")
        normalized = " ".join(content.lower().split())[:100]
        content_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
        return f"{observer}:{severity}:{content_hash}"

    async def _write_observations(self, observations: list[dict[str, Any]]) -> None:
        """Write observations to the observations tool, skipping duplicates."""
        try:
            # Use coordinator.get() to access tools by mount point
            tool = self.coordinator.get("tools", "observations")
            if not tool:
                return

            # Get existing observations to avoid duplicates
            existing = await self._get_open_observations()
            existing_keys = {self._observation_key(obs) for obs in existing}

            # Filter out duplicates
            new_observations = [
                obs for obs in observations if self._observation_key(obs) not in existing_keys
            ]

            if not new_observations:
                logger.debug("All observations already exist, skipping write")
                return

            skipped = len(observations) - len(new_observations)
            if skipped > 0:
                logger.debug(f"Skipping {skipped} duplicate observation(s)")

            # Tools have an execute() method
            await tool.execute(
                {
                    "operation": "create_batch",
                    "observations": new_observations,
                }
            )
            logger.info(f"Wrote {len(new_observations)} observations to tool")
        except Exception as e:
            logger.exception(f"Failed to write observations: {e}")

    async def _resolve_observations(self, resolved: list[dict[str, Any]]) -> None:
        """Resolve observations that the observer detected as fixed."""
        try:
            tool = self.coordinator.get("tools", "observations")
            if not tool:
                return

            for item in resolved:
                obs_id = item.get("id")
                reason = item.get("reason", "Issue no longer detected by observer")

                if not obs_id:
                    continue

                try:
                    await tool.execute(
                        {
                            "operation": "resolve",
                            "observation_id": obs_id,
                            "resolution_note": f"Auto-resolved: {reason}",
                        }
                    )
                    logger.debug(f"Resolved observation {obs_id}: {reason}")
                except Exception as e:
                    logger.warning(f"Failed to resolve observation {obs_id}: {e}")

        except Exception as e:
            logger.exception(f"Failed to resolve observations: {e}")

    async def _get_open_observations(self) -> list[dict[str, Any]]:
        """Get open observations from the tool."""
        try:
            # Use coordinator.get() to access tools by mount point
            tool = self.coordinator.get("tools", "observations")

            if tool:
                # Tools have an execute() method that returns ToolResult
                result = await tool.execute(
                    {
                        "operation": "list",
                        "filters": {"status": "open"},
                    }
                )
                # ToolResult has .output attribute containing the actual data
                if result.success and result.output:
                    return result.output.get("observations", [])
        except Exception as e:
            logger.debug(f"Could not get observations: {e}")

        return []

    def _format_observations_summary(self, observations: list[dict[str, Any]]) -> str:
        """Format observations for context injection."""
        by_severity: dict[str, int] = {}
        for obs in observations:
            sev = obs.get("severity", "info")
            by_severity[sev] = by_severity.get(sev, 0) + 1

        lines = [
            f"Active Observations: {len(observations)} open",
            f"By Severity: {', '.join(f'{sev}: {count}' for sev, count in by_severity.items())}",
        ]

        # Group by observer
        by_observer: dict[str, list[dict[str, Any]]] = {}
        for obs in observations:
            observer = obs.get("observer", "unknown")
            if observer not in by_observer:
                by_observer[observer] = []
            by_observer[observer].append(obs)

        for observer, obs_list in by_observer.items():
            lines.append(f"\n**{observer}** ({len(obs_list)} observations):")
            for obs in obs_list[:3]:  # Top 3 per observer
                lines.append(f"  [{obs.get('severity', 'info')}] {obs.get('content', '')[:100]}")
            if len(obs_list) > 3:
                lines.append(f"  ... and {len(obs_list) - 3} more")

        return "\n".join(lines)


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """
    Mount the observations hooks module.

    Args:
        coordinator: Orchestrator coordinator instance
        config: Module configuration
    """

    # Parse configuration
    module_config = ObservationsModuleConfig.from_dict(config or {})

    # Create hooks handler
    hooks = ObservationHooks(module_config, coordinator)

    # Register hooks based on configuration using standard Amplifier pattern
    for hook_config in module_config.hooks:
        coordinator.hooks.register(
            hook_config.trigger,
            hooks.trigger_observers,
            priority=hook_config.priority,
            name="hooks-observations",
        )

    # Register injection hook - inject observations at START of next turn
    coordinator.hooks.register(
        "prompt:submit",
        hooks.inject_observations,
        priority=10,  # Early in the hook chain
        name="hooks-observations-inject",
    )

    logger.info(
        f"Mounted hooks-observations module with {len(module_config.observers)} observer(s)"
    )
