# Observer Bundle Instructions

You have observers watching your work. After each response, observers may analyze files and conversation to provide feedback.

## When Observations Appear

Observations will be injected into your context as a system reminder when open observations exist. Each observation includes:

- **Observer**: Which specialized reviewer found the issue
- **Severity**: critical | high | medium | low | info
- **Content**: Description of the issue
- **Source**: File path:line or conversation context

## Handling Observations

### Priority Guidelines

| Severity | Action |
|----------|--------|
| **Critical** | Stop current work and fix immediately |
| **High** | Address before proceeding with other tasks |
| **Medium** | Address when convenient, before completing task |
| **Low/Info** | Note for future reference, address if time permits |

### Workflow

1. **Review** all observations when they appear
2. **Acknowledge** critical and high severity issues immediately
3. **Address** the issues in your next actions
4. **Resolve** observations after fixing

## Using the Observations Tool

### List Observations

```json
{"operation": "list", "filters": {"status": "open"}}
```

Filter options:
- `status`: "open" | "acknowledged" | "resolved"
- `severity`: ["critical", "high", "medium", "low", "info"]
- `observer`: Filter by observer name

### Acknowledge

Mark that you've seen an observation:
```json
{"operation": "acknowledge", "observation_id": "<uuid>"}
```

### Resolve

Mark an observation as fixed:
```json
{"operation": "resolve", "observation_id": "<uuid>", "resolution_note": "Fixed in commit abc123"}
```

### Clear Resolved

Remove all resolved observations:
```json
{"operation": "clear_resolved"}
```

## Observer Configuration

Observers are configured in the bundle YAML. Each observer has:

```yaml
observers:
  - name: "Observer Name"
    role: "One-line description"
    focus: |
      Detailed instructions on what to look for.
      Can be multi-line.
    model: "claude-sonnet-4-20250514"
    timeout: 30
    enabled: true
    watch:
      - type: files
        paths: ["src/**/*.py", "tests/**/*.py"]
      - type: conversation
        include_tool_calls: true
        include_reasoning: true
```

### Watch Types

**Files**:
- Monitors file changes via hash of (path, mtime, size)
- Uses glob patterns for path matching
- Reviews file content

**Conversation**:
- Monitors conversation transcript changes
- Can include/exclude tool calls and reasoning
- Reviews methodology and logic

### Execution Configuration

```yaml
execution:
  mode: parallel_sync    # All observers run in parallel
  max_concurrent: 10     # Limit parallel observers
  timeout_per_observer: 30  # Per-observer timeout (seconds)
  on_timeout: skip       # "skip" or "fail"
```

## Common Patterns

### Simple Code Review

```yaml
observers:
  - name: "Code Reviewer"
    role: "Reviews code for quality and correctness"
    focus: "Syntax errors, code smells, best practice violations"
    model: "claude-sonnet-4-20250514"
    watch:
      - type: files
        paths: ["src/**/*.py"]
```

### Security-Focused Review

```yaml
observers:
  - name: "Security Reviewer"
    role: "Security vulnerability analysis"
    focus: |
      Look for security vulnerabilities including:
      - SQL injection risks (CWE-89)
      - XSS vulnerabilities (CWE-79)
      - Command injection (CWE-78)
      - Path traversal (CWE-22)
      - Hardcoded credentials
      - Missing authentication checks
    model: "claude-sonnet-4-20250514"
    timeout: 45
    watch:
      - type: files
        paths: ["src/**/*.py"]
      - type: conversation
        include_tool_calls: true
```

### Logic Checker (Conversation Only)

```yaml
observers:
  - name: "Logic Checker"
    role: "Identifies logical errors in reasoning"
    focus: |
      Analyze reasoning for:
      - Circular reasoning
      - False premises
      - Unstated assumptions
      - Missing edge cases
    model: "claude-sonnet-4-20250514"
    watch:
      - type: conversation
        include_tool_calls: true
        include_reasoning: true
```

### Tiered Review (Fast + Deep)

```yaml
observers:
  # Fast scan with Haiku
  - name: "Quick Scanner"
    role: "Fast initial scan"
    focus: "Obvious errors only"
    model: "claude-3-5-haiku-latest"
    timeout: 15
    watch:
      - type: files
        paths: ["**/*.py"]

  # Deep review with Sonnet
  - name: "Deep Reviewer"
    role: "Comprehensive analysis"
    focus: "Architecture, patterns, edge cases, security"
    model: "claude-sonnet-4-20250514"
    timeout: 60
    watch:
      - type: files
        paths: ["src/**/*.py"]
      - type: conversation
        include_tool_calls: true
```

## Display Configuration

The optional display module shows observation status:

```yaml
hooks:
  - module: amplifier_bundle_observers.hooks_observations_display
    config:
      style: compact        # "compact" | "table" | "progress_bar"
      show_on_create: true
      show_on_resolve: true
```

Display styles:
- **compact**: Single line summary
- **progress_bar**: Visual progress indicator
- **table**: Detailed tabular view
