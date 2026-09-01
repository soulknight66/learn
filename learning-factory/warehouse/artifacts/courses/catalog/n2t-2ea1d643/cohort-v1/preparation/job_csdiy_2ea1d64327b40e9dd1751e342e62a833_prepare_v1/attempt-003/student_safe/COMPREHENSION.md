# Comprehension Prompts

Answer each prompt in `submission/COMPREHENSION_RESPONSES.md`. Refer to specific files, test cases, and evidence from your own implementation. Do not use inaccessible course material.

1. **Two kinds of correctness.** Separate the claim that each component returns the specified output from the claim that it obeys the NAND-only construction constraint. What evidence supports each claim, and why does one not automatically prove the other?

2. **Finite-domain evidence.** Explain why exhaustive enumeration is feasible for every component in this unit. Precisely state what your passing enumeration establishes and name at least two relevant properties it does not establish.

3. **Independent oracle.** How did you keep expected test results independent of the implementation? Identify one circular test design that could pass even when both the test and implementation are wrong.

4. **Fault sensitivity.** Describe the temporary fault used for your mutation check. Which case or cases detected it? If some cases did not, explain why that is expected.

5. **Abstraction and dependencies.** Walk through your dependency DAG. How does its structure help review, change isolation, and debugging? What failure would a cycle introduce in your chosen implementation model?

6. **Interface boundary.** Defend your input-domain and invalid-input policy. Identify one host-language coercion or type behavior that could otherwise make the library surprising.

7. **Scaling the method.** Exhaustive truth-table testing works here. Explain why the same method becomes impractical as input width or state grows, and propose two complementary verification techniques for a larger component.

8. **Bounded claim.** State exactly what completing this artifact demonstrates. Explain why it is not evidence that an official Nand2Tetris project, a hardware module, or the full course has been completed.
