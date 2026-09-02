# PyDocklet: build a container-like runtime in Python

PyDocklet is a systems-programming challenge about the mechanics underneath a small Docker-style
tool. You will import immutable filesystem layers, create writable container snapshots, persist a
container lifecycle, and execute a command with bounded resources. The finished project is useful as
a teaching model, but it is **not a security boundary** and must never run untrusted programs.

## Learning path

Material is intentionally revealed in stages:

1. Read `REQUIREMENTS.md` and `CONCEPTS.md`. Answer `DESIGN_QUESTIONS.md` before coding.
2. Work through the numbered TODOs described in `starter/README.md`.
3. Run the public contract tests. They cover representative cases, not the complete threat model.
4. Ask an instructor for adversarial, debugging, or review exercises only after the core suite passes.

An actual learner view has no `sealed/` tree or evaluator exercises. If those paths are present, you
have received the production pack rather than the student artifact; stop and ask the distributor to
correct the release.

## Distribution boundary

The full repository is an evaluator pack and MUST NOT be handed to learners. Distributors validate
its exact learner allowlist without writing an output tree with:

```bash
python3 environment/export_student_view.py --source . --check
```

They then export to a new, separate destination with `--destination PATH`. Only paths named in
`environment/student_view_allowlist.json` are copied. The factory publishes that exported artifact
separately; prose instructions are not the access boundary. Every export includes
`environment/COPYING_NOTICE.md`, whose generated-material terms must remain with learner copies.

## Quick start

No third-party packages are required. From the repository root:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

The starter intentionally raises `NotImplementedError`; an untouched checkout will not pass. Keep
the public API stable while replacing TODOs. A convenient manual flow after implementation is:

```bash
PYTHONPATH=starter python3 -m pydocklet --root .docklet import demo layer.tar
PYTHONPATH=starter python3 -m pydocklet --root .docklet create demo python3 app.py
PYTHONPATH=starter python3 -m pydocklet --root .docklet start c000001
PYTHONPATH=starter python3 -m pydocklet --root .docklet inspect c000001
```

Use a disposable `.docklet` directory. Do not commit it; imported layers can contain arbitrary data.

## What “isolation” means here

The portable target uses a dedicated working directory, an explicit environment, argv-only process
launch, a fresh process group, a timeout, and bounded captured logs. It does not use `chroot`, user or
mount namespaces, seccomp, cgroups, capability dropping, or network namespaces. An absolute path in a
child process still names the host filesystem. This limitation is central to the exercise rather than
something to hide.

Linux namespace support is an optional design extension, not part of the validated baseline. Never
run learner or reference code with elevated privileges.

## Repository map

- `starter/`: learner-owned Python package with explicit TODOs.
- `public_tests/`: stable, black-box API checks.
- `environment/`: supported host and dependency notes.
- `sealed/`: reference implementation and private evaluation material, present only in the full pack.
- `MANIFEST.yaml` and `PROVENANCE.json`: immutable generation and provenance records.

`MANIFEST.yaml` and the learner-safe `environment/COPYING_NOTICE.md` are in the learner view. The
full `PROVENANCE.json`, evaluator boundary/review records, private tests, and validation evidence
remain with the evaluator pack.

The authoritative status is `GENERATED` + `PARTIAL`; independent validation is mandatory.
