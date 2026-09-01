# Comprehension Prompts

Answer these prompts in `submission/COMPREHENSION_RESPONSE.md` after implementing and testing the application. Refer to concrete files, functions, and test names from your own submission. Aim for 150–250 words per response unless a prompt asks for a table.

## 1. Boundaries and dependency direction

Draw a small dependency diagram for your model, storage adapter, browser controller, and DOM. Explain which dependencies point inward or outward and identify one failure that your chosen boundary prevents from contaminating the model.

## 2. State invariants and atomic failure

State at least four collection invariants. Trace a submission containing a duplicate identifier, an invalid `n`, and a valid elapsed time through your code. Explain why no partial update can become visible or persistent, citing relevant tests.

## 3. Untrusted display data

Trace the required markup-like algorithm name from form input to its displayed table cell and back through persistence. Identify every trust boundary it crosses, the browser behavior that would be dangerous, and the evidence that your implementation preserves literal text.

## 4. Persistence recovery

Compare these three storage states in a table: missing key, malformed JSON, and valid JSON with an invalid record. For each, give your load result, user-visible behavior, overwrite behavior during initial load, and the automated test that demonstrates it. Explain why the cases should or should not be equivalent.

## 5. Determinism and diagnostic value

Choose two tests that could pass accidentally in a stateful or nondeterministic suite. Explain how your fixtures, identifiers, ordering rule, fake storage, and setup/teardown choices make failures reproducible and diagnostically useful.

## 6. Controlled change

Suppose the next unit requires editing an existing run while preserving identifier uniqueness and the same validation rules. Describe the smallest contract-level changes you would make, which module should own them, and which existing tests should remain unchanged. Do not implement the feature.

## Submission check

Before finishing, make sure every response cites evidence from your own work rather than only restating the task. If your implementation differs from the suggested design, identify the difference and justify how it still meets the behavioral contract.

---

**Provenance and status:** Manager-authored learner prompts for the bounded kickoff unit. They contain questions only; evaluation guidance is kept outside the learner-safe directory. Validation label: unassessed prompts.
