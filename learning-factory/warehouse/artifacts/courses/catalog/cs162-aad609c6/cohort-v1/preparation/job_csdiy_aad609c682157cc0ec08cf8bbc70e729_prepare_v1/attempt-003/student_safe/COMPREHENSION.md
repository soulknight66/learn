# Comprehension Prompts

Answer all prompts in `RESPONSES.md` after implementing and testing the simulator. Refer to concrete functions and test names where requested. This file contains questions only; no solution or scoring guide is included.

1. Describe your task state model. State at least three invariants that hold at every scheduling boundary, and identify where the implementation establishes or checks each one.

2. For the required example in `STUDY_TASK.md` with quantum 2, show the ready queue and running task at every dispatch boundary. Then give every required output line, including the summary.

3. Construct the smallest workload you can that would produce different results if an unfinished task were requeued before tasks arriving exactly at the slice-ending boundary. Explain what observable output distinguishes the two rules and name the automated test that checks it.

4. Which parts of your program implement scheduling policy, and which implement mechanisms that could be reused by another policy? Describe one interface boundary that keeps those concerns separate.

5. Pick one malformed-input case that is easy to accept accidentally in C. Trace how your program detects it, prevents partial standard output, and releases resources. Cite the corresponding test.

6. Explain the integer types used for parsed values, accumulated service, clock time, and metrics. Show why the public limits are safe under those choices and where conversion or overflow is rejected.

7. Give the asymptotic time and auxiliary-space costs in terms of task count, dispatch count, and input size. Identify one implementation choice made for clarity or reliability rather than the lowest possible asymptotic bound.

8. Suppose the next unit added a preemptive-priority policy while retaining this input and report format. Identify the modules, invariants, and tests that should remain unchanged, and the ones that would need revision. Do not implement the extension.
