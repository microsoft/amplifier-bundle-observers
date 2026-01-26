---
bundle:
  name: systems-thinking
  version: 0.1.0
  description: Observers for systemic analysis, architecture discussions, and decision-making

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/payneio/amplifier-bundle-observers@main

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
        timeout_per_observer: 45
        on_timeout: skip
      observers:
        - observer: observers/systems-dynamics
          watch:
            - type: conversation
              include_reasoning: true

        - observer: observers/second-order-effects
          watch:
            - type: conversation
              include_reasoning: true

        - observer: observers/leverage-points
          watch:
            - type: conversation
              include_reasoning: true

        - observer: observers/bias-detector
          watch:
            - type: conversation
              include_reasoning: true

        - observer: observers/stakeholder-analyzer
          watch:
            - type: conversation
              include_reasoning: true

tools:
  - module: tool-observations
    source: git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
---

# Systems Thinking Bundle

Observers focused on systemic analysis, not just code. Great for architecture discussions, planning sessions, and decision-making.

## Usage

```bash
amplifier bundle add examples/systems-thinking.md --name systems-thinking
amplifier run -B systems-thinking
```

## Observers

| Observer | Focus |
|----------|-------|
| systems-dynamics | Feedback loops, stocks and flows, system behavior |
| second-order-effects | Unintended consequences, ripple effects |
| leverage-points | High-impact intervention opportunities |
| bias-detector | Cognitive biases affecting decisions |
| stakeholder-analyzer | Who's affected and how |

## Try It

Start a conversation about a complex decision:

> "I'm thinking about migrating our monolith to microservices. What should I consider?"

The observers will surface systemic considerations you might miss.
