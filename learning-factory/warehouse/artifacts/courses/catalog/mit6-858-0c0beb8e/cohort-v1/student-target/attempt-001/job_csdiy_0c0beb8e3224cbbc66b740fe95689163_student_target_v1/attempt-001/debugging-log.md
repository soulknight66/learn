# Debugging log

This is a chronological record of observable hypotheses, commands, failures, and conclusions for the kickoff unit. It does not reconstruct hidden reasoning.

## 1. JSON duplicate and whitespace semantics

**Hypothesis.** `json.loads` with an object-pairs hook would see nested duplicates; ordinary JSON trailing whitespace would be accepted; a Unicode non-breaking space would not count as JSON whitespace.

**First experiment.** The first one-line fixture used Python literals containing `"\\t\\r\\n"` and `"\\u00a0"`:

```bash
python3 -c 'import json

def no_dupes(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate")
        out[key] = value
    return out
samples = [("nested-duplicate", "{\"outer\":{\"role\":\"member\",\"role\":\"admin\"}}"), ("json-whitespace", "{\"a\":1} \\t\\r\\n"), ("unicode-nbsp", "{\"a\":1}\\u00a0")]
for label, source in samples:
    try:
        json.loads(source, object_pairs_hook=no_dupes)
        print(label + ": accepted")
    except (ValueError, json.JSONDecodeError) as exc:
        print(label + ": rejected:" + type(exc).__name__)'
```

Observed relevant output, exit 0:

```text
nested-duplicate: rejected:ValueError
json-whitespace: rejected:JSONDecodeError
unicode-nbsp: rejected:JSONDecodeError
```

**Failure and correction.** Inspection of the fixture showed that the latter two samples contained literal backslash escape sequences rather than the intended characters. I did not treat that rejection as evidence about whitespace. I reran the same loop with these exact sample constructors:

```python
samples = [
    ("nested-duplicate", "{\"outer\":{\"role\":\"member\",\"role\":\"admin\"}}"),
    ("json-whitespace", "{\"a\":1} " + chr(9) + chr(13) + chr(10)),
    ("unicode-nbsp", "{\"a\":1}" + chr(160)),
]
```

Corrected observation, exit 0:

```text
nested-duplicate: rejected:ValueError
json-whitespace: accepted
unicode-nbsp: rejected:JSONDecodeError
```

**Conclusion/change.** The parser uses an object-pairs hook and explicit JSON whitespace characters. The failed fixture also led me to prefer byte/character constructors in boundary probes when shell and language escaping overlap.

## 2. The mandated interpreter was older than assumed

**Hypothesis.** The specified command would discover the initial implementation's tests under a modern Python 3 interpreter.

**Experiment.** Exact command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

**Observation.** Exit status 1. Discovery produced two failed-test placeholders. Both source and test imports stopped at:

```text
SyntaxError: future feature annotations is not defined
...
Ran 2 tests in 0.000s
FAILED (errors=2)
```

The follow-up interpreter probe was:

```bash
command -v python3
python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed, exit 0:

```text
/usr/bin/python3
Python 3.6.8
Python 3.11.5
```

**Conclusion/change.** “Python 3” was not sufficient justification for newer syntax or `dataclasses`. I replaced postponed annotations, built-in generic syntax, union syntax, and dataclasses with Python-3.6-compatible `typing` forms and immutable `NamedTuple` models. I kept the exact required command as the baseline instead of silently switching to 3.11.

## 3. A running interpreter did not identify a relaunch path

**Hypothesis.** After the compatibility rewrite, subprocess tests could use `sys.executable` to launch the CLI.

**Experiment.** I reran:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

**Observation.** Sixteen non-process tests passed, but five subprocess executions errored; the summarized run was:

```text
Ran 21 tests in 0.016s
FAILED (errors=5)
PermissionError: [Errno 13] Permission denied: ''
```

I isolated the assumption with:

```bash
PYTHONPATH=src python3 -c 'import shutil,sys; print("sys.executable=" + repr(sys.executable)); print("which.python3=" + repr(shutil.which("python3")))'
```

Observed, exit 0:

```text
sys.executable=''
which.python3='/bin/python3'
```

**Conclusion/change.** The managed runner can execute Python while leaving `sys.executable` empty. The test helper now selects `sys.executable or shutil.which("python3")`, fails explicitly if neither exists, uses an argv array, provides a minimal environment, starts a new session, captures both streams, and applies a three-second timeout. This changed my environment model rather than merely correcting syntax.

## 4. Bounded reads must tolerate short reads

**Hypothesis.** A single `read(4097)` is usually sufficient for buffered standard input but embeds an avoidable assumption that the read cannot return early. A synthetic stream returning three or seven bytes per call should still be consumed only through EOF or byte 4,097.

**Experiment.** I introduced `ShortReadStream` as a deterministic local fake and ran:

```bash
PYTHONPATH=src:tests python3 -m unittest -v test_boundary.BoundedReadTests
```

Observed, exit 0:

```text
test_short_reads_are_joined_until_eof (test_boundary.BoundedReadTests) ... ok
test_short_reads_stop_after_overflow_detection_byte (test_boundary.BoundedReadTests) ... ok

Ran 2 tests in 0.001s
OK
```

**Conclusion/change.** `_read_bounded` loops over short reads, stops after reading the overflow-detection byte, and never buffers the remaining input. This preserves the 4,096-byte contract without relying on one read call's behavior.

## 5. Exact byte-limit boundary

**Hypothesis.** A valid JSON document padded with legal JSON whitespace to exactly 4,096 bytes should be processed normally; an otherwise identical 4,097-byte input should return the one malformed response. Both should have empty stderr.

**Experiment.** Exact command:

```bash
PYTHONPATH=src python3 -c 'import json,subprocess
document={"principal":{"subject_id":"a","tenant_id":"t","role":"member"},"action":"read","resource":{"resource_id":"r","tenant_id":"t","owner_id":"a"}}
raw=json.dumps(document,separators=(",", ":")).encode("utf-8")
for size in (4096,4097):
    completed=subprocess.run(["/bin/python3","-m","authz"],input=raw+b" "*(size-len(raw)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={"PYTHONPATH":"src"},timeout=3,check=False,start_new_session=True)
    print(size,completed.returncode,completed.stdout.decode("ascii").strip(),repr(completed.stderr))'
```

Observed, harness exit 0:

```text
4096 0 {"allowed":true,"reason":"allow_owner"} b''
4097 2 {"error":"invalid_input"} b''
```

**Conclusion/change.** The exact boundary matched the contract and direct parser test. This experiment supplied process-level evidence that the byte limit, response, status, and stderr behavior compose correctly.

## 6. Final regression and compatibility check

**Hypothesis.** The final implementation and new bounded-read tests should pass both the mandated workspace interpreter and the separately available Python 3.11 interpreter.

**Experiments.** Exact commands:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s tests -v
```

**Observation.** Both commands exited 0 and reported:

```text
Ran 23 tests
OK
```

The 23 discovered methods include one table-driven method that itself checks all 36 finite policy combinations, plus invariant, parser, bounded-read, and subprocess cases.

**Conclusion.** No known failing check remained at handoff. This is learner-captured local evidence, not independent validation or evidence beyond this kickoff unit.
