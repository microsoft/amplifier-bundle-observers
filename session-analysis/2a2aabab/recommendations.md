# Session 2a2aabab Analysis: Amplifier Bundle Observers Development

## 1. Session Overview: What Was the User Trying to Accomplish?

You resumed work on `amplifier-bundle-observers` after a few days away, asking "where were we at?" The session evolved into:

- **Initial goal**: Test the observer bundle, specifically the tiered-review.yaml example
- **Expanded scope**: Debug module loading, fix bundle packaging, redesign observer architecture
- **Final outcome**: Complete redesign of observers as markdown files (like agents) with 50+ observers created across 6 domains

**Key Milestone**: By session end, you had a working observer system with:
- Observers defined as reusable markdown files with @-mentions and tools
- Semantic deduplication to prevent duplicate observations
- Auto-resolution of fixed issues
- 50 observers covering coding, writing, reasoning, planning, systems design, and systemic thinking

---

## 2. Problems with Amplifier's Performance

### A. **Excessive Trial-and-Error Without Planning**

**Issue**: Amplifier repeatedly tried approaches without diagnosing root causes first.

**Examples**:
- **Turns 47-130**: ~80 turns trying different bundle.md formats (relative paths → Python module paths → absolute paths → git URLs) without understanding how Amplifier's bundle system works
- **Turn 122**: Error: "No handler for URI: amplifier_bundle_observers.tool_observations" - Amplifier tried 5+ different source formats before consulting the amplifier-expert

**Impact**: Wasted ~2 hours cycling through variations instead of investigating the bundle loading system upfront.

**Pattern**: "Try something → fails → try slight variation → fails → repeat" instead of "Investigate how it's supposed to work → implement correctly"

---

### B. **Slow to Delegate to Experts**

**Issue**: Amplifier attempted complex tasks itself instead of delegating to specialized agents earlier.

**Examples**:
- **Turn 264**: Finally delegated to `amplifier-expert` to understand spawn capabilities after ~20 turns of trial-and-error with spawn mechanisms
- **Turn 381**: Finally delegated to `amplifier-expert` to understand hook event names after observers failed to trigger
- **Turn 798**: Finally delegated to `foundation:explorer` to understand bundle resolution after implementing a custom `sources` config mechanism

**Impact**: Custom implementations were often wrong and had to be redone. Consulting experts earlier would have saved significant effort.

**Better Pattern**: When encountering unfamiliar Amplifier internals (bundle loading, hook events, capabilities), delegate to amplifier-expert/foundation:explorer FIRST, not after multiple failed attempts.

---

### C. **Inadequate Root Cause Analysis**

**Issue**: Amplifier fixed symptoms without diagnosing underlying causes, leading to cascading issues.

**Examples**:
- **Turns 176-260**: Fixed hook triggering by changing "prompt:complete" → "orchestrator:complete", but didn't notice until turn 381 that the original event name was never emitted by any orchestrator
- **Turns 866-1092**: Fixed entry points, then path resolution, then coordinator.get() errors - each fix revealed the next issue because the initial diagnosis was incomplete

**Impact**: Each "fix" revealed a new problem, creating a whack-a-mole pattern requiring ~200 turns total.

**Better Pattern**: When something doesn't work, trace the execution path from end to end before attempting fixes. Use logging/debugging to understand the full failure chain.

---

### D. **Module Loading Confusion**

**Issue**: Amplifier was confused about how Amplifier loads modules, leading to incorrect implementations.

**Examples**:
- **Turns 78-125**: Tried using Python module paths (`amplifier_bundle_observers.tool_observations`) when bundle system needs `source:` fields
- **Turn 380**: Didn't understand that bundle.md modules need `source:` field; thought entry points alone were sufficient
- **Turn 728**: Implemented custom `sources` config mechanism, not realizing Amplifier already has mention_resolver capability

**Impact**: Created incorrect implementations that had to be completely redone, wasting ~100 turns.

**Root Cause**: Amplifier didn't consult foundation/core documentation or experts about module loading before implementing.

---

### E. **Shadow Environment Overuse for Simple Tests**

**Issue**: Repeatedly created shadow environments for tests that could be done more simply.

**Examples**:
- **Turns 164-181**: Created shadow for end-to-end testing when local testing would have been faster
- **Turns 256-274**: Created another shadow to test after fixes
- Shadow creation often hit rate limits or errors, adding delays

**Impact**: Shadow environment setup added 5-10 minutes per iteration. Local testing would have been faster for module-level issues.

**Better Pattern**: Use shadow environments for integration testing across repos, not for testing local code changes.

---

### F. **Incomplete Error Messages**

**Issue**: Amplifier didn't always surface full error details to help diagnose issues.

**Examples**:
- **Turn 69**: "Failed to activate tool-observations: File not found: ..." - didn't explain WHY the path was wrong (bundle composition issue)
- **Turn 122**: "No handler for URI" - didn't explain what URI formats ARE supported

**Impact**: User had to ask "what's going wrong?" multiple times. Error messages should be actionable.

---

### G. **Poor Commit Hygiene During Development**

**Issue**: Amplifier made many small commits during active debugging instead of squashing/organizing them.

**Examples**:
- 12+ commits made during the session, including fixes to fixes
- Commits like "Fix deduplication key" followed by "Fix deduplication key to exclude content" followed by "Improve deduplication to handle different observer types"

**Impact**: Messy git history that's hard to review or revert.

**Better Pattern**: During exploratory development, work on a branch or make temporary commits that get squashed before pushing.

---

## 3. User Improvement Opportunities

### A. **Provide Clearer Requirements Upfront**

**Issue**: User provided incremental requirements, causing frequent direction changes.

**Examples**:
- **Turn 18**: "How might we test this more thoroughly?" - opened exploration of testing strategies
- **Turn 182**: "Run a test with buggy code" (new requirement after testing clean code)
- **Turn 398**: "observers sometimes make duplicate observations" (new requirement after testing)
- **Turn 457**: "Since we're doing it this way now, perhaps observers should close issues automatically" (expanding scope mid-implementation)

**Impact**: Each new requirement required rework of existing implementations. The deduplication system was rewritten 3 times as requirements evolved.

**Better Pattern**: Before starting implementation, spec out the full feature set:
- "I want observers that: (1) avoid duplicates semantically, (2) auto-close fixed issues, (3) can be defined as reusable files"
- This would enable Amplifier to design the solution once instead of iterating.

---

### B. **Could Have Used More Targeted Delegation**

**Issue**: User let Amplifier struggle with implementation details instead of delegating specific sub-tasks.

**Examples**:
- The shadow environment testing could have been delegated to `shadow-smoke-test` agent directly instead of having Amplifier coordinate it
- The git commits could have been batched: "commit all the observer files in one commit" instead of multiple small commits

**Better Pattern**: 
```
"Delegate to shadow-smoke-test: Test the observer bundle end-to-end with buggy code"
"Delegate to git-ops: Commit all observer redesign changes in one organized commit"
```

---

### C. **Asking "Yes/No" Without Context**

**Issue**: User said "yes" or "sure" without specifying what they're agreeing to, forcing Amplifier to infer.

**Examples**:
- **Turn 51**: "yes" (agreeing to proceed with Option A testing)
- **Turn 502**: "Yes. Implement!" (agreeing to observer redesign spec)
- **Turn 612**: "yes" (agreeing to commit changes)

**Impact**: Sometimes Amplifier guessed wrong about what "yes" meant, requiring clarification.

**Better Pattern**: "Yes, proceed with Option A - manual testing first" or "Yes, commit the observer redesign changes"

---

### D. **Not Reviewing Intermediate Outputs**

**Issue**: User didn't catch issues in Amplifier's intermediate work that caused problems later.

**Examples**:
- The bundle.md with broken source paths was committed (turn 78) and not caught until turn 122
- The incorrect entry points in root pyproject.toml existed for hundreds of turns before being discovered (turn 957)

**Better Pattern**: When Amplifier says "I've updated bundle.md", check the changes before proceeding: "Show me the diff first" or "Let me review the changes"

---

### E. **Scope Creep Mid-Session**

**Issue**: Session started as "test the bundle" but expanded to complete redesign without explicitly acknowledging scope change.

**Phases**:
1. Turn 1: "Where were we?" (status check)
2. Turn 18: "How to test?" (testing)
3. Turn 398: "Avoid duplicate observations" (new feature)
4. Turn 489: "Observers should be markdown files like agents" (architecture redesign)
5. Turn 644: "Add non-coding observers" (massive scope expansion)

**Impact**: 42 turns and ~1000 commits of work, much of it not originally intended.

**Better Pattern**: At turn 489, could have paused: "This is a significant redesign. Should we:
- Complete testing first, then redesign separately?
- Or pivot to the redesign now and test later?"

---

### F. **Didn't Leverage Amplifier's Capabilities Fully**

**Issue**: User could have used more powerful Amplifier features.

**Examples**:
- Could have used `/save recommendations.md` to capture design decisions as you went
- Could have used todo list more actively to track the multi-phase work
- Could have used recipes for the repetitive "create observer file" tasks (50 observers created manually)

**Better Pattern**:
```
"Create a recipe for generating observer markdown files so we can batch-create them"
"Use the todo tool to track our test suite development"
```

---

## 4. Recommendations

### For Improving Amplifier's Behavior

#### High Priority

1. **Consult Experts Earlier**
   - **Rule**: When encountering unfamiliar Amplifier internals (bundle loading, hooks, capabilities), delegate to `amplifier-expert` or `foundation:explorer` within the first 2-3 failed attempts
   - **Implementation**: Add a heuristic: "If I've tried 3 variations of the same approach and all failed, consult an expert before attempt 4"

2. **Better Error Messages**
   - **Issue**: Errors like "File not found: /path" should explain WHY the path is wrong
   - **Fix**: When bundle loading fails, explain:
     - What the bundle system expected (e.g., "source: field required for modules")
     - What format is correct (e.g., "use git+https://...#subdirectory=...")
   - **Example**: Instead of "No handler for URI: X", say "No handler for URI: X. Supported formats are: git+https://..., ./relative/path, file:///absolute/path"

3. **Root Cause Analysis Before Fixing**
   - **Pattern**: When something fails, trace the full execution path:
     1. Check logs/events for the failure point
     2. Understand what was expected vs. what happened
     3. Identify ALL the conditions that must be met
     4. Fix the root cause, not symptoms
   - **Example**: When hooks didn't fire, should have:
     1. Checked if hook module loaded → NO
     2. Checked entry points → MISSING
     3. Fixed entry points
     Instead of trying to fix spawn mechanisms, triggers, etc.

4. **Commit Organization**
   - **Pattern**: During exploratory work, use a feature branch or mark commits as WIP
   - **Implementation**: After getting something working, offer to squash commits: "I made 5 commits during debugging. Should I squash these into one clean commit before pushing?"

#### Medium Priority

5. **Test Complexity Matching**
   - **Rule**: Use shadow environments for cross-repo integration tests, not for local module issues
   - **Alternative**: For local testing, use direct Python execution or local amplifier invocation

6. **Proactive Documentation**
   - **Pattern**: When making significant design decisions (like "observers as markdown files"), offer to document the decision: "Should I create a design doc explaining why we chose this approach?"

### For Improving Your Workflow

#### High Priority

1. **Spec Requirements Upfront**
   - Before starting implementation, write down the complete feature requirements:
   ```
   "I want observers that:
   1. Avoid duplicates (semantic, not string matching)
   2. Auto-close fixed issues
   3. Can be defined as reusable markdown files with @-mentions
   4. Support tools for verification
   5. Work across multiple bundles"
   ```
   - This prevents the "3 rewrites" pattern seen with deduplication

2. **Explicit Delegation for Specialized Tasks**
   - Instead of: "Test this in a shadow environment"
   - Use: "Delegate to shadow-smoke-test: [specific test instructions]"
   - This is clearer and lets the specialized agent work autonomously

3. **Review Before Proceeding**
   - When Amplifier completes a significant change, review it before moving on:
   - "Show me the bundle.md diff before we test"
   - "Let me see the pyproject.toml changes"
   - This catches issues early (like broken entry points that persisted for 800+ turns)

#### Medium Priority

4. **Acknowledge Scope Changes**
   - When work expands beyond original intent, explicitly decide:
   - "Let's pause testing and focus on the redesign instead"
   - This prevents accidental scope creep and keeps work focused

5. **Use Amplifier's Tracking Tools**
   - Todo list for multi-phase work
   - `/save` to capture design decisions
   - Recipes for repetitive tasks (creating 50 observer files)

6. **Be Specific with "Yes"**
   - Instead of: "yes"
   - Use: "Yes, proceed with Option A" or "Yes, commit the changes"
   - Reduces ambiguity and misinterpretation

---

## Summary

**Amplifier's Main Issues**:
1. Too much trial-and-error before consulting experts
2. Fixing symptoms instead of diagnosing root causes
3. Incomplete understanding of Amplifier's module/bundle system

**Your Main Opportunities**:
1. Specify complete requirements upfront
2. Review Amplifier's changes before proceeding
3. Explicitly acknowledge when scope changes

**Biggest Win**: When you finally said "Let's not reinvent this - see how foundation does it" (turn 797), Amplifier delegated to foundation:explorer and discovered the existing mention_resolver capability, avoiding a duplicate implementation.

**Pattern to Adopt**: **"Investigate before implementing"** - especially for Amplifier internals.
