# Design questions

Write down your answers before implementation. Revisit them after the tests pass.

1. Why is checking `str(candidate).startswith(str(root))` insufficient? Give two counterexamples.
2. Should `a/../b` be normalized or rejected? What ambiguity does your choice remove?
3. Why must the complete tar header set be validated before the first whiteout or write is applied?
4. What should happen if one layer contains both `.wh.note` and a new `note` file?
5. Which exact bytes and ordering should determine an image digest? How do you ensure later
   application consumes those same bytes? Should the image tag participate?
6. How can two image tags safely share one snapshot without allowing a container or caller to mutate
   it? What detects a same-user chmod-and-write?
7. Which invariant belongs in application code, and which also belongs in a SQLite trigger?
8. What race occurs with `SELECT state` followed later by `UPDATE state` in deferred transactions?
9. If a worker dies after committing `RUNNING` but before `Popen`, what evidence could distinguish
   that case from a long-running process?
10. Why can `communicate()` with pipes be dangerous even when a subprocess timeout is configured?
    Does your output byte limit include truncation-marker and UTF-8 replacement overhead?
11. What does `start_new_session=True` enable? What does it fail to isolate?
12. Which host resources remain reachable when only `cwd` and environment are changed?
13. In what order would a Linux helper create user and mount namespaces, map IDs, mount a rootfs,
   drop capabilities, apply seccomp, and exec? Which steps require privilege?
14. What cleanup is safe after a crash, and how would you prove that a path belongs to this runtime?
15. Which claims could this project truthfully make after public tests pass? Which require independent
   security review or a hostile multi-tenant test environment?
