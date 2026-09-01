# Comprehension prompts

Answer all prompts in `submission/COMPREHENSION_RESPONSES.md`. Favor precise reasoning over long responses; about 2–6 sentences per prompt is usually enough.

1. Why can the classifier rank neighbors by squared Euclidean distance without taking square roots? State what this does and does not change.

2. Construct a situation in which several training rows are equally distant from a query. Explain how every specified tie rule affects reproducibility and whether changing training-row order can still change the result.

3. Suppose means and scales were fitted on all 240 rows before splitting. Explain the information leak even though labels are not used by the standardizer. How does your experiment avoid it during both selection and final evaluation?

4. Distinguish a test that establishes deterministic behavior from one that establishes predictive correctness. Give one example of each from your suite and name a bug each could catch.

5. Derive the fit and prediction time and auxiliary-space complexity of your implementation using `n` training rows, `d` features, `q` queries, and `k` neighbors. Identify which step dominates for large `n`.

6. Name one exact-search data structure or algorithm that might reduce query cost. Under what data distribution or dimensional regime might it help, and why is it not an automatic improvement?

7. Why is the test partition evaluated only after choosing `k`? If two candidates tie on validation accuracy, what engineering benefit does the specified selection rule provide beyond statistical considerations?

8. Imagine another engineer receives only your repository and `experiment.json`. Which fields and commands let them reproduce the run, and what additional provenance would be needed before using real external data in place of the generator?
