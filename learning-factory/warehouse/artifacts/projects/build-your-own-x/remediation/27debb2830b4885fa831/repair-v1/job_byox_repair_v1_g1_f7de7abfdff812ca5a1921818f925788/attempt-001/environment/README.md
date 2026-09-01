# Environment

The project has no third-party dependencies. It targets Node.js 20 or newer because tests use the
built-in `node:test` runner and modern ECMAScript module features such as `Array.prototype.at`.

Expected commands:

```sh
node --version
cd starter && npm test && npm run test:public
```

Generation host observation on 2026-08-31: `node`, `nodejs`, `npm`, `deno`, `bun`, `qjs`, `js`, and
`quickjs` were not found on `PATH`. Python 3.6.8 was available for metadata and structure checks only.
No dependency installation or network access was attempted.

GJS 1.56.2 (SpiderMonkey JavaScript-C60.9.0) was available, but that command exposes only classic
script mode. Loading the reference entry point rejected its top-level `import`, and `gjs -m` was an
unknown option. It cannot directly execute this Node.js ECMAScript-module project or its `node:test`
suites. An evaluator-only mechanical bundle provided supplemental smoke coverage as documented in
`../VALIDATION.md`; it is not a substitute for Node.js validation.

`check.mjs` is a small reproducible runtime preflight. It does not install or alter anything.

## Deterministic learner view

`learner_view.py` is the worker-harness boundary for progressive disclosure. Its fixed allowlist is
limited to `README.md`, `AGENTS.md`, `MANIFEST.yaml`, `REQUIREMENTS.md`, `CONCEPTS.md`,
`DESIGN_QUESTIONS.md`, `starter/`, `public_tests/`, and `environment/`. It rejects symlinks and
special files, requires an exact destination file set, verifies byte-for-byte hashes, and checks
that no learner file duplicates a sealed-file hash.

Policy-only generation check (creates nothing):

```sh
python3 -B environment/learner_view.py check-policy
```

Worker-harness export and verification (the destination must not already exist and must be outside
the complete artifact):

```sh
python3 -B environment/learner_view.py export /absolute/new/learner-view
python3 -B environment/learner_view.py verify /absolute/new/learner-view
```

The export/verify commands are supplied for a trusted harness; they were not run during generation.
Their presence does not earn a transfer-validation label.
