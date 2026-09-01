# Postmortem

Passing the model does not establish kernel-level competence. It does expose whether the
learner can keep fork, unlink, unmap, exec, and exit invariants consistent when ordinary COW
and intentional sharing coexist. A later attempt should implement the mechanism in xv6 or a
small native runtime and stress actual fault paths.
