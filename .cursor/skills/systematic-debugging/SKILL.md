---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

## When to Use

Use for ANY technical issue:

- Test failures, bugs in production, unexpected behavior
- Performance problems, build failures, integration issues

**Use ESPECIALLY when:**

- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes without success
- You don't fully understand the issue

## The Four Phases

Complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

1. **Read Error Messages Carefully** - Don't skip past errors; they often contain the exact solution
2. **Reproduce Consistently** - Can you trigger it reliably? What are the exact steps?
3. **Check Recent Changes** - Git diff, commits, new dependencies, config changes
4. **Gather Evidence in Multi-Component Systems** - Add diagnostic instrumentation at each layer boundary
5. **Trace Data Flow** - Use backward tracing to find where bad data originated

For detailed tracing technique, see [root-cause-tracing.md](root-cause-tracing.md).

### Phase 2: Pattern Analysis

1. **Find Working Examples** - Locate similar working code in the codebase
2. **Compare Against References** - Read reference implementations COMPLETELY
3. **Identify Differences** - List every difference between working and broken
4. **Understand Dependencies** - What settings, config, environment does it need?

### Phase 3: Hypothesis and Testing

1. **Form Single Hypothesis** - State clearly: "I think X is the root cause because Y"
2. **Test Minimally** - Smallest possible change, one variable at a time
3. **Verify Before Continuing** - Did it work? If not, form NEW hypothesis
4. **When You Don't Know** - Say "I don't understand X", don't pretend

### Phase 4: Implementation

1. **Create Failing Test Case** - Must have before fixing
2. **Implement Single Fix** - Address root cause, not symptoms
3. **Verify Fix** - Test passes, no regressions
4. **If Fix Doesn't Work:**
   - If < 3 fixes: Return to Phase 1 with new information
   - If >= 3 fixes: STOP and question the architecture

**If 3+ Fixes Failed:** Architectural problem. Discuss with human partner before continuing.

## Red Flags - STOP and Follow Process

If you catch yourself thinking:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "It's probably X, let me fix that"
- Proposing solutions before tracing data flow
- "One more fix attempt" (when already tried 2+)

**ALL mean: STOP. Return to Phase 1.**

## Your Human Partner's Signals You're Doing It Wrong

- "Is that not happening?" - You assumed without verifying
- "Will it show us...?" - You should have added evidence gathering
- "Stop guessing" - You're proposing fixes without understanding
- "Ultrathink this" - Question fundamentals, not symptoms

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too |
| "Emergency, no time for process" | Systematic debugging is FASTER |
| "Just try this first, then investigate" | First fix sets the pattern |
| "I see the problem, let me fix it" | Symptoms ≠ root cause |
| "One more fix attempt" (after 2+ failures) | 3+ = architectural problem |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|----------------|------------------|
| **1. Root Cause** | Read errors, reproduce, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new theory |
| **4. Implementation** | Create test, fix, verify | Bug resolved |

## Supporting Techniques

- [root-cause-tracing.md](root-cause-tracing.md) - Trace bugs backward through call stack
- [defense-in-depth.md](defense-in-depth.md) - Add validation at multiple layers
- [condition-based-waiting.md](condition-based-waiting.md) - Replace arbitrary timeouts with polling

## Real-World Impact

- Systematic: 15-30 minutes to fix
- Random fixes: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
