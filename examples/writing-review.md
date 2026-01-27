---
bundle:
  name: writing-review
  version: 0.1.0
  description: Observers for written content quality - documentation, emails, reports

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
        max_concurrent: 4
        timeout_per_observer: 45
        on_timeout: skip
      observers:
        - observer: observers/writing-quality
          watch:
            - type: conversation
              include_reasoning: true

        - observer: observers/communication-reviewer
          watch:
            - type: conversation
              include_reasoning: true

        - observer: observers/argument-analyzer
          watch:
            - type: conversation
              include_reasoning: true

        - observer: observers/simplicity-guardian
          watch:
            - type: conversation
              include_reasoning: true

tools:
  - module: tool-observations
    source: git+https://github.com/microsoft/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
---

# Writing Review Bundle

You are working with **four specialized observers** focused on written content quality. These observers analyze your communication, documentation, and written reasoning for clarity, effectiveness, and impact.

## Active Observers (4 Total)

| Observer | What It Watches | Focus Areas |
|----------|-----------------|-------------|
| **writing-quality** | Conversation with reasoning | Clarity, structure, grammar, tone consistency, readability, sentence flow |
| **communication-reviewer** | Conversation with reasoning | Message effectiveness, audience appropriateness, persuasiveness, call-to-action clarity |
| **argument-analyzer** | Conversation with reasoning | Logical structure, evidence quality, reasoning validity, claim support, counterargument consideration |
| **simplicity-guardian** | Conversation with reasoning | Unnecessary complexity, jargon usage, verbosity, unclear abstractions, over-engineering in language |

## When Observers Trigger

These observers watch **conversation with reasoning** enabled. They activate when you:

- Draft documentation, emails, or reports
- Explain complex concepts to the user
- Write instructions or guides
- Construct arguments or recommendations
- Communicate decisions or trade-offs

## What Makes This Different

Unlike code-focused observers, these analyze **how you communicate**:

- **Writing quality** ensures your text is clear and well-structured
- **Communication reviewer** checks if your message will land with the intended audience
- **Argument analyzer** validates your reasoning and evidence
- **Simplicity guardian** ensures you're not over-complicating explanations

## Using Observer Feedback

When these observers provide observations:

1. **Clarity issues** - Rewrite confusing sections before presenting to user
2. **Weak arguments** - Strengthen your reasoning with better evidence
3. **Jargon alerts** - Simplify language for better understanding
4. **Structural problems** - Reorganize for better flow

These observers help you communicate more effectively, especially when drafting content the user will share externally (team announcements, documentation, reports).
