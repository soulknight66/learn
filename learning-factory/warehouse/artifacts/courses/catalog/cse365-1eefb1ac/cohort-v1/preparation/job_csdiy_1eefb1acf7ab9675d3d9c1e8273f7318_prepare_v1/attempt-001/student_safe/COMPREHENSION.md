# Comprehension prompts

Answer each prompt in your own `COMPREHENSION_RESPONSES.md`. Refer to specific implementation choices and tests. These are reasoning prompts; do not merely state that your tests pass.

1. In a process launch, which values belong to the program's data model and which values can alter executable behavior? Explain how your interface maintains that distinction.

2. Consider this hypothetical design:

   ```python
   subprocess.run(f"python helper.py {action} {target}", shell=True)
   ```

   Identify its trust-boundary failures without supplying an attack command. Why would a correct digest algorithm not make this design correct as software?

3. State a precise invariant for a valid target path. Why are textual prefix checks insufficient? Discuss both `..` segments and symlinks.

4. What does a wall-clock timeout guarantee, and what does it not guarantee about descendants, CPU, memory, output volume, cleanup, or partial side effects?

5. Explain the structured result states you chose. Which fields allow a caller to tell rejection, launch failure, child failure, timeout, and success apart without inspecting prose?

6. Propose one property-style or metamorphic test that would generalize beyond the named examples in the required test matrix. State the property and how you would generate safe cases.

7. Suppose the same operation is later offered through an HTTP endpoint. Which trust boundaries stay the same, which new ones appear, and which part of your current interface should remain unchanged?

8. Separate these three claims: “the learner says the adapter is safe,” “the learner's tests pass,” and “an independent validator has accepted the unit.” What evidence supports each, and why are they not equivalent?
