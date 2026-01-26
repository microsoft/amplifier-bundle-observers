---
bundle:
  name: observers
  version: 0.1.1
  description: Automated code and conversation review through specialized AI observers

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

tools:
  - module: tool-observations
    source: git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
    config: {}

hooks:
  - module: hooks-observations
    source: git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=modules/hooks-observations
    config:
      hooks:
        - trigger: "orchestrator:complete"
          priority: 5
      execution:
        mode: parallel_sync
        max_concurrent: 10
        timeout_per_observer: 30
        on_timeout: skip
      observers:
        - observer: observers/security-auditor
          watch:
            - type: files
              paths: ["**/*.py"]
        - observer: observers/code-quality
          watch:
            - type: files
              paths: ["**/*.py"]

  - module: hooks-observations-display
    source: git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=modules/hooks-observations-display
    config:
      style: compact
      show_on_create: true
      show_on_resolve: true
---

# Observer Bundle

You are working with automated code and conversation review through specialized AI observers.

@observers:context/instructions.md

---

## Active Observers

This bundle has **two observers** monitoring your work:

| Observer | What It Watches | Focus Areas |
|----------|-----------------|-------------|
| **security-auditor** | Python files (`**/*.py`) | SQL injection, code injection (eval/exec), hardcoded credentials, authentication/authorization issues, input validation |
| **code-quality** | Python files (`**/*.py`) | Code smells (long functions, deep nesting), error handling, resource leaks, missing type hints, documentation quality |

## How Observers Work

**Trigger**: After each orchestrator cycle completes (`orchestrator:complete` event)

**Process**:
1. Detect changes in watched files or conversation
2. Spawn observers in parallel (up to 10 concurrent)
3. Each observer analyzes and reports findings
4. Observations are created with severity: critical, high, medium, low, info
5. You receive a system-reminder with observation summaries

**Change detection**: Files are tracked by (path, mtime, size) hash. Only changed files trigger reviews.

## Responding to Observations

When observers create observations:

1. **Critical/High severity** - Address immediately, these are blocking issues
2. **Medium severity** - Address before completing the task
3. **Low/Info severity** - Note for future reference

Use the `observations` tool to:
- List: `observations list filters={"status": "open"}`
- Acknowledge: `observations acknowledge observation_id=<uuid>`
- Resolve: `observations resolve observation_id=<uuid> resolution_note="Fixed by..."`

## Observer Capabilities

Both observers have access to:
- **grep**: Search for patterns across files
- **read_file**: Read full file contents for context

They use these tools to verify findings and reduce false positives before creating observations.
