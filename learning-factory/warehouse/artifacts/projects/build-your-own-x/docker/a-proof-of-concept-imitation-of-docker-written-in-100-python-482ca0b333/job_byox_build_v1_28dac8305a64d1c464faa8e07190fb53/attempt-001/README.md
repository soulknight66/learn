# MiniBox: build a tiny container runtime control plane

MiniBox is a deliberately small, Linux-oriented Build-Your-Own-X challenge. You will implement the safety-critical core of a container runtime in Python: identifier and state validation, safe filesystem-layer application, durable lifecycle transitions, namespace command construction, and bounded process execution.

This is an educational proof of concept, not a replacement for Docker. It does not implement image registries, cgroups, networking, seccomp, capabilities, or a production-grade overlay filesystem. Never run untrusted workloads with it.

## Progressive path

1. **Pure logic** — implement identifiers, container specs, and lifecycle transitions in `starter/minibox/models.py`.
2. **Filesystem boundary** — safely apply tar layers in `starter/minibox/archive.py`, including whiteouts without path traversal.
3. **Durable control plane** — implement the SQLite methods in `starter/minibox/state.py` using explicit transactions and compare-and-transition semantics.
4. **Isolation plan** — construct an argv-only `unshare` plan in `starter/minibox/runtime.py`.
5. **Integration** — connect image import, container creation, inspection, and execution in `starter/minibox/workspace.py` and `starter/minibox/cli.py`.

Read [REQUIREMENTS.md](REQUIREMENTS.md) before coding. `CONCEPTS.md` gives background without implementation answers, and `DESIGN_QUESTIONS.md` provides checkpoints for design review.

## Run the learner tests

From this repository root:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

The starter intentionally contains `NotImplementedError` markers, so the initial suite is expected to fail. Work milestone by milestone and keep all subprocess construction argv-based—never interpolate a shell command.

## Environment and safety

The core project uses only Python's standard library. Linux namespace execution additionally needs a Linux host with util-linux `unshare`, enabled user namespaces, and a suitable root filesystem containing the requested executable. Run the non-mutating capability probe described in `environment/README.md`; a failed probe is a supported result.

The sealed material is for independent validation and instructor review. Do not use it while solving the challenge. Passing local tests is useful evidence, but only the external harness can award validation labels.
