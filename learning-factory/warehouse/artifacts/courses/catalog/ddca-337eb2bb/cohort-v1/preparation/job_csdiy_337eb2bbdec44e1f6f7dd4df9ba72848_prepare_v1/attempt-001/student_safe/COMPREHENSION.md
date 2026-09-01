# Comprehension prompts

Answer all eight prompts in `answers.md`. Explain your reasoning and refer to your design or tests where useful. These are analysis prompts; this file intentionally contains no answer key.

1. Starting only from the meaning of binary addition, derive expressions for the one-bit sum and carry-out. Explain why each expression covers all eight input combinations.

2. Why are eight cases exhaustive for `full_adder`, and why are 512 cases exhaustive for `ripple_add4`? State the domain calculation rather than relying on a test-run count.

3. Trace the four stages for `a = 15`, `b = 1`, and `carry_in = 0`. At each bit position, record both the sum bit and the carry passed onward, then connect the trace to the public arithmetic invariant.

4. Consider a mutant implementation in which every bit position receives the original `carry_in` instead of the preceding stage's carry-out. Give a small valid input that distinguishes the mutant from the contract and explain the propagation error.

5. Suppose a test computes expected outputs by copying the same Boolean equations used in production. Why can both copies agree and still be wrong? Explain how your arithmetic oracle reduces that risk and name one risk it does not eliminate.

6. Python treats `bool` as a subclass of `int`. Why does the task nevertheless reject `True` and `False`? Discuss the difference between a language-level representation accident and an interface-domain decision.

7. Exhaustive tests can establish the modeled truth table but do not make a four-stage ripple design fast. Explain the longest carry dependency and compare it with a dependency chain or parallelization limit from an algorithm you know.

8. Identify the evidence needed to support completion of this kickoff unit. Then explain why that evidence cannot support a claim that the full Digital Design and Computer Architecture course—or an official ETH Zurich lab—has been completed.
