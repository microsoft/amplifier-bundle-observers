# Session Analysis: Why Amplifier Kept Claiming "Complete" When It Wasn't

## Executive Summary

After analyzing the 157MB session (~5900 events, 49 child sessions), I identified **5 major failure patterns** that caused the AI to claim tasks were complete when they weren't working. The issues span **AI reasoning failures, system/documentation gaps, and user prompting patterns**.

---

## The Failure Patterns

### Pattern 1: Unit Tests ≠ Integration (Most Critical)

**What happened:**
```
AI: "All 50 tests pass! Let me update our progress..."
AI: "Excellent! All 50 unit tests passed! Here's where we're at: ✅ Completed"
```

**Reality:** The bundle immediately failed when the user tried to use it:
```
Failed to activate tool-observations: File not found: /home/payne/.amplifier/cache/...
Failed to activate hooks-observations: File not found...
```

**Root cause:** The AI treated passing unit tests as proof the system worked. But unit tests with mocks don't catch:
- Bundle path resolution issues
- Entry point registration failures
- Coordinator API compatibility
- Session spawning mechanics

**Who's responsible:** Primarily **AI reasoning failure** - the AI should have tested the actual user workflow (running the bundle in Amplifier) before claiming completion.

---

### Pattern 2: Path Resolution Assumptions

**What happened:**
```yaml
# AI wrote this in bundle.md:
tools:
  - module: tool-observations
    source: ./amplifier_bundle_observers/tool_observations
```

**Reality:** Relative paths resolved from the **cache directory** when using `amplifier bundle add git+...`, not from the repo root.

**The fix that finally worked:**
```yaml
source: /data/repos/msft/amplifier-bundle-observers/amplifier_bundle_observers/tool_observations
```

**Root cause:** The AI assumed relative paths would "just work" without understanding how Amplifier resolves paths in different contexts (local dev vs published bundle vs cache).

**Who's responsible:** 
- **System gap** - Amplifier's path resolution behavior wasn't well documented
- **AI reasoning failure** - Should have tested the published bundle flow explicitly

---

### Pattern 3: Module Discovery ≠ Module Mounting

**What happened:**
```
AI: Runs `amplifier module list`
AI: "The modules ARE installed and showing up in the module list"
AI: (assumes everything is working)
```

**Reality:** Modules appeared in the list but:
- Tool wasn't appearing in the agent's tool list
- Hook was running but showing "No observers configured"

**Root cause:** The AI conflated "discoverable" with "correctly mounted and usable." Multiple debugging iterations followed where the AI checked various things but didn't test the actual end-to-end flow.

**Who's responsible:** **AI reasoning failure** - drew premature conclusions from partial evidence.

---

### Pattern 4: Recommendations Without Verification

**What happened:**
```
User: "Which option should I choose?"
AI: "My recommendation: Option A first, then Option C."
AI: (provides detailed reasoning for why Option A is best)
AI: "Want me to proceed with Option A?"
User: "yes"
```

**Reality:** Option A immediately failed because the bundle path issues hadn't been resolved.

**Root cause:** The AI made confident recommendations based on theoretical reasoning without having actually tested any of the options first.

**Who's responsible:** 
- **AI reasoning failure** - Should have said "let me quickly verify Option A works before recommending it"
- **User prompting** - Asking "which should I choose?" invited recommendation without testing

---

### Pattern 5: Design Iteration Without Re-testing

**What happened:** The session shows multiple design changes:
1. Added deduplication logic
2. Changed to bundle-based observers
3. Added auto-close for stale issues
4. Added multi-bundle source support

Each iteration, the AI implemented changes and moved on without comprehensive re-testing.

**Root cause:** As the session got longer and more complex, the AI (and user) relied on incremental "it should work" assumptions rather than running the full test suite after each change.

**Who's responsible:** Both **AI** and **user prompting** - the user gave broad instructions like "Yes. Implement!" without specific acceptance criteria, and the AI didn't insist on verification.

---

## Root Cause Analysis

### AI Reasoning Failures (Primary)

| Issue | Description |
|-------|-------------|
| **Green tests = done** | Treated passing unit tests as proof of working system |
| **Partial evidence → full conclusions** | Saw modules in list, assumed they were working |
| **Confident recommendations without testing** | Recommended Option A without verifying it worked |
| **Assumption about path resolution** | Didn't test how paths resolve in different contexts |
| **No end-to-end testing** | Never ran `amplifier bundle add git+...` to test the actual user flow |

### System/Documentation Gaps (Contributing)

| Issue | Description |
|-------|-------------|
| **Path resolution unclear** | How Amplifier resolves relative paths in bundles isn't well documented |
| **Entry point vs source confusion** | Multiple ways to reference modules (entry points, source paths) without clear guidance |
| **Local dev vs published gap** | Different behavior between local development and published bundles |

### User Prompting Patterns (Contributing)

| Pattern | Impact |
|---------|--------|
| Accepted "50 tests pass" as completion | Didn't push for integration testing |
| "Which option should I choose?" | Invited recommendation without verification |
| "Yes. Implement!" | Broad instruction without acceptance criteria |
| Didn't specify "test the published bundle flow" | AI tested local flow only |

---

## Recommendations

### For Amplifier (System Improvements)

1. **Add a `bundle validate` command** that tests:
   - Path resolution in all contexts (local, cache, published)
   - Module mounting actually works
   - Entry points are correctly registered

2. **Better error messages** when paths fail to resolve - show the attempted resolution path

3. **Documentation** on bundle path resolution behavior (local vs published vs cache)

### For AI Prompting Strategy

1. **Define acceptance criteria upfront:**
   ```
   "Create the bundle. It's done when:
   1. `amplifier bundle add git+...` works
   2. The observations tool appears in agent's tool list
   3. Observers actually trigger on file changes"
   ```

2. **Request explicit verification steps:**
   ```
   "After implementing, test it by:
   1. Push to GitHub
   2. Run `amplifier bundle add git+...`
   3. Start a session and verify the tool loads"
   ```

3. **Don't accept "tests pass" as completion** - ask "did you test the actual user workflow?"

### For AI Behavior Improvements

1. **Integration test BEFORE claiming completion** - always test the user's actual workflow, not just unit tests

2. **Don't recommend options without testing** - say "let me verify this works first"

3. **Re-test after design changes** - don't assume incremental changes preserve functionality

4. **Be explicit about what was vs wasn't tested:**
   ```
   "✅ Unit tests pass (models, parsing, state management)
   ⚠️ NOT TESTED: Bundle installation from GitHub
   ⚠️ NOT TESTED: Actual session with observers"
   ```

---

## Summary

| Category | % Responsibility | Key Fix |
|----------|-----------------|---------|
| **AI Reasoning** | ~60% | Test user workflow before claiming completion |
| **System Gaps** | ~25% | Better path resolution docs and validation |
| **User Prompting** | ~15% | Define acceptance criteria, request verification |

The core issue is that **"tests pass" became synonymous with "done"** when the tests only covered isolated components, not the integrated system the user actually interacts with.

---

## Session Metadata

- **Session ID:** `2a2aabab-87e3-4975-9fda-09afc94e4ba4`
- **Location:** `~/.amplifier/projects/-data-repos-msft-amplifier-bundle-observers/sessions/`
- **Size:** 157MB events.jsonl, ~5900 events
- **Child sessions:** 49 (shadow-operator, git-ops, amplifier-expert, shadow-smoke-test, etc.)
- **Analysis date:** 2026-01-22
