# Unit 01 Comprehension Prompts

Submit responses in `COMPREHENSION_RESPONSES.md`. Number them 1–8. Use your own implementation and evidence; this sheet contains questions only.

1. State the coverage invariant your implementation uses. How do you normalize or otherwise account for winding, and how is an exact shared-edge sample assigned to only one of two adjacent triangles? Point to the relevant implementation and tests.

2. Explain how your barycentric weights are obtained and identify two properties that your tests check. What should those properties reveal if the vertex order changes but vertex attributes remain attached to their vertices?

3. Give the rasterization time complexity for a scene in terms of the clipped pixel bounding boxes. Compare it with scanning the entire framebuffer per triangle, and name a scene where the distinction matters.

4. Your contract skips exactly zero-area triangles but does not declare every skinny triangle degenerate. Explain the numerical risk in using one unconditional epsilon for all scenes. Describe the concrete policy your code follows and its limitations.

5. Trace one valid scene from input tokens to final PPM bytes. Identify where each validation boundary lives and which parts can be tested without filesystem or process setup.

6. Choose one malformed-input case and one output-failure case. Explain how each propagates to the CLI status and why neither can leave a success-looking result. Cite the corresponding tests.

7. Describe a fixed-seed property check in your suite: its generated inputs, invariant, oracle, and failure report. Explain what this check can find that your hand-picked examples may miss, and what it cannot prove.

8. Suppose a future change adds depth buffering and perspective-correct attributes. Identify which current interfaces and invariants should remain stable, which must change, and how you would stage the change without invalidating existing deterministic tests.

**Scope label:** `UNIT_01_ONLY`  
**Source label:** manager-authored from catalog-declared topics; no remote course content was retrieved  
**Validation label:** `PREPARED_UNVALIDATED`
