---
bundle:
  name: tiered-review
  version: 0.1.0
  description: Two-tier review - fast Haiku scans + deep Sonnet analysis

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

hooks:
  - module: hooks-observations
    source: git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=modules/hooks-observations
    config:
      hooks:
        - trigger: "orchestrator:complete"
          priority: 5
      execution:
        mode: parallel_sync
        max_concurrent: 5
        timeout_per_observer: 60
        on_timeout: skip
      observers:
        # Tier 1: Fast scans with Haiku (default model)
        - observer: observers/python-best-practices
          watch:
            - type: files
              paths: ["**/*.py"]

        - observer: observers/error-handling
          watch:
            - type: files
              paths: ["**/*.py"]

        - observer: observers/secrets-scanner
          watch:
            - type: files
              paths: ["**/*"]

        # Tier 2: Deep analysis with Sonnet (override model)
        - observer: observers/security-auditor
          model: claude-sonnet-4-20250514
          watch:
            - type: files
              paths: ["src/**/*.py"]
            - type: conversation
              include_tool_calls: true

        - observer: observers/architecture-reviewer
          model: claude-sonnet-4-20250514
          watch:
            - type: conversation
              include_tool_calls: true
              include_reasoning: true

tools:
  - module: tool-observations
    source: git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
---

# Tiered Review Bundle

You are working with a **cost-optimized two-tier review strategy**: fast Haiku observers catch obvious issues while powerful Sonnet observers handle complex analysis.

## Active Observers (5 Total)

### Tier 1: Fast Scans (Haiku - Default Model)

| Observer | What It Watches | Focus Areas |
|----------|-----------------|-------------|
| **python-best-practices** | Python files | PEP 8 compliance, Python idioms, common mistakes, code organization |
| **error-handling** | Python files | Exception handling patterns, edge cases, error propagation, missing try/except |
| **secrets-scanner** | All files | Hardcoded credentials, API keys, passwords, tokens |

### Tier 2: Deep Analysis (Sonnet-4 - Explicit Override)

| Observer | What It Watches | Focus Areas |
|----------|-----------------|-------------|
| **security-auditor** | Python files + conversation | Security vulnerabilities, attack vectors, authentication/authorization, injection attacks |
| **architecture-reviewer** | Conversation with reasoning | Design patterns, system structure, architectural decisions, complexity analysis |

## Cost-Performance Strategy

**Why this tiering works:**

1. **Fast observers (Tier 1)** use the default Haiku model:
   - Catch ~80% of issues (style, obvious mistakes, secrets)
   - Cost: Very low per review
   - Speed: Fast turnaround (< 5 seconds typically)

2. **Deep observers (Tier 2)** use Sonnet-4 explicitly:
   - Handle complex analysis requiring deeper reasoning
   - Cost: ~10x more expensive, but only for critical domains
   - Speed: Slower but thorough (10-20 seconds)

**Result**: Better cost/quality tradeoff than using Sonnet for everything, while maintaining thorough coverage where it matters (security and architecture).

## Execution Parameters

- **Max concurrent**: 5 observers
- **Timeout**: 60 seconds per observer (higher for Sonnet observers)
- **Model override**: Tier 2 observers explicitly specify `model: claude-sonnet-4-20250514`

Use this bundle when you want comprehensive review but need to **optimize for cost** without sacrificing security or architectural quality.
