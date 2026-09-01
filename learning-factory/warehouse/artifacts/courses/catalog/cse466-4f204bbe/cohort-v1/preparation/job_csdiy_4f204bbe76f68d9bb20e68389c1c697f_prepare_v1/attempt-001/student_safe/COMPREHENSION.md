# Comprehension prompts

Answer these in `COMPREHENSION_RESPONSES.md` after finishing the implementation. Use your own words. Refer to named functions, states, and tests from your submission where requested. Do not include external exploit demonstrations.

1. Draw or describe your runner's state machine. Which terminal states are mutually exclusive, and where is that exclusivity enforced in your code?

2. Give one argument vector from your round-trip test that would have different meaning if joined into a shell string. Explain the trust-boundary error without showing a harmful payload.

3. A child writes enough data to fill stderr, then writes a completion marker to stdout. Explain how a runner that reads the streams sequentially can wait forever. Identify the part of your design that prevents this wait.

4. State a precise invariant relating the configured limit, `bytes_observed`, `bytes_stored`, and the decoded Base64 length. Point to two tests that exercise different sides of the invariant.

5. Why must the runner continue draining a pipe after it stops retaining bytes from that pipe? Contrast the memory-space bound with the progress requirement.

6. Describe one possible race between observing child exit and reaching the timeout deadline. What deterministic decision rule does your implementation apply, and how does your near-boundary test avoid assuming a deterministic scheduler?

7. Explain why terminating only the direct child is insufficient for the process-tree fixture. Describe how your tests establish cleanup without relying only on the runner's report.

8. Atomic replacement prevents one class of report corruption but does not make every failure disappear. Describe what it guarantees and give one report-publication failure it does not solve.

9. Pick one algorithmic technique you already knew—such as an invariant, state machine, amortized bound, or adversarial case analysis—and explain how operating-system behavior forced you to refine it in this lab.

10. Name two changes that would be needed before embedding this runner in a multi-user production service. Keep the answer defensive and within authorization boundaries.
