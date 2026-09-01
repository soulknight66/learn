# Comprehension prompts

Answer in `submission/COMPREHENSION_RESPONSES.md`. Number the responses 1–8, use at most 150 words each, and cite concrete test names or benchmark `case_id` values where requested. These prompts ask for your reasoning; this file intentionally contains no answers.

1. For this quantizer, how does scale constrain the error of one reconstructed weight? Explain how weight-level errors can combine in one output row, including any assumptions your argument needs.

2. Suppose one matrix has a single large outlier while most weights are near zero. Predict what one per-tensor scale does to the smaller weights, and identify evidence from your implementation that could test the prediction.

3. Compare the logical payload calculation in `results.json` with the likely in-memory footprint of your Python objects. Why would presenting either number without its representation model be misleading?

4. Using at least two benchmark cases, state what happened to runtime as bit width changed. Explain why reduced logical payload does or does not translate to speed in this particular implementation; do not generalize beyond your evidence.

5. Which benchmark controls make the two paths comparable, and where is dequantization work paid? Describe one remaining source of bias and one concrete improvement for a larger experiment.

6. Give two properties from your seeded tests that cover more behavior than isolated examples. For each, name a plausible bug it could reveal and explain why its oracle is independent of the production implementation.

7. Why does an all-zero matrix need an explicit scale policy? Trace the consequences of your policy through serialization, `quantized_matvec`, validation, and repeatability.

8. If the component changed from one scale per matrix to one scale per output row, which API, metadata, tests, and storage calculations would have to change? What evidence would you require before adopting that design?

---

Provenance: manager-authored questions for `kickoff_u01_quantization_engineering`; no answer key is included in learner-safe material.
