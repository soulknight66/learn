# Diagnosis and repair

The counter increments before comparison, so exhaustion occurs only when `used` becomes greater than
the permitted count. The candidate uses `>=`, rejecting the third call for a limit of three. Change
the condition to:

```python
if self.used > self.limit:
    raise BudgetExceeded()
```

Boundary tests should assert that limit zero rejects the first call and limit one accepts one call then
rejects the second. This is the convention used by both reference execution engines.
