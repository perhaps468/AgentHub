# Root Cause Tracing

Trace bugs backward through call stack to find the original trigger.

## The Backward Tracing Technique

When an error surfaces deep in the call stack, don't fix symptoms. Trace backward to find where bad data originated.

## Step-by-Step Process

1. **Identify the bad value**
   - What specific value is wrong?
   - What type should it be?
   - What's the actual value?

2. **Find who produced it**
   - What function created/returned this value?
   - What were the inputs to that function?
   - Were those inputs correct?

3. **Trace one level up**
   - Who called that function?
   - What did they pass?
   - Were those arguments correct?

4. **Repeat until source found**
   - Continue tracing up the call chain
   - Each level asks: "Where did THIS come from?"
   - Stop when you reach code that produced correct data

5. **Fix at source**
   - The bug is where bad data was CREATED
   - NOT where bad data was USED
   - Fix the source, not the symptom

## Example

```
Error: "Cannot read property 'name' of undefined"
Location: user.render() → line 42
```

**Tracing:**

```
user.render() line 42
  └── Where does `user` come from? → passed as parameter
  └── Who calls render()? → list.renderItem() → line 87
  └── Where does item come from? → from users.map()
  └── What is users? → const users = await getUsers()
  └── What does getUsers() return? → response.data.items

Found: getUsers() returns undefined for response.data.items when API returns empty array
Fix: Handle empty array case in getUsers() or at the parsing layer
```

## Key Principle

**The error location is rarely the fix location.**

The stack trace tells you WHERE the problem was DISCOVERED, not WHERE it was CREATED.
