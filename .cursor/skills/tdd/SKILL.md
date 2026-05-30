---
name: tdd
description: Enforce Test-Driven Development discipline: RED (write failing test first), GREEN (minimal implementation), REFACTOR (clean up). Use when writing tests, fixing bugs, adding features, or refactoring — or when the user says TDD, test-driven, 红绿重构, or 先行测试.
---

# TDD — Test-Driven Development

Core rule: **no production code until a test fails first.**

## RED — Write the Failing Test

Write a minimal test that describes what should happen.

```typescript
test('failed operation retries 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };
  const result = await retryOperation(operation);
  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```

Requirements:
- One behavior per test
- Descriptive test name
- Test real behavior, not mocks

## Verify RED

Run the test and confirm it **fails**, not errors. Verify the failure reason is correct — it must be because the feature is missing, not due to typos.

**If the test passes on first run, you wrote a test for existing behavior. Rewrite it.**

## GREEN — Minimal Implementation

Write only the code needed to make the test pass. Nothing more.

```typescript
async function retryOperation(fn) {
  for (let i = 0; i < 3; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === 2) throw e;
    }
  }
}
```

No extra features, no premature optimization, no refactoring other code.

## Verify GREEN

Run tests again. All must pass — current test and all others. No warnings.

**If it fails: fix the code, not the test.**

## REFACTOR — Clean Up

Only after GREEN. Remove duplication, improve naming, extract shared logic. Keep tests green throughout.

---

## Task Discipline (铁律)

Before each TDD cycle, confirm:
1. Which task this belongs to
2. The task's acceptance criteria
3. Which behavior within the task this test validates

Rules:
- One behavior per task — don't span multiple tasks in one cycle
- Test name, implementation, and result must trace back to the current task
- If you discover a new behavior not in the current task, **stop and update the task first**
- Do not expand scope with "I'll optimize while I'm here"

---

## When to Use

Always: new features, bug fixes, refactoring, behavior changes.

Ask the team first: one-off prototypes, generated code, config files.

---

## Bug Fix Cycle

```
RED:    test('rejects empty email', () => {
          const result = submitForm({ email: '' });
          expect(result.error).toBe('Email required');
        });

Verify: FAIL — expected 'Email required', got undefined

GREEN:  function submitForm(data) {
          if (!data.email?.trim()) {
            return { error: 'Email required' };
          }
        }

Verify: PASS

Refactor: if multiple fields have similar rules, extract validation.
```

---

## Red Flags — Stop Immediately

- Test passes on first run
- Writing production code before writing the test
- "I'll add tests later"
- "This is simple enough to skip"
- "I already tested it manually"
- Keeping existing code to "use as reference"

If any of these happen: delete the code and restart from the failing test.

---

## Common Excuses vs. Reality

| Excuse | Reality |
|--------|---------|
| "It's too simple" | Simple code still breaks |
| "Tests later" | Tests that pass from the start prove nothing |
| "Manually tested" | Manual tests are not repeatable |
| "TDD is slow" | Debugging is slower |
| "Delete waste" | Keeping untrusted code is the real waste |

---

## Verification Checklist

Before calling done:

- [ ] Each new behavior has a test
- [ ] Each test failed at least once before implementation
- [ ] Failure reason was correct
- [ ] Implementation is minimal (just enough to pass)
- [ ] All tests pass
- [ ] No warnings or errors
- [ ] Edge cases are covered

If any checkbox is unchecked, TDD was skipped.

---

## Final Rule

```
Production code → requires a failing test first
Otherwise → not TDD
```
