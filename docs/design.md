# Observer Bundle Design Specification

## Overview

The Observer Bundle provides automated code and conversation review capabilities through specialized AI agents (observers) that monitor work in progress and provide feedback. Observers run in parallel, triggered by hooks, and persist their findings in the session state for the main agent to address.

### Core Capabilities

- **Parallel observation**: Multiple specialized observers run concurrently
- **Multi-source monitoring**: Watch files, conversation transcripts, or both
- **Session-based persistence**: Observations stored in session transcript (JSONL)
- **Hook-driven execution**: Triggered by orchestrator events
- **Flexible feedback**: Support multiple feedback delivery mechanisms
- **Change detection**: Avoid redundant reviews through state hashing

### Use Cases

- Code quality review (syntax, patterns, best practices)
- Security analysis (vulnerabilities, unsafe patterns)
- Logic checking (reasoning errors, assumptions)
- Content review (clarity, accuracy, completeness)
- Multi-phase analysis (fast scan → deep review)

---

## Architecture

The Observer Bundle consists of three separate modules that compose together:

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Orchestrator                       │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Hooks Coordinator                                   │   │
│  │  - message:received → observer_hook                │   │
│  │  - response:complete → inject_observations         │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│          Module 1: hooks-observations                        │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Observer Coordinator                                │   │
│  │  - Detect changes (file/conversation hashing)      │   │
│  │  - Spawn observers in parallel (asyncio.gather)    │   │
│  │  - Aggregate results                               │   │
│  │  - Write to observations tool                      │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │Observer A│    │Observer B│    │Observer C│
        │ Session  │    │ Session  │    │ Session  │
        └──────────┘    └──────────┘    └──────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│          Module 2: tool-observations                         │
│  ┌────────────────────────────────────────────────────┐   │
│  │ State Management                                    │   │
│  │  - CRUD operations (create, list, acknowledge)     │   │
│  │  - Session transcript persistence (JSONL)          │   │
│  │  - Query/filter by severity, observer, status      │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│          Module 3: hooks-observations-display (Optional)     │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Visualization                                       │   │
│  │  - Render observation status (progress bar style)  │   │
│  │  - Display by severity/observer                    │   │
│  │  - Show acknowledgment counts                      │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

#### 1. tool-observations (Core State Management)
- Manages observation state in session transcript
- Provides CRUD API for observations
- Handles persistence in JSONL format
- No business logic - pure data management

#### 2. hooks-observations (Orchestration Integration)
- Registers hooks with orchestrator coordinator
- Implements change detection (MD5 hashing)
- Spawns observers in parallel via asyncio
- Aggregates results and writes to tool-observations
- Injects observation summary into context

#### 3. hooks-observations-display (Optional Visualization)
- Registers display hooks
- Renders observation status in UI/terminal
- Shows progress and severity distribution
- Similar to todo tool progress bar

---

## Observation Dimensions (Orthogonal Concerns)

Observers are configured along three independent dimensions:

### Dimension 1: What to Observe (Target)

**Files**
- Monitors file system for changes
- Detects via MD5 hash of `(path, mtime, size)` tuples
- Reviews file content
- Best for artifact quality (code, documents, output)

**Conversation**
- Monitors conversation transcript
- Detects via MD5 hash of messages
- Reviews reasoning, tool usage, responses
- Best for logic/methodology quality

**Both**
- Observer can watch multiple sources
- Useful for comprehensive review
- Example: Security reviewer checks both code and reasoning

### Dimension 2: When to Trigger (Hook)

**message:received**
- After user sends message, before main processing
- Useful for pre-flight checks

**response:complete**
- After main agent completes response
- Most common trigger point
- Allows reviewing what was just produced

**tool:post**
- After specific tool executes
- Targeted observation (e.g., after file write)

**Custom hooks**
- Extensible for specific workflows

### Dimension 3: How to Execute (Execution Model)

**Parallel with Wait** (Primary Design)
- All observers spawn simultaneously
- Hook waits for all to complete (asyncio.gather)
- Results aggregated before continuing
- Timeout per observer (default: 30s)

**Configuration**:
```yaml
execution:
  mode: parallel_sync
  max_concurrent: 10      # Limit parallelism
  timeout_per_observer: 30  # Seconds
  on_timeout: skip        # or 'fail'
```

---

## Hook-Based Execution Model

### Hook Flow

```
1. Orchestrator event fires (e.g., message:received)
      ↓
2. Hook observer_hook triggered
      ↓
3. Change detection (hash current state)
      ↓
4. If unchanged → exit early
   If changed → continue
      ↓
5. Spawn all configured observers in parallel
   observer_tasks = [spawn_observer(obs) for obs in config.observers]
      ↓
6. Wait for all completions
   results = await asyncio.gather(*observer_tasks, return_exceptions=True)
      ↓
7. Aggregate results into observations
   observations = aggregate_results(results)
      ↓
8. Write to tool-observations
   await tool.create_observations(observations)
      ↓
9. Hook completes, orchestrator continues
```

### Implementation Pattern

```python
async def observer_hook(context: OrchestrationContext, event: HookEvent) -> HookResult:
    """Main observer hook triggered by orchestrator."""

    # 1. Change detection
    current_state = await get_observation_target_state(context, config.observers)
    state_hash = hashlib.md5(current_state.encode()).hexdigest()

    if state_hash == context.get_metadata("last_observation_state"):
        # No changes detected, skip observation
        return HookResult(action="continue")

    # 2. Spawn observers in parallel
    observer_tasks = []
    for observer_config in config.observers:
        task = spawn_observer(observer_config, context)
        observer_tasks.append(task)

    # 3. Wait for all with timeout
    try:
        results = await asyncio.gather(*observer_tasks, return_exceptions=True)
    except asyncio.TimeoutError:
        # Handle timeout based on config
        if config.on_timeout == "fail":
            return HookResult(action="deny", reason="Observer timeout")
        # else: skip and continue

    # 4. Aggregate and persist
    observations = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Observer failed: {result}")
            continue
        if result and result.get("observations"):
            observations.extend(result["observations"])

    if observations:
        await context.call_tool("observations", {
            "operation": "create_batch",
            "observations": observations
        })

    # 5. Update state hash
    context.set_metadata("last_observation_state", state_hash)

    return HookResult(action="continue")


async def spawn_observer(
    observer_config: ObserverConfig,
    context: OrchestrationContext
) -> dict:
    """Spawn single observer agent with timeout."""

    # Build observer-specific prompt
    prompt = build_observer_prompt(observer_config, context)

    # Create ephemeral session
    async with AmplifierSession(observer_config.mount_plan, loader=context.loader) as session:
        try:
            result = await asyncio.wait_for(
                session.execute(prompt),
                timeout=observer_config.timeout
            )
            return parse_observer_result(result, observer_config.name)

        except asyncio.TimeoutError:
            return {"error": "timeout", "observer": observer_config.name}
```

### Change Detection

**File Watching**:
```python
def get_file_state(paths: list[str]) -> str:
    """Compute hash of file metadata."""
    file_info = []
    for path in paths:
        for file_path in glob(path):
            stat = os.stat(file_path)
            file_info.append((file_path, stat.st_mtime, stat.st_size))

    file_info.sort()  # Consistent ordering
    state_str = json.dumps(file_info)
    return hashlib.md5(state_str.encode()).hexdigest()
```

**Conversation Watching**:
```python
def get_conversation_state(context: OrchestrationContext) -> str:
    """Compute hash of conversation transcript."""
    messages = context.get_messages()

    # Filter to relevant messages (user, assistant, tool)
    relevant = [m for m in messages if m["role"] in ("user", "assistant", "tool")]

    # Serialize and hash
    conversation_str = json.dumps(relevant, sort_keys=True)
    return hashlib.md5(conversation_str.encode()).hexdigest()
```

---

## State Management

### Session-Based Persistence

Observations are stored in the session transcript using JSONL format, following the same pattern as the todo tool.

**Storage Location**: `~/.config/claude/projects/{project-hash}/{session-id}.jsonl`

**Benefits**:
- Automatic persistence via session infrastructure
- No separate file I/O
- Can resume sessions with observation state intact
- Observations visible in conversation history
- No file locking conflicts

### Observation Data Structure

```python
@dataclass
class Observation:
    id: str                    # UUID
    observer: str              # Observer name that created it
    content: str               # Observation text
    severity: str              # "critical" | "high" | "medium" | "low" | "info"
    status: str                # "open" | "acknowledged" | "resolved"
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    metadata: dict[str, Any]   # Extensible metadata
    source_type: str           # "file" | "conversation" | "mixed"
    source_ref: str | None     # File path or message ID

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "observer": self.observer,
            "content": self.content,
            "severity": self.severity,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
            "source_type": self.source_type,
            "source_ref": self.source_ref
        }
```

### Tool API

The `tool-observations` module provides a standard tool interface:

```python
# Create observations (batch)
{
    "operation": "create_batch",
    "observations": [
        {
            "observer": "Security Reviewer",
            "content": "Found potential SQL injection in query builder",
            "severity": "critical",
            "source_type": "file",
            "source_ref": "src/database/query.py:45",
            "metadata": {
                "category": "security",
                "cwe": "CWE-89"
            }
        }
    ]
}

# Response
{
    "status": "created",
    "count": 1,
    "observations": [...],  # Full observation objects with IDs
    "by_severity": {"critical": 1},
    "by_status": {"open": 1}
}

# List observations
{
    "operation": "list",
    "filters": {
        "status": "open",           # Optional
        "severity": ["critical", "high"],  # Optional
        "observer": "Security Reviewer"   # Optional
    },
    "sort_by": "severity",  # or "created_at"
    "limit": 50
}

# Response
{
    "status": "ok",
    "observations": [...],
    "count": 10,
    "by_severity": {"critical": 2, "high": 8},
    "by_observer": {"Security Reviewer": 5, "Code Quality": 5}
}

# Acknowledge observation
{
    "operation": "acknowledge",
    "observation_id": "uuid-here"
}

# Resolve observation
{
    "operation": "resolve",
    "observation_id": "uuid-here",
    "resolution_note": "Fixed in commit abc123"  # Optional
}

# Clear all resolved
{
    "operation": "clear_resolved"
}
```

### Context Injection

After observers run, the hooks-observations module injects a summary into the next turn's context:

```python
async def inject_observations_hook(context: OrchestrationContext, event: HookEvent) -> HookResult:
    """Inject observation summary after response completes."""

    # Get current observations
    result = await context.call_tool("observations", {"operation": "list", "filters": {"status": "open"}})

    if result.get("count", 0) == 0:
        return HookResult(action="continue")

    # Build summary
    summary = format_observations_summary(result)

    # Inject into context
    return HookResult(
        action="inject_context",
        context={
            "role": "system",
            "content": f"""<observations>
{summary}
</observations>

Please review and address these observations in your response."""
        }
    )


def format_observations_summary(result: dict) -> str:
    """Format observations for context injection."""
    by_severity = result.get("by_severity", {})
    observations = result.get("observations", [])

    lines = [
        f"Active Observations: {result['count']} open",
        f"By Severity: {', '.join(f'{sev}: {count}' for sev, count in by_severity.items())}"
    ]

    # Group by observer
    by_observer = {}
    for obs in observations:
        observer = obs["observer"]
        if observer not in by_observer:
            by_observer[observer] = []
        by_observer[observer].append(obs)

    for observer, obs_list in by_observer.items():
        lines.append(f"\n**{observer}** ({len(obs_list)} observations):")
        for obs in obs_list[:3]:  # Limit to top 3
            lines.append(f"  [{obs['severity']}] {obs['content']}")
        if len(obs_list) > 3:
            lines.append(f"  ... and {len(obs_list) - 3} more")

    return "\n".join(lines)
```

---

## Observer Configuration

### Observer Config Schema

```python
@dataclass
class ObserverConfig:
    name: str                  # Display name
    role: str                  # One-line description of role
    focus: str                 # Detailed instructions on what to look for
    model: str                 # Model to use (e.g., "claude-3-5-sonnet")
    watch: list[WatchConfig]   # What to observe
    timeout: int = 30          # Timeout in seconds
    enabled: bool = True       # Can disable without removing
    metadata: dict = field(default_factory=dict)  # Custom metadata


@dataclass
class WatchConfig:
    type: str                  # "files" | "conversation"
    paths: list[str] | None = None  # For file watching (glob patterns)
    include_tool_calls: bool = True  # For conversation watching
    include_reasoning: bool = True   # For conversation watching
```

### Observer Prompting Pattern

Observers are spawned as ephemeral AmplifierSession instances. Each observer receives a specialized prompt:

```
You are **{name}**, a specialized code reviewer.

## Your Role
{role}

## Your Focus
{focus}

## Content to Review

{content}

## Instructions

1. **Analyze** the content from your specialized perspective
2. **Identify issues** that fall within your focus area
3. **Be specific** - reference exact locations (file:line or message IDs)
4. **Prioritize** - report only significant issues (max 5 per review)
5. **Format** your response as JSON:

```json
{
  "observations": [
    {
      "content": "Description of the issue",
      "severity": "critical|high|medium|low|info",
      "source_ref": "file path:line or message ID",
      "metadata": {
        "category": "security|quality|logic|etc",
        "suggestion": "How to fix (optional)"
      }
    }
  ]
}
```

6. If you find **no issues**, respond with:
```json
{
  "observations": []
}
```

Focus on issues within your expertise. Do not report issues outside your focus area.
```

### Complete Configuration Example

```yaml
tools:
  - module: tool-observations
    source: git+https://github.com/microsoft/amplifier-module-tool-observations@main

behaviors:
  - module: hooks-observations
    source: git+https://github.com/microsoft/amplifier-module-hooks-observations@main
    config:
      # Hook configuration
      hooks:
        - trigger: "response:complete"
          priority: 5

      # Execution configuration
      execution:
        mode: parallel_sync
        max_concurrent: 10
        timeout_per_observer: 30
        on_timeout: skip

      # Observer definitions
      observers:
        # Fast scanner with Haiku
        - name: "Quick Scanner"
          role: "Fast initial scan for obvious issues"
          focus: "Syntax errors, missing imports, undefined variables, basic logic errors"
          model: "claude-3-5-haiku"
          timeout: 15
          watch:
            - type: files
              paths:
                - "src/**/*.py"
                - "tests/**/*.py"

        # Deep security review with Sonnet
        - name: "Security Reviewer"
          role: "Security vulnerability analysis"
          focus: |
            Look for security vulnerabilities including:
            - SQL injection risks (CWE-89)
            - XSS vulnerabilities (CWE-79)
            - Command injection (CWE-78)
            - Path traversal (CWE-22)
            - Hardcoded credentials
            - Unsafe deserialization
            - Missing authentication/authorization checks
          model: "claude-3-5-sonnet"
          timeout: 45
          watch:
            - type: files
              paths:
                - "src/**/*.py"
            - type: conversation
              include_tool_calls: true
              include_reasoning: true
          metadata:
            category: "security"

        # Logic checker watching conversation only
        - name: "Logic Checker"
          role: "Identifies logical fallacies and reasoning errors"
          focus: |
            Analyze reasoning for:
            - Circular reasoning
            - False premises
            - Unstated assumptions
            - Missing edge cases
            - Incorrect conclusions
          model: "claude-3-5-sonnet"
          timeout: 30
          watch:
            - type: conversation
              include_tool_calls: true
              include_reasoning: true

  # Optional: Display module
  - module: hooks-observations-display
    source: git+https://github.com/microsoft/amplifier-module-hooks-observations-display@main
    config:
      style: "progress_bar"  # or "table" or "compact"
      show_on_create: true
      show_on_resolve: true
```

---

## Implementation Specifications

### Module Mount Protocol

Each module must implement the amplifier mount protocol:

```python
async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Mount the module and register hooks.

    Args:
        coordinator: Orchestrator coordinator instance
        config: Module configuration from YAML

    Returns:
        Module metadata dict with name, version, description
    """
    # Parse and validate config
    module_config = parse_config(config or {})

    # Create hook handler instances
    hooks = ObservationHooks(module_config)

    # Register hooks with coordinator
    coordinator.hooks.register(
        "response:complete",
        hooks.trigger_observers,
        priority=module_config.priority
    )

    coordinator.hooks.register(
        "response:complete",
        hooks.inject_observations,
        priority=10  # After observers complete
    )

    # Return module metadata
    return {
        "name": "hooks-observations",
        "version": "1.0.0",
        "description": "Observer orchestration and coordination",
        "config": module_config.to_dict()
    }
```

### Hook Handler Signatures

```python
from typing import Literal, Any

HookAction = Literal["continue", "deny", "modify", "inject_context", "ask_user"]

@dataclass
class HookResult:
    action: HookAction
    reason: str | None = None      # For deny
    modified_data: Any | None = None  # For modify
    context: dict | None = None    # For inject_context
    question: str | None = None    # For ask_user


async def hook_handler(
    context: OrchestrationContext,
    event: HookEvent
) -> HookResult:
    """
    Standard hook handler signature.

    Args:
        context: Current orchestration context
        event: Hook event data

    Returns:
        HookResult indicating action to take
    """
    pass
```

### Observer Result Parsing

```python
def parse_observer_result(result: str, observer_name: str) -> dict:
    """
    Parse observer agent response into structured observations.

    Args:
        result: Raw text response from observer agent
        observer_name: Name of observer for metadata

    Returns:
        Dict with observations array
    """
    try:
        # Try to parse as JSON
        data = json.loads(result)

        if "observations" in data:
            # Add observer name to each observation
            for obs in data["observations"]:
                obs["observer"] = observer_name
                obs.setdefault("status", "open")
                obs.setdefault("metadata", {})

            return data

    except json.JSONDecodeError:
        # Fallback: treat as plain text observation
        return {
            "observations": [{
                "observer": observer_name,
                "content": result[:500],  # Truncate
                "severity": "info",
                "status": "open",
                "source_type": "unknown",
                "metadata": {"parse_error": True}
            }]
        }

    return {"observations": []}
```

---

## Configuration Patterns

### Pattern 1: Simple Single Observer

Minimal setup with one observer watching files:

```yaml
tools:
  - module: tool-observations
    source: git+https://github.com/microsoft/amplifier-module-tool-observations@main

behaviors:
  - module: hooks-observations
    source: git+https://github.com/microsoft/amplifier-module-hooks-observations@main
    config:
      observers:
        - name: "Code Reviewer"
          role: "Reviews code for quality and correctness"
          focus: "Syntax errors, code smells, best practice violations"
          model: "claude-3-5-sonnet"
          watch:
            - type: files
              paths: ["src/**/*.py"]
```

### Pattern 2: Multi-Observer Parallel

Multiple specialized observers running in parallel:

```yaml
behaviors:
  - module: hooks-observations
    config:
      execution:
        mode: parallel_sync
        max_concurrent: 5
        timeout_per_observer: 30

      observers:
        - name: "Security"
          role: "Security analysis"
          focus: "Vulnerabilities and unsafe patterns"
          model: "claude-3-5-sonnet"
          watch:
            - type: files
              paths: ["src/**/*.py"]

        - name: "Performance"
          role: "Performance analysis"
          focus: "Inefficient algorithms, memory leaks"
          model: "claude-3-5-sonnet"
          watch:
            - type: files
              paths: ["src/**/*.py"]

        - name: "Testing"
          role: "Test coverage analysis"
          focus: "Missing tests, edge cases"
          model: "claude-3-5-sonnet"
          watch:
            - type: files
              paths: ["tests/**/*.py", "src/**/*.py"]
```

### Pattern 3: Tiered Review (Fast → Deep)

Fast scan with Haiku, followed by deep review with Opus:

```yaml
behaviors:
  - module: hooks-observations
    config:
      observers:
        # Phase 1: Fast scan
        - name: "Quick Scan"
          role: "Fast initial check"
          focus: "Obvious errors only"
          model: "claude-3-5-haiku"
          timeout: 10
          watch:
            - type: files
              paths: ["**/*.py"]

        # Phase 2: Deep analysis
        - name: "Deep Review"
          role: "Comprehensive analysis"
          focus: "Architecture, design patterns, edge cases, security"
          model: "claude-3-5-opus"
          timeout: 60
          watch:
            - type: files
              paths: ["src/**/*.py"]
            - type: conversation
              include_tool_calls: true
```

### Pattern 4: Multi-Source Observer

Single observer watching both files and conversation:

```yaml
behaviors:
  - module: hooks-observations
    config:
      observers:
        - name: "Holistic Reviewer"
          role: "Reviews both code and reasoning"
          focus: |
            Analyze code quality AND reasoning quality:
            - Code: syntax, patterns, security
            - Reasoning: logic, assumptions, edge cases
            - Alignment: does code match stated intent?
          model: "claude-3-5-opus"
          timeout: 60
          watch:
            - type: files
              paths: ["src/**/*.py", "tests/**/*.py"]
            - type: conversation
              include_tool_calls: true
              include_reasoning: true
```

### Pattern 5: Integration with Issues

Use observations to create issues for complex workflows:

```yaml
tools:
  - module: tool-observations
  - module: tool-issue
    source: git+https://github.com/microsoft/amplifier-bundle-issues@main

behaviors:
  - module: hooks-observations
    config:
      # Standard observation configuration
      observers: [...]

      # Post-processing: Convert critical observations to issues
      post_processing:
        create_issues_for:
          severity: ["critical", "high"]
          issue_type: "bug"
          auto_assign: true
```

---

## Integration & Composition

### Bundle Composition

The observer bundle composes cleanly with other bundles:

```yaml
# Your main bundle
name: my-development-bundle

includes:
  # Base capabilities
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

  # Add observation capabilities
  - bundle: git+https://github.com/microsoft/amplifier-bundle-observations@main
    config:
      observers:
        - name: "My Custom Observer"
          # ... config ...

  # Optional: Issue tracking
  - bundle: git+https://github.com/microsoft/amplifier-bundle-issues@main

# Your bundle-specific context
context:
  - file: my-instructions.md
```

### System Instructions

Add instructions for the main agent to work with observations:

```markdown
# Observation Handling

You have observers watching your work. After each response, you may receive observations.

## When Observations Appear

1. **Review** all observations carefully
2. **Acknowledge** critical and high severity observations immediately
3. **Address** observations in your next action
4. **Resolve** observations after fixing

## Using the Observations Tool

List open observations:
```
observations list status=open
```

Acknowledge an observation:
```
observations acknowledge <id>
```

Resolve an observation:
```
observations resolve <id> note="Fixed in commit abc123"
```

## Prioritization

- **Critical**: Stop and fix immediately
- **High**: Address before proceeding
- **Medium**: Address when convenient
- **Low/Info**: Note for future reference
```

---

## Summary

The Observer Bundle provides a flexible, powerful system for automated review and feedback:

- **Three-module architecture**: Separation of concerns (state, orchestration, display)
- **Hook-driven**: Integrates cleanly with orchestrator lifecycle
- **Parallel execution**: Multiple observers run concurrently for efficiency
- **Session-based state**: Observations persist in session transcript
- **Orthogonal configuration**: Independent what/when/how dimensions
- **Flexible feedback**: Supports multiple delivery mechanisms
- **Change detection**: Avoids redundant reviews
- **Composable**: Works with other bundles (issues, workflows)

### Implementation Checklist

- [ ] Implement `tool-observations` module with JSONL persistence
- [ ] Implement `hooks-observations` module with parallel spawning
- [ ] Implement `hooks-observations-display` module for visualization
- [ ] Create observer prompting templates
- [ ] Implement change detection (file and conversation hashing)
- [ ] Implement context injection hooks
- [ ] Write configuration schema validation
- [ ] Create example configurations for common patterns
- [ ] Write integration tests
- [ ] Document bundle composition patterns
