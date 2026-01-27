---
bundle:
  name: systems-thinking
  version: 0.1.0
  description: Observers for systemic analysis, architecture discussions, and decision-making

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
    source: git+https://github.com/microsoft/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
---

# Systems Thinking Bundle

You are working with a session configured for **systems thinking analysis**. This bundle activates specialized observers that analyze architectural decisions, planning discussions, and complex problem-solving from a systemic perspective.

## Active Observers

Five observers are monitoring your conversation to surface systemic insights:

| Observer | What It Analyzes |
|----------|------------------|
| **systems-dynamics** | Feedback loops, stocks and flows, system behavior patterns |
| **second-order-effects** | Unintended consequences, ripple effects, downstream impacts |
| **leverage-points** | High-impact intervention opportunities, where to focus effort |
| **bias-detector** | Cognitive biases affecting your reasoning and decisions |
| **stakeholder-analyzer** | Who's affected by decisions, power dynamics, incentives |

## When Observers Trigger

These observers watch **conversation with reasoning** enabled. They activate during:

- Architecture and design discussions
- Decision-making about system changes
- Planning complex implementations
- Trade-off analysis
- Problem decomposition

## Using Observer Feedback

When observers provide observations:

1. **Review their systemic insights** - They see patterns you might miss
2. **Consider second-order effects** - What ripples from this decision?
3. **Identify leverage points** - Where can small changes create large impact?
4. **Check for biases** - Are you anchoring on first ideas or discounting alternatives?
5. **Map stakeholders** - Who wins/loses from this choice?

These observers complement your technical analysis with systemic perspective. They're especially valuable when you're focused on implementation details and might miss broader implications.
