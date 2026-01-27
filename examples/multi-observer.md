---
bundle:
  name: multi-observer
  version: 0.1.0
  description: Multiple specialized observers for comprehensive code review

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

hooks:
  - module: hooks-observations
    source: git+https://github.com/microsoft/amplifier-bundle-observers@main#subdirectory=modules/hooks-observations
    config:
      hooks:
        - trigger: "orchestrator:complete"
          priority: 5
      execution:
        mode: parallel_sync
        max_concurrent: 5
        timeout_per_observer: 45
        on_timeout: skip
      observers:
        - observer: observers/security-auditor
          watch:
            - type: files
              paths: ["src/**/*.py"]
            - type: conversation
              include_tool_calls: true

        - observer: observers/secrets-scanner
          watch:
            - type: files
              paths: ["**/*.py", "**/*.yaml", "**/*.json", "**/*.env*"]

        - observer: observers/performance-reviewer
          watch:
            - type: files
              paths: ["src/**/*.py"]

        - observer: observers/test-quality
          watch:
            - type: files
              paths: ["src/**/*.py", "tests/**/*.py"]

        - observer: observers/logic-checker
          watch:
            - type: conversation
              include_tool_calls: true
              include_reasoning: true

tools:
  - module: tool-observations
    source: git+https://github.com/microsoft/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
---

# Multi-Observer Bundle

You are working with **five specialized observers** running in parallel for comprehensive code review. Each observer focuses on a specific quality dimension.

## Active Observers

| Observer | What It Watches | Focus Areas |
|----------|-----------------|-------------|
| **security-auditor** | Python files + conversation | Security vulnerabilities, injection attacks, authentication/authorization issues |
| **secrets-scanner** | All files (Python, YAML, JSON, env) | Hardcoded credentials, API keys, exposed secrets |
| **performance-reviewer** | Python files (`src/**/*.py`) | Performance issues, inefficiencies, algorithmic problems, unnecessary computation |
| **test-quality** | Source and test files | Test coverage, test quality, missing edge cases, brittle tests |
| **logic-checker** | Conversation with reasoning | Logical errors, reasoning flaws, invalid assumptions, incomplete analysis |

## Observer Strategy

This configuration uses **breadth over depth** - multiple specialized observers catch different issue types in parallel:

- **Security & Secrets** work together: one finds code vulnerabilities, one finds exposed credentials
- **Performance & Test Quality** ensure production readiness
- **Logic Checker** monitors your reasoning process in real-time

## Execution Parameters

- **Max concurrent**: 5 observers run in parallel
- **Timeout**: 45 seconds per observer
- **On timeout**: Skip (continues even if an observer times out)

Use this bundle when you want **comprehensive automated review** across multiple quality dimensions, not just code style.
