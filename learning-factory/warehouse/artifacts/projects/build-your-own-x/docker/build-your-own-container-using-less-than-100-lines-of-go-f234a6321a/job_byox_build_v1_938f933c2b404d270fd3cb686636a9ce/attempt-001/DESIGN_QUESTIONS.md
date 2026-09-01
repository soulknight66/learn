# Design questions

Answer these before comparing your work with any sealed review material.

1. Why must mount propagation be changed before mounting anything under the new rootfs?
2. What observable difference is created by `CLONE_NEWPID`, and why does it apply only to children?
3. What is gained and what remains unsafe when host UID 1000 maps to container UID 0?
4. Why encode a distinct internal child marker instead of deciding the phase from an environment
   variable?
5. Which validation checks can race with a hostile process changing the rootfs afterward?
6. When should the parent preserve an exit status, and when should it use a runtime/setup status?
7. What responsibilities arise when the workload itself becomes PID 1?
8. Why does a network namespace without interface setup usually have no useful connectivity?
9. Which controls would you add before allowing untrusted code, and which kernel object owns each
   control?
10. How would a `pivot_root` design differ in setup, cleanup, and failure recovery?
11. Why can mounting the host's `/proc` by bind mount expose the wrong process view?
12. How would you test cancellation and signal behavior without letting unit tests perform mounts?
