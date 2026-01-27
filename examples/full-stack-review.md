---
bundle:
  name: full-stack-review
  version: 0.1.0
  description: Comprehensive review for full-stack web development

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
        max_concurrent: 8
        timeout_per_observer: 45
        on_timeout: skip
      observers:
        # Backend (Python)
        - observer: observers/python-best-practices
          watch:
            - type: files
              paths: ["**/*.py"]

        - observer: observers/async-patterns
          watch:
            - type: files
              paths: ["**/*.py"]

        # Frontend (TypeScript/React)
        - observer: observers/typescript-reviewer
          watch:
            - type: files
              paths: ["**/*.ts", "**/*.tsx"]

        - observer: observers/react-reviewer
          watch:
            - type: files
              paths: ["**/*.tsx", "**/*.jsx"]

        # Database
        - observer: observers/sql-reviewer
          watch:
            - type: files
              paths: ["**/*.py", "**/*.sql"]

        # API Design
        - observer: observers/api-design
          watch:
            - type: files
              paths: ["**/routes/**", "**/api/**", "**/*.py"]

        # Security (all code)
        - observer: observers/security-auditor
          model: claude-sonnet-4-20250514
          watch:
            - type: files
              paths: ["**/*"]

        # Accessibility (frontend)
        - observer: observers/accessibility-checker
          watch:
            - type: files
              paths: ["**/*.tsx", "**/*.jsx", "**/*.html"]

        # Config and DevOps
        - observer: observers/config-reviewer
          watch:
            - type: files
              paths:
                - "**/*.yaml"
                - "**/*.yml"
                - "**/*.json"
                - "**/*.toml"
                - "**/Dockerfile"
                - "**/.env*"

tools:
  - module: tool-observations
    source: git+https://github.com/microsoft/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
---

# Full-Stack Review Bundle

You are working with **comprehensive full-stack review** across nine specialized observers covering backend, frontend, database, API, security, accessibility, and infrastructure.

## Active Observers (9 Total)

| Layer | Observer | What It Watches | Focus Areas |
|-------|----------|-----------------|-------------|
| **Backend** | python-best-practices | Python files | PEP 8, Python idioms, design patterns, code organization |
| | async-patterns | Python files | Async/await correctness, event loop usage, concurrent execution patterns |
| **Frontend** | typescript-reviewer | TypeScript files (`.ts`, `.tsx`) | Type safety, TypeScript best practices, type definitions |
| | react-reviewer | React files (`.tsx`, `.jsx`) | Component patterns, hooks usage, state management, React best practices |
| **Database** | sql-reviewer | Python + SQL files | Query optimization, N+1 queries, database patterns, SQL injection prevention |
| **API** | api-design | Route/API files | REST conventions, HTTP method usage, endpoint design, error responses |
| **Security** | security-auditor | All files (uses Sonnet-4 model) | Vulnerabilities, authentication/authorization, input validation, security best practices |
| **Accessibility** | accessibility-checker | Frontend files (`.tsx`, `.jsx`, `.html`) | WCAG compliance, semantic HTML, ARIA usage, keyboard navigation |
| **DevOps** | config-reviewer | Config files (YAML, JSON, TOML, Dockerfile, .env) | Configuration best practices, security in configs, environment management |

## Execution Parameters

- **Max concurrent**: 8 observers run in parallel
- **Timeout**: 45 seconds per observer
- **Security observer uses Sonnet-4**: More expensive model for critical security analysis

## When to Use This Bundle

This configuration is ideal when:
- Working on full-stack applications (Python backend + React/TypeScript frontend)
- You need comprehensive review across all layers of the stack
- You want specialized expertise for each technology (not generic code review)
- The project has database, API, and infrastructure concerns

## Handling Observations from Multiple Observers

With 9 observers active, you may receive observations from multiple domains simultaneously:

1. **Prioritize by severity** first (critical → high → medium → low)
2. **Then by layer** - Fix security issues before style issues
3. **Use observer expertise** - Each observer is a specialist, trust their domain knowledge
4. **Address cross-cutting concerns** - If multiple observers flag the same code, it's a design smell
