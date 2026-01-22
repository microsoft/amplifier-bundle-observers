# Amplifier Observer Bundle

Automated code and conversation review through specialized AI observers.

## Overview

This bundle provides a hook-based observer system that automatically reviews code and conversations, creating actionable observations with severity levels.

**Components:**

| Module | Purpose |
|--------|---------|
| `tool-observations` | State management for observations (CRUD operations) |
| `hooks-observations` | Observer orchestration triggered by hook events |
| `hooks-observations-display` | Visualization of observation status |

## Installation

```bash
pip install amplifier-bundle-observers
```

Or for development:

```bash
pip install -e .
```

## Usage

Include in your bundle:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-observers@main
```

Or configure observers directly:

```yaml
hooks:
  - module: hooks-observations
    config:
      hooks:
        - trigger: "orchestrator:complete"
          priority: 5
      observers:
        - observer: "@observers:observers/security-auditor"
          watch:
            - type: files
              paths: ["**/*.py"]

tools:
  - module: tool-observations
```

See `bundle.md` for full documentation and `examples/` for configuration patterns.

## Observer Reference Patterns

Observer references use the same `@bundle:path` format as agents and context files in Amplifier, resolved via the `mention_resolver` capability:

```yaml
observers:
  # Cross-bundle reference (resolved via mention_resolver)
  - observer: "@observers:observers/security-auditor"
    watch:
      - type: files
        paths: ["**/*.py"]

  # From another bundle in your includes
  - observer: "@company:observers/compliance-checker"
    watch:
      - type: files
        paths: ["**/*"]

  # Relative path (resolved from base_path)
  - observer: "observers/custom-rules"
    watch:
      - type: files
        paths: ["src/**/*.py"]

  # Local file
  - observer: "./my-custom-observer.md"
    watch:
      - type: conversation
```

**Reference patterns:**
| Pattern | Resolution |
|---------|------------|
| `@bundle:path/to/observer` | Via `mention_resolver` capability (same as agents) |
| `path/to/observer` | Relative to base_path |
| `./local/observer.md` | Local file path |

The `mention_resolver` is automatically available when bundles are composed, so any bundle in your `includes` can be referenced.

## Shadow Environment Testing

For reproducible integration testing, use the shadow environment to test observers in isolation.

### Quick Test

From an Amplifier session:

```
Run a shadow test for amplifier-bundle-observers:
1. Create shadow with local source from ~/repos/amplifier-bundle-observers
2. Install the package
3. Test with the buggy code in tests/shadow/buggy_code.py
4. Verify observations are created
```

### Manual Shadow Test

1. **Create shadow environment:**
   ```bash
   # From Amplifier session
   shadow(operation="create", local_sources=[
       "~/repos/amplifier-bundle-observers:microsoft/amplifier-bundle-observers"
   ])
   ```

2. **Set up inside shadow:**
   ```bash
   shadow exec <id> "uv tool install git+https://github.com/microsoft/amplifier"
   shadow exec <id> "cd /home/amplifier && git clone https://github.com/microsoft/amplifier-bundle-observers"
   shadow exec <id> "uv tool install --force git+https://github.com/microsoft/amplifier --with file:///home/amplifier/amplifier-bundle-observers"
   shadow exec <id> "amplifier provider install -q"
   ```

3. **Create test bundle:**
   ```bash
   shadow exec <id> "cat > /home/amplifier/test-bundle.md << 'EOF'
   ---
   bundle:
     name: observer-test
     version: 0.1.0
   includes:
     - bundle: git+https://github.com/microsoft/amplifier-foundation@main
   tools:
     - module: tool-observations
       source: /home/amplifier/amplifier-bundle-observers/amplifier_bundle_observers/tool_observations
   hooks:
     - module: hooks-observations
       source: /home/amplifier/amplifier-bundle-observers/amplifier_bundle_observers/hooks_observations
       config:
         hooks:
           - trigger: \"orchestrator:complete\"
         observers:
           - name: \"Scanner\"
             role: \"Find bugs and security issues\"
             focus: \"Hardcoded credentials, SQL injection, missing error handling\"
             model: \"claude-3-5-haiku-latest\"
             timeout: 30
             watch:
               - type: files
                 paths: [\"**/*.py\"]
   ---
   Test bundle
   EOF"
   
   shadow exec <id> "amplifier bundle add /home/amplifier/test-bundle.md --name observer-test"
   ```

4. **Run test with buggy code:**
   ```bash
   shadow exec <id> "cp /home/amplifier/amplifier-bundle-observers/tests/shadow/buggy_code.py /home/amplifier/"
   shadow exec <id> "cd /home/amplifier && amplifier run -B observer-test --mode single 'Read buggy_code.py and identify issues'"
   ```

5. **Verify observations in same session:**
   The observer hook triggers on `orchestrator:complete` and creates observations within the session.

### Test Files

| File | Purpose |
|------|---------|
| `tests/shadow/buggy_code.py` | Intentionally buggy Python code with security issues |
| `tests/shadow/shadow-test-bundle.md` | Pre-configured bundle for shadow testing |
| `tests/shadow/README.md` | Detailed shadow testing instructions |

### Expected Results

The `buggy_code.py` file contains intentional issues:

| Category | Issues |
|----------|--------|
| **Critical** | SQL injection, eval() on user input, hardcoded credentials |
| **High** | Division by zero risk, unclosed file handle |
| **Medium** | Bare except, global mutable state |
| **Low** | Unused imports, wildcard import |

A successful test shows:
- Observer spawns on `orchestrator:complete` event
- Observer analyzes code via direct provider call
- Observations created with appropriate severities

## Development

```bash
# Run unit tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=amplifier_bundle_observers

# Type checking
uv run pyright amplifier_bundle_observers/
```

## Architecture

```
orchestrator:complete event
        │
        ▼
┌─────────────────────┐
│  hooks-observations │
│  - Change detection │
│  - Observer config  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Direct LLM call    │
│  via provider API   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  tool-observations  │
│  - Create/store     │
│  - Query/filter     │
└─────────────────────┘
```

## License

MIT
