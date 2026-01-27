# Amplifier Observer Bundle

Get automatic file and conversation review as you work, with specialized AI observers that watch for issues and provide actionable feedback.

## What This Does For You

While you're working with Amplifier, observers run automatically in the background, reviewing your files and conversations. They catch issues early, suggest improvements, and help you maintain quality without interrupting your flow.

**Think of observers as expert colleagues looking over your shoulder** - a security expert watching for vulnerabilities, a performance specialist checking for bottlenecks, a systems thinker surfacing unintended consequences.

## How It Works

1. **You work normally** - Write code, have conversations, make decisions
2. **Observers activate automatically** - After each response, observers check for changes
3. **You get targeted feedback** - Observations appear with severity levels (critical, high, medium, low, info)
4. **You address what matters** - Focus on high-severity issues, handle others when convenient

## Quick Start

**Important**: This bundle must be used as a **top-level bundle** (loaded directly with `amplifier run`). It cannot be included in other bundles because it provides an orchestrator.

### Use a Pre-Built Example

We've created 6 ready-to-use bundles for common scenarios:

```bash
# Systems thinking for architecture and decision-making
amplifier bundle add \
  "git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=examples/systems-thinking.md" \
  --name systems-thinking
amplifier run -B systems-thinking

# Code quality for Python development
amplifier bundle add \
  "git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=examples/simple-observer.md" \
  --name code-review
amplifier run -B code-review

# Full-stack web development review
amplifier bundle add \
  "git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=examples/full-stack-review.md" \
  --name full-stack
amplifier run -B full-stack
```

Or run directly without registering:

```bash
amplifier run --bundle "git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=examples/systems-thinking.md"
```

## Available Examples

| Bundle | Best For |
|--------|----------|
| **simple-observer** | Minimal setup - just code quality for Python |
| **multi-observer** | Comprehensive code review (security, performance, tests) |
| **systems-thinking** | Architecture discussions and complex decisions |
| **writing-review** | Documentation, emails, and written content |
| **tiered-review** | Fast scans + deep analysis (Haiku + Sonnet) |
| **full-stack-review** | Complete web development review (Python, TypeScript, React, SQL, API design) |

Each example is ready to use as-is or copy and customize for your needs.

## 50+ Pre-Built Observers

The `observers/` directory contains specialized observers you can reference in your own bundles:

### Code & Technical
- `code-quality` - Code smells, long functions, complexity
- `python-best-practices` - Python-specific patterns
- `typescript-reviewer` - TypeScript and type safety
- `react-reviewer` - React patterns and hooks
- `sql-reviewer` - SQL patterns and query optimization
- `async-patterns` - Async/await usage and concurrency
- `error-handling` - Exception handling patterns
- `test-quality` - Test coverage and assertions

### Security & Reliability
- `security-auditor` - Vulnerabilities and unsafe patterns
- `security-design-reviewer` - Security architecture
- `secrets-scanner` - Hardcoded credentials and API keys
- `performance-reviewer` - Bottlenecks and optimization
- `reliability-reviewer` - Fault tolerance and resilience
- `dependency-reviewer` - Dependency health and risks

### Architecture & Design
- `architecture-reviewer` - System structure and modularity
- `api-design` - API contracts and consistency
- `data-design-reviewer` - Data models and schemas
- `boundary-analyzer` - Module boundaries and coupling
- `simplicity-guardian` - Unnecessary complexity
- `scalability-reviewer` - Growth and scaling concerns

### Systems Thinking
- `systems-dynamics` - Feedback loops and system behavior
- `second-order-effects` - Unintended consequences
- `leverage-points` - High-impact interventions
- `bias-detector` - Cognitive biases in reasoning
- `stakeholder-analyzer` - People and incentives
- `mental-models` - Assumptions and frameworks
- `root-cause-analyzer` - Problem diagnosis

### Documentation & Communication
- `writing-quality` - Clarity, tone, structure
- `documentation-checker` - Docs completeness and accuracy
- `communication-reviewer` - Team communication patterns
- `accessibility-checker` - Inclusive design and content
- `meeting-notes` - Meeting effectiveness and action items

### Process & Planning
- `task-completion` - Task tracking and follow-through
- `planning-reviewer` - Planning quality and realism
- `decision-reviewer` - Decision-making process
- `tradeoff-analyzer` - Trade-off analysis
- `requirements-analyzer` - Requirements clarity
- `research-reviewer` - Research methodology

### Operations & Deployment
- `operational-reviewer` - Deployment and monitoring
- `migration-reviewer` - Migration safety and planning
- `integration-reviewer` - Integration patterns
- `config-reviewer` - Configuration management
- `git-hygiene` - Git workflow and commit quality
- `cost-reviewer` - Cost implications and optimization

**See each observer file in `observers/` for specific focus areas and severity guidelines.**

## Building Your Own Bundle

Copy an example and customize:

```bash
# Copy an example to start
cp examples/simple-observer.md my-custom-bundle.md

# Edit the observers section to use the ones you need
```

Example configuration:

```yaml
hooks:
  - module: hooks-observations
    source: git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=modules/hooks-observations
    config:
      hooks:
        - trigger: "orchestrator:complete"
          priority: 5
      observers:
        # Reference observers from this bundle
        - observer: "@observers:observers/security-auditor"
          watch:
            - type: files
              paths: ["**/*.py"]
        
        - observer: "@observers:observers/performance-reviewer"
          watch:
            - type: files
              paths: ["src/**/*.py"]

tools:
  - module: tool-observations
    source: git+https://github.com/payneio/amplifier-bundle-observers@main#subdirectory=modules/tool-observations
```

## How Observations Work

Observers create observations with:
- **Severity**: critical, high, medium, low, info
- **Category**: What type of issue (security, performance, etc.)
- **Message**: What's wrong and why it matters
- **Location**: File and line number (for code observations)
- **Suggestion**: How to fix it

You can query observations during your session:

```
"Show me high-severity observations"
"What security issues did the observer find?"
"List all observations for auth.py"
```

## Observer Types

### File Observers
Watch for changes to specific files and review them:

```yaml
watch:
  - type: files
    paths: ["**/*.py", "src/**/*.ts"]
```

### Conversation Observers
Analyze discussions, decisions, and reasoning:

```yaml
watch:
  - type: conversation
    include_reasoning: true  # See the thinking process
```

## Architecture

Observers use a hook-based architecture:

1. **hooks-observations** - Orchestrates observers when events trigger
2. **tool-observations** - Manages observation storage and querying
3. **Observer definitions** - Specialized review prompts in `observers/`

When `orchestrator:complete` fires, the hook:
- Detects what changed (files or conversation)
- Activates matching observers
- Each observer calls the LLM directly to analyze
- Observations are stored for later reference

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
