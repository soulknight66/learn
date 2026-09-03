# Design questions

Answer these before or while implementing. Defend invariants rather than matching a particular code layout.

1. What object owns each token string before parsing, and when does ownership change?
2. How will an empty quoted argument differ from “no word currently being built”?
3. At which layer are duplicate redirections detected, and why?
4. How do you make every partially constructed token list and pipeline safe to free?
5. Which pipe ends must each child retain immediately before redirection and `execvp`?
6. Why must the parent close pipe ends before waiting?
7. Which process chooses the pipeline's process-group ID, and what races require duplicate `setpgid` calls?
8. How will terminal ownership be restored after normal exit, a signal, or an interrupted wait?
9. How do you identify the last pipeline command's status if children finish out of order?
10. What should happen to already-created children when a later `fork` fails?
11. Which built-ins fundamentally require execution in the parent, and what policy applies inside a pipeline?
12. How can tests detect descriptor leaks and zombies without depending on timing alone?
