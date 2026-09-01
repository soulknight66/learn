# Learner Validation Record

Validation label: `LEARNER_SELF_CHECKED`.

This is learner-run evidence for the bounded kickoff only. It is not harness-controlled or
independent validation.

## Environment and commands

The supported interpreter actually used was CPython 3.11.5. In this workspace the unqualified
`python3` initially resolved to Python 3.6, so the Python 3.11 installation was placed first on
`PATH` before running the specified command form:

```bash
PATH=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin:$PATH \
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Observed outcome: exit code 0; 32 tests ran in 4.127 seconds; final unittest result `OK`.

A targeted core run used the supplied representative model under the same interpreter. Observed
outcome: `CONVERGED` after 40 updates, allocation
`(0.5142857120180376, 0.25714285900887307, 0.2285714289730893)`, objective
`0.07142857142857145`, fixed-point residual `8.228356884742993e-10`, and feasibility residual
`0.0` at tolerance `1e-9`.

## Observed contract cases

The CLI tests start the real module in a new process with a five-second timeout and observed:

- converged representative input: exit 0, one normal JSON document on stdout, empty stderr;
- malformed JSON and each validation category: exit 2, empty stdout, one JSON error on stderr;
- forced one-update exhaustion: exit 3, `MAX_ITERATIONS` result on stdout, empty stderr;
- finite but overflow-prone input: exit 4, empty stdout, stable `NUMERICAL_FAILURE` on stderr;
- injected unexpected runtime failure at the adapter boundary: exit 1, empty stdout, stable generic
  `INTERNAL_ERROR` on stderr, with the private exception text absent; and
- two identical raw inputs: identical return code and byte-for-byte identical streams.

The suite also observed the required projection examples, one-item/symmetric/boundary/zero-budget
solves, convergence on the final permitted update, raw-byte hash sensitivity, negative-zero
normalization, permutation equivariance, common-weight scaling invariance, and agreement within the
stated `0.001` resolution of an independently written two-item finite-grid oracle.

## Raw-input hashing rule

`input_sha256` is lowercase hexadecimal SHA-256 over the file's exact bytes as read, before UTF-8
decoding or JSON normalization. Spaces, line endings, member order, and numeric spelling therefore
affect the digest. A test feeds semantically equal compact and indented documents and observes
different hashes.

## Failure retained during development

The first attempted test command used the workspace's default Python 3.6. It exited 1: source
imports failed because that interpreter does not support the Python 3.11-targeted annotation
features, and downstream CLI assertions consequently saw exit 1. The source was not downgraded;
the experiment was rerun with the required interpreter. Details are in `debugging-log.md`.

## Remaining limitations

- Evidence and expected values were written and run by the learner, not an independent harness.
- Binary64 overflow, underflow, cancellation, and ill-conditioning remain possible; detected
  non-finite results become exit 4, while slow finite progress may become exit 3.
- The finite-grid oracle covers one two-item instance and cannot certify arbitrary real inputs.
- Deterministic bytes are claimed only for identical input on the supported Python version.
- No external course resources, optimization package, large benchmark, or deployment test was used.

