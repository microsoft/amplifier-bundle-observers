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

## Observer Definition

Observers are defined as markdown files with YAML frontmatter, similar to how agents are defined in Amplifier. This allows:

- **@-mentions** for pulling in domain knowledge and context
- **Tools** for more sophisticated analysis (grep, read_file, etc.)
- **Rich instructions** in the markdown body

### Observer File Format

```markdown
---
observer:
  name: Security Auditor
  description: Identifies security vulnerabilities
  model: claude-3-5-haiku-latest
  timeout: 30

tools:
  - grep
  - read_file
---

# Security Auditor

You are a security expert reviewing code for vulnerabilities.

## Domain Knowledge

@security-bundle:context/owasp-top-10.md

## Focus Areas

- Injection attacks (SQL, command, code)
- Hardcoded secrets and credentials
- Authentication/authorization flaws

## Methodology

1. Use `grep` to find dangerous patterns
2. Use `read_file` to examine context
3. Verify findings aren't false positives
```

### Observer Properties

| Property | Description | Default |
|----------|-------------|---------|
| `name` | Display name for the observer | File stem |
| `description` | Brief description | Empty |
| `model` | LLM model to use | claude-3-5-haiku-latest |
| `timeout` | Max execution time (seconds) | 30 |
| `tools` | Tools the observer can use | None |

## Hook Configuration

Observers are referenced in the hook config with watch patterns:

```yaml
hooks:
  - module: hooks-observations
    source: git+https://github.com/microsoft/amplifier-bundle-observers@main#subdirectory=modules/hooks-observations
    config:
      observers:
        # Reference an observer from this bundle
        - observer: observers/security-auditor
          watch:
            - type: files
              paths: ["src/**/*.py"]
        
        # Reference with overrides
        - observer: observers/code-quality
          model: claude-sonnet-4-20250514  # Override default model
          timeout: 60
          watch:
            - type: files
              paths: ["**/*.py"]
            - type: conversation
              include_tool_calls: true
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

## Built-in Observers

This bundle includes two ready-to-use observers:

### Security Auditor (`observers/security-auditor`)

Focuses on security vulnerabilities:
- Injection attacks (SQL, command, code via eval/exec)
- Hardcoded credentials and secrets
- Authentication/authorization issues
- Input validation problems

Uses `grep` and `read_file` to verify findings.

### Code Quality (`observers/code-quality`)

Focuses on maintainability and patterns:
- Code smells (long functions, deep nesting)
- Error handling issues
- Resource management (unclosed files/connections)
- Missing type hints and documentation

## Creating Custom Observers

1. Create a markdown file in `observers/` directory
2. Add YAML frontmatter with `observer:` section
3. Write instructions in markdown body
4. Optionally add tools and @-mentions
5. Reference in hook config

Example custom observer:

```markdown
---
observer:
  name: API Reviewer
  description: Reviews API design and REST conventions
  model: claude-3-5-haiku-latest

tools:
  - grep
  - read_file
---

# API Reviewer

Review API endpoints for REST best practices.

@my-bundle:context/api-guidelines.md

## Focus Areas

- Proper HTTP method usage (GET/POST/PUT/DELETE)
- Consistent naming conventions
- Error response formats
- Authentication requirements
```

## Display Configuration

The optional display module shows observation status:

```yaml
hooks:
  - module: hooks-observations-display
    source: git+https://github.com/microsoft/amplifier-bundle-observers@main#subdirectory=modules/hooks-observations-display
    config:
      style: compact        # "compact" | "table" | "progress_bar"
      show_on_create: true
      show_on_resolve: true
```

Display styles:
- **compact**: Single line summary
- **progress_bar**: Visual progress indicator
- **table**: Detailed tabular view
