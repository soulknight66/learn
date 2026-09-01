# Design questions

Answer these before implementing each milestone. Keep your answers with your own work; no canonical answers are learner-visible.

## Parsing

1. What lexer states do you need, and which bytes cause a transition in each state?
2. How will you represent an empty quoted argument distinctly from no argument?
3. Can token storage be transferred into command argument vectors, or must it be copied? Who frees it after an error halfway through parsing?
4. Which validation pass guarantees that no child has been launched before a syntax error is known?

## Pipeline execution

5. For an `N`-command pipeline, how many pipes and descriptors exist? Which descriptors remain open in each child immediately before `execvp`?
6. What happens if pipe creation succeeds twice and the third call fails? What happens if the second `fork` fails?
7. Why can waiting for command 1 before forking command 2 deadlock on input larger than a pipe buffer?
8. Which child determines the public status, and how will you retain that fact if children finish out of order?

## Built-ins and jobs

9. Which built-ins must mutate parent state? What should happen if they appear in a pipeline?
10. What per-process states are needed to derive a whole job's `Running`, `Stopped`, or `Done` state?
11. When can a completed job be removed without making `jobs` or `wait` nondeterministic?
12. How will monotonically increasing job IDs behave after jobs are deleted?

## Terminal control

13. What race exists between `fork`, `setpgid`, and `exec`, and which processes can safely call `setpgid`?
14. Which signals should the interactive shell ignore, and why must children undo that choice?
15. What must happen to terminal ownership on every foreground error, normal exit, signal exit, and stop path?
16. How can automated tests distinguish correct process-group behavior from a shell that merely happens to run a pipeline?

## Review checklist

17. Can any descriptor remain open across `exec` unintentionally?
18. Can any allocation size overflow or any `realloc` lose the old pointer?
19. Can an interrupted system call corrupt state or make the shell exit unexpectedly?
20. Which claims in your README are backed by a reproducible command and captured result?
