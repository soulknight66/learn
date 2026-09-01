# Comprehension check

Answer every prompt in your own words. Refer to concrete functions, tests, or observations from your submission when requested. Do not paste source code in place of an explanation.

1. State the ordering relation for two items as a sequence of decisions. Why must creation sequence be the final decision rather than relying on whatever order the runtime happens to preserve?

2. Identify one domain function and one browser-effect function in your design. What makes the first independently testable, and what evidence shows the boundary is real?

3. Give one example of input that can pass an HTML control's ordinary interaction but still needs validation in JavaScript. Explain where trust is established in your program.

4. Trace an Add action from user input to persisted state and rendered output. At which points can the operation fail, and how does the application avoid a partial update?

5. Why is parsed JSON not automatically valid application state? Name at least four invariants your restore path checks and describe what your interface does after rejection.

6. Choose one ordering test that could pass even if the comparator had a subtle defect. Describe a stronger test or set of examples that would expose that defect.

7. Describe two accessibility decisions in the interface. For each, state the user need it addresses and the manual observation you made.

8. A teammate proposes adding editing, deletion, server synchronization, and deployment before review. Explain which changes belong outside this unit and how respecting the boundary improves the reliability of the submitted evidence.

9. Describe one implementation limitation that remains after this kickoff. Distinguish it from a failed stated requirement, and propose the next smallest study step.

At the end, add the commit or submission identifier you reviewed and the exact test command whose output you used while answering.
