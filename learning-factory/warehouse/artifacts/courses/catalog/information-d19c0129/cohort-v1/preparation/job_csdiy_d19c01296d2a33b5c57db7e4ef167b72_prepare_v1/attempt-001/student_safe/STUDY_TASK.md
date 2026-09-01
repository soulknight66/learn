# Study Task: Build a Streaming Empirical-Entropy Tool

> Provenance: manager-authored kickoff task; not an MIT assignment.
>
> Validation label: `LEARNER_SAFE_UNVALIDATED_KICKOFF`.

## Goal and boundary

Create a small Python 3.11 utility that reports the empirical byte entropy of one non-empty file. The implementation must also expose a reusable count-based entropy function. Use only the Python standard library and keep the work to the four deliverables below.

Do not depend on the catalog's external links: their contents are not present in this workspace, and this task is self-contained.

## Deliverables

Create:

```text
submission/
├── entropy_tool.py
├── test_entropy_tool.py
├── README.md
└── COMPREHENSION_RESPONSES.md
```

- `entropy_tool.py` contains the reusable function, streaming file analysis, and CLI.
- `test_entropy_tool.py` contains deterministic `unittest` tests.
- `README.md` states the contract, design choices, complexity, and exact run/test commands.
- `COMPREHENSION_RESPONSES.md` gives your own numbered responses to `COMPREHENSION.md`.

Do not copy the prompts into code comments merely to create volume. Keep generated caches, environments, and large fixtures out of the submission.

## Public behavior

### Reusable calculation

Provide this importable function in `entropy_tool.py`:

```python
def entropy_from_counts(counts):
    """Return base-2 empirical entropy as a float."""
```

Its contract is:

- `counts` is a finite iterable of Python integers;
- booleans and non-integers are invalid counts;
- each count must be non-negative;
- at least one count must be positive;
- zero entries are permitted and make no contribution; and
- invalid types raise `TypeError`, while an empty/all-zero collection or a negative count raises `ValueError`.

Do not silently clamp, take absolute values, or normalize malformed input. Consume a one-shot iterable at most once.

### File analysis

Interpret the target file as raw bytes, with an alphabet of 256 possible byte values. Read it in bounded-size binary chunks and count every byte, including null bytes, newlines, and byte sequences that are not valid UTF-8. Do not use an unbounded `read()` call and do not retain a copy of the file contents.

For a valid non-empty file, compute:

- `byte_count`: total observed bytes;
- `distinct_byte_values`: number of byte values with positive counts; and
- `entropy_bits_per_byte`: base-2 empirical entropy.

An empty file is a domain error, not a zero-entropy success.

### Command line

This invocation is the supported interface:

```bash
python3 submission/entropy_tool.py PATH
```

On success, exit with status `0` and write exactly one JSON object to standard output containing exactly the three keys above. Values for both counts are JSON integers; entropy is a finite JSON number. Do not add explanatory prose to standard output.

For a missing argument, extra argument, missing/unreadable file, directory in place of a file, or empty file, exit nonzero, emit a concise diagnostic on standard error, and emit no success JSON. Avoid a traceback for an expected user error.

## Required test coverage

Use `unittest` and temporary files. Include focused tests for:

- a distribution with one observed symbol;
- two equally frequent symbols and four equally frequent symbols;
- zero entries mixed with positive counts;
- relabeling/permuting symbols and scaling all counts by the same positive integer;
- empty, all-zero, negative, boolean, and non-integer count inputs;
- null bytes, newlines, and bytes that are invalid UTF-8;
- empty-file rejection;
- a file spanning more than one read chunk; and
- CLI success JSON plus at least two CLI failure paths.

Compare floating-point values with a stated tolerance. Tests must be repeatable, must not use the network, and must not rely on files outside temporary test data you create.

## Design evidence

In `README.md`, state:

- the accepted-input and error contract;
- why the observation model uses bytes;
- the chosen chunk size and why file contents are not retained;
- time and auxiliary-space complexity, with variables defined;
- commands to run the tool and the full test suite; and
- one limitation of single-byte empirical entropy.

Run at least:

```bash
python3 -m unittest discover -s submission -p 'test*.py' -v
python3 submission/entropy_tool.py SOME_NONEMPTY_FILE
```

Inspect the actual exit status and JSON rather than treating the command's existence as proof it passed.

## Completion boundary

Stop after the four deliverables are implemented, locally exercised, and ready for independent evaluation. Do not claim completion of the full information-theory course, do not reconstruct unavailable MIT assignments, and do not place examiner material in the submission.
