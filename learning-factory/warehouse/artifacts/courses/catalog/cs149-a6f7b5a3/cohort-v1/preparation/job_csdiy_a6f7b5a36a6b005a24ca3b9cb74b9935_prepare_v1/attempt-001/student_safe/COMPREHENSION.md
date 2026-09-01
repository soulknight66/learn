# Comprehension Prompts

Answer in your own `COMPREHENSION_ANSWERS.md`. Refer to your design and observations where requested. These prompts ask for reasoning; short unsupported definitions are insufficient.

1. For your chosen decomposition, express total work and critical-path length in terms of input size `N` and requested threads `T`. Which operations or phases determine the critical path?

2. Describe every location that can be mutated while worker threads are active. For each, explain why two workers can or cannot access it concurrently and how the C++ memory model makes the access safe.

3. Consider `N = 3` with `T = 8`, and also `N = 0`. What does your public contract require, how many workers does your implementation actually create, and why is the result correct?

4. Exact equality with the sequential oracle is necessary evidence. Why is it not by itself proof that the parallel implementation has no data race? Name one additional method of evidence and one limitation of that method.

5. A one-thread parallel run is slower than the sequential implementation, while a larger run improves at two threads and then flattens. Give three distinct plausible causes. For each cause, name an observation or experiment that would help distinguish it from the others.

6. Explain why input generation, file I/O, worker creation, and result combination may need different treatment in a benchmark. State exactly which of these your primary timed region includes and defend that choice.

7. Pick one performance statement from your report. List the machine, workload, build, repetitions, and uncertainty information needed to make that statement reproducible. Rewrite the statement so that it does not generalize beyond your evidence.

8. Suppose the histogram is embedded in a long-lived service that processes many small buffers. Identify one design decision you would reconsider, and propose a test that evaluates the new trade-off without weakening correctness checks.

9. What did the sequential oracle make easier to engineer? Describe one class of bug it can expose reliably and one class it might fail to expose on a particular run.

10. Identify the strongest remaining limitation of your implementation or evidence. Propose a narrowly scoped next unit or experiment, but do not claim it has already been completed.
