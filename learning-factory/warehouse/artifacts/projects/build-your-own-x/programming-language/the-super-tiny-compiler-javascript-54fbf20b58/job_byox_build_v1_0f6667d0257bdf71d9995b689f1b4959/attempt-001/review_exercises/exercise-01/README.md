# Exercise 01: inconsistent work budgets

This patch adds `maxSteps` to both execution engines:

```js
// tree interpreter, inside visitWhile
while (truthy(evaluate(node.condition, environment))) {
  if (--steps < 0) throw new PebbleStepLimitError("Step limit exceeded");
  evaluateBlock(node.body, environment);
}

// VM, at the top of its dispatch loop
if (--steps < 0) throw new PebbleStepLimitError("Step limit exceeded");
const instruction = code[ip++];
dispatch(instruction);
```

Review questions:

1. Do the two implementations assign the same meaning to a “step”?
2. Which finite programs could be rejected by one backend but not the other?
3. Which expensive tree-interpreter work is not charged at all?
4. What API contract and tests would make resource exhaustion predictable?
5. Is an in-language counter enough to replace an outer process deadline?

Classify correctness and availability concerns separately.
