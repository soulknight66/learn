# Benchmark stage

Performance work begins only after correctness. The opt-in sealed driver times one million successful
translations with `clock()`. It is a smoke probe for accidental gross regressions, not a portable
benchmark: clock resolution, optimization, host load, CPU, and sandbox policy all affect the result.

For a meaningful study, pin the compiler and flags, warm up separately, run multiple samples, report
the full distribution and machine context, prevent dead-code elimination, and compare against a
declared baseline. Never promote a validation label from one local timing run.
