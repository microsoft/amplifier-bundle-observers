---
bundle:
  name: observers
  version: 0.1.0
  description: Automated code and conversation review through specialized AI observers

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

tools:
  - module: tool-observations
    source: ./modules/tool-observations
    config: {}

hooks:
  - module: hooks-observations
    source: ./modules/hooks-observations
    config:
      hooks:
        - trigger: "orchestrator:complete"
          priority: 5
      execution:
        mode: parallel_sync
        max_concurrent: 10
        timeout_per_observer: 30
        on_timeout: skip
      observers: []  # Override in your bundle

  - module: hooks-observations-display
    source: ./modules/hooks-observations-display
    config:
      style: compact
      show_on_create: true
      show_on_resolve: true
---

# Observer Bundle

Provides automated code and conversation review through specialized AI observers.

@observers:context/instructions.md

---

## Overview

The Observer Bundle enables parallel, automated review of your work through specialized AI observers. Observers can monitor:

- **Files**: Watch for changes in source code, configs, or any files
- **Conversation**: Monitor reasoning, tool usage, and responses
- **Both**: Comprehensive review of artifacts and methodology

## Quick Start

Include this bundle and configure observers for your use case:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-observers@main
    config:
      hooks:
        - module: amplifier_bundle_observers.hooks_observations
          config:
            observers:
              - name: "Code Reviewer"
                role: "Reviews code quality"
                focus: "Syntax errors, code smells, best practices"
                model: "claude-sonnet-4-20250514"
                watch:
                  - type: files
                    paths: ["src/**/*.py"]
```

## Architecture

Three modules working together:

1. **tool-observations**: State management (CRUD for observations)
2. **hooks-observations**: Observer orchestration (parallel spawning, change detection)
3. **hooks-observations-display**: Optional visualization

## Using the Observations Tool

List open observations:
```
observations list status=open
```

Filter by severity:
```
observations list filters={"severity": ["critical", "high"]}
```

Acknowledge an observation:
```
observations acknowledge observation_id=<uuid>
```

Resolve an observation:
```
observations resolve observation_id=<uuid> resolution_note="Fixed in commit abc123"
```

## Configuration Reference

See `@observers:context/instructions.md` for detailed configuration options.
