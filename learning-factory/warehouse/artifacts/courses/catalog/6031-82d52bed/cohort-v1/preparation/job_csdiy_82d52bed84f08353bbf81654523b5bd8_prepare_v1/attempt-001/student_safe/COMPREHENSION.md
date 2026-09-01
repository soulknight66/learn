# Comprehension Prompts

Answer these questions in `COMPREHENSION_RESPONSES.md` after completing the implementation. This file intentionally contains questions only.

1. For this ADT, give one concrete way that each course goal—safe from bugs, easy to understand, and ready for change—affected your work. Point to an artifact or code location for each.

2. State the precondition, normal postcondition, and exceptional behavior of `add`. Why does “the set is unchanged” matter as part of the exceptional behavior?

3. Write your representation invariant and abstraction function in mathematical or precise prose. Which clause connects the internal representation to the maximal intervals returned to clients?

4. Identify two distinct overflow hazards that a straightforward interval-merging or interval-splitting implementation can encounter at the limits of `int`. Explain how your code avoids each without excluding a valid endpoint.

5. Describe an aliasing failure that could occur if `intervals()` exposed the representation. Distinguish an unmodifiable view from an immutable snapshot, and explain which behavior your contract requires.

6. Choose one focused example test and one model-based test from your suite. What different defect-finding role does each serve, and how is the model-based test reproducible?

7. Enumerate the structurally different effects that one call to `remove` can have on stored intervals. For each effect, identify a test in your suite or state the missing test you would add.

8. Give the worst-case time and space costs of each public operation in terms of the number of stored intervals. Which costs are guaranteed by the public contract, if any, and which are merely properties of your implementation?

9. Use evidence from `CHANGELOG.md` to explain one place where the abstraction reduced the cost of adding `remove`, and one place where your initial design created friction. What would you retain or revise in a second version?
