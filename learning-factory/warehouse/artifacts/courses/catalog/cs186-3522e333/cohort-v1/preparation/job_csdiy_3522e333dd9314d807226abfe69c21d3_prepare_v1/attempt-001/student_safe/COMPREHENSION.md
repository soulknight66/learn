# Comprehension Check

> Unit: `managed_unit_01_relational_pipeline` · Classification: manager-authored learner assessment · Validation label: `PREPARED_NO_ANSWERS`

Answer these questions in your own words after completing the implementation. Refer to your code by component or method name where useful. Save your answers as `COMPREHENSION_RESPONSE.md`; do not modify this prompt file to embed answers.

1. Consider the ordered rows under schema `(id INT, team TEXT, score INT)`:

   ```text
   (7, "blue", 12)
   (3, "red",   5)
   (9, "blue",  8)
   (4, "blue", 12)
   (6, "red",  20)
   ```

   Trace this pipeline in pull order: scan; filter `team = "blue"`; filter `score > 8`; project `(id, score)`; limit `2`. Show every row emitted by each stage, the final output schema, and the point at which upstream work can stop.

2. Pick two invalid inputs from different categories (for example, schema/type misuse and lifecycle misuse). Explain where your implementation detects each one, what the caller observes, and why that detection boundary is preferable to a later failure.

3. State the lifecycle invariant that prevents an upstream operator from being closed twice. Walk through both normal exhaustion and early limit termination, and identify the tests that would catch a violation.

4. Describe your fixed-seed generated test. Why is its oracle independent enough to find a shared bug rather than merely repeat the production algorithm? Name one defect it can detect that your hand-written examples might miss.

5. Give one example where the asymptotically simplest implementation would still be poor production engineering in this task. Discuss the tradeoff using ownership, diagnostics, coupling, or reproducibility rather than runtime alone.

6. Suppose a later unit replaces the in-memory scan with disk-backed pages. Identify one contract that should remain stable, one contract that must become richer, and one new failure mode that needs explicit representation. Keep the proposal within the operator boundary; do not design an entire storage engine.
