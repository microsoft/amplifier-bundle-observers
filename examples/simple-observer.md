---
bundle:
  name: simple-observer
  version: 0.1.0
  description: Minimal setup with a single code quality observer

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
        timeout_per_observer: 30
        on_timeout: skip
      observers:
        - observer: observers:observers/code-quality"
          watch:
            - type: files
              paths:
                - "src/**/*.py"
                - "**/*.py"

tools:
  - module: tool-observations
    source: git+https://github.com/microsoft/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
---

# Simple Observer Bundle

You are working with a minimal observer configuration focused on **code quality**.

## Active Observer

One observer is monitoring your work:

| Observer | What It Watches | Focus Areas |
|----------|-----------------|-------------|
| **code-quality** | Python files (`src/**/*.py`, `**/*.py`) | Code smells (long functions, deep nesting), error handling issues, resource leaks (unclosed files/connections), missing type hints and documentation |

## When It Triggers

The observer activates after each response (`orchestrator:complete`) when:
- You read Python files
- You write or edit Python files
- File contents change (detected by path/mtime/size hash)

## Using Observations

The code-quality observer will create observations with severity levels:
- **High** - Significant issues like resource leaks or missing error handling
- **Medium** - Code smells and maintainability concerns
- **Low** - Style suggestions and minor improvements
- **Info** - Informational notes about patterns

Address high-severity observations before completing work. Medium and low observations can be addressed when convenient.
