# Design questions

Answer these before comparing your work with any instructor material.

1. Why should archive validation finish before the first payload byte is written? Which failures can still leave a partial rootfs afterward?
2. How can an existing symlink in a destination rootfs turn a seemingly normalized member path into an escape?
3. Should a payload exit code of 1 mean the runtime failed, or that the runtime successfully observed a failed workload? How should durable state represent the distinction?
4. Why is `BEGIN IMMEDIATE` useful for compare-and-transition? What behavior would you expect with deferred transactions under contention?
5. Which lifecycle rules belong in Python, and which should be enforced in SQLite as well?
6. Why does a PID namespace operation normally need a fork? What responsibilities does PID 1 inherit?
7. What does `chroot` change, and what does it *not* isolate?
8. Which environment variables should cross into the payload? What risks follow from inheriting the caller's complete environment?
9. What cleanup is safe after an interrupted image import? How can staging names and atomic rename help establish ownership?
10. Which missing controls prevent this proof of concept from safely running hostile code?
