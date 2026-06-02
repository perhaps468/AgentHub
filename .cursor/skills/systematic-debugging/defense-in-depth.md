# Defense in Depth

Add validation at multiple layers after finding root cause.

## Concept

Single-point validation fails. True defense requires validation at entry points, boundaries, and before critical operations.

## Three Layers

### Layer 1: Entry Point Validation
Validate at system boundaries (API endpoints, user input, file reads).

```
function createUser(input) {
  validateEmail(input.email)    // Entry validation
  validatePassword(input.password)
  // ... proceed
}
```

### Layer 2: Boundary Validation
Validate when crossing component boundaries.

```
// Service layer
async function processOrder(orderId) {
  const order = await db.orders.find(orderId)
  if (!order) throw new NotFoundError(orderId)  // Boundary validation
  
  const user = await userService.getUser(order.userId)
  if (!user.isActive) throw new InactiveUserError()  // Another boundary
  
  return processOrderInternal(order, user)
}
```

### Layer 3: Pre-Operation Validation
Validate immediately before critical operations.

```
async function transferFunds(from, to, amount) {
  // ... validations above ...
  
  // Pre-operation check
  const balance = await accountRepo.getBalance(from)
  if (balance < amount) {
    throw new InsufficientFundsError()
  }
  
  // NOW safe to proceed
  await accountRepo.debit(from, amount)
  await accountRepo.credit(to, amount)
}
```

## When to Apply

After root cause investigation reveals:

- Data corruption at boundaries
- Missing null checks
- Assumption that external data is valid
- Silent failures that cascade

## Anti-Pattern

Throwing exceptions without validation at multiple layers:

```python
# BAD: No defense
def process_order(order_id):
    order = get_order(order_id)  # What if order_id is invalid?
    order.status = "processing"
    order.save()  # What if save fails silently?
    send_confirmation(order.user_email)  # What if email is None?
```

## Golden Rule

**Never trust data from another layer.**

Every component should validate inputs from external sources before using them.
