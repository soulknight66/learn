# Comprehension Questions

Answer these in `submission/COMPREHENSION_RESPONSES.md` in your own words. Refer to concrete control paths or tests in your implementation where useful.

1. After `fork`, what is copied logically, what remains backed by shared operating-system state, and why does that distinction matter for redirected file descriptors?
2. Why does passing an argument vector directly to an `exec` function preserve a safer boundary than concatenating arguments into a shell command? Give one input that distinguishes the behaviors.
3. Describe every observable outcome your parent can receive for the direct child. How does the encoded `waitpid` status distinguish them?
4. If child-side redirection succeeds but execution of the requested program fails, which process should emit a diagnostic, where should it appear, and how does the parent eventually finish?
5. Why is elapsed-time measurement appropriate for a timeout while calendar time is not? What kinds of clock changes should not extend the child's budget?
6. Identify a race between natural child exit and timeout enforcement. What invariant must hold regardless of which event wins?
7. Why target a process group on timeout instead of only the direct child? State one limitation that process groups do not solve.
8. Choose one system call in your implementation that can be interrupted. Explain how you decide whether to retry, change state, or fail.
9. Which of your tests is most likely to become flaky under heavy machine load? Describe how its assertions create timing margin without making the test unbounded.
10. Suppose this runner became one component in a larger build service. Name two interface or observability decisions you would revisit, and explain the tradeoff behind each without implementing the expansion.
