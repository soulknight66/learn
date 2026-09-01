# Comprehension Prompts

Create `COMPREHENSION_RESPONSES.md` at the root of your submission. Answer all eight prompts in your own words. Label responses `1` through `8`; concise answers are welcome when the reasoning is explicit. Do not include source code except for a small expression or input fragment needed to explain a point.

1. Under this unit's column-vector convention, write the expression for applying `A`, then `B`, then `C` to a point. Explain how that expression determines the update rule for a running composite matrix.

2. Give one concrete point and two elementary transforms for which reversing the transform order changes the result. Show both orders and explain geometrically why they differ.

3. Why can a 3-by-3 homogeneous matrix express 2D translation while an ordinary 2-by-2 linear map cannot? What role does the coordinate `w = 1` play for a point?

4. State the absolute/relative comparison rule used in your tests. Give one situation in this project where exact comparison is appropriate and one where approximate comparison is appropriate.

5. Explain why the CLI must parse and validate the complete file before printing its first point. Name a specific late-file error and describe the misleading observable behavior that buffering prevents.

6. Describe an inverse round-trip property for a composed transform. State the preconditions on scaling and the finite test domain that make your test claim honest; also name something the property would not prove.

7. Trace one malformed input from token reading to process exit. Which module discovers it, how is the error represented across boundaries, and which module owns the exact diagnostic text?

8. Suppose elementary-transform tests pass but a three-operation black-box test fails. Give a short, evidence-driven debugging plan that distinguishes a multiplication-order defect from parsing and output-formatting defects.
