# Adversarial checks

These black-box checks probe the edges of the public `minictr` contract. They do
not inspect or modify implementation files. In particular, they exercise name
validation, rootfs validation, duplicate operations, deterministic listing,
argument boundaries, exit-status propagation, and deletion while a run is
active.

Run them from the repository root:

```bash
bash adversarial/run.sh ./starter/minictr
```

The harness creates a private temporary `MINICTR_HOME`, uses a fake isolator,
and removes its temporary files on exit. It must not be run against a state
directory that contains useful data. No root privileges or namespace support
are needed. A timeout in the active-run case is reported as a failure instead
of waiting indefinitely.

These checks are deliberately incomplete. They do not establish that the
default isolator is secure, that kernel namespaces are available, or that the
runtime is production-ready. Run the public tests as the primary learner
feedback and treat this directory as extra hostile-input practice.

