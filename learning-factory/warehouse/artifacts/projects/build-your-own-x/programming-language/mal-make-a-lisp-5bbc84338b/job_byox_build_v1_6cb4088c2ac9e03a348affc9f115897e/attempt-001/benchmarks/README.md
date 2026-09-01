# Benchmark status

No benchmark was executed and no performance number is claimed. Microbenchmarks would be misleading
until the semantic suite, bytecode verifier, and resource model are independently validated.

A future benchmark plan should retain raw inputs, exact commands, interpreter/OS details, warm-up
policy, sample distributions, and unrounded results. Useful separate workloads include reader
throughput by nesting shape, evaluator arithmetic/call depth, compile time, VM dispatch, and peak
memory. Evaluator/VM comparisons must use expressions supported by both and verify results before
timing them.
