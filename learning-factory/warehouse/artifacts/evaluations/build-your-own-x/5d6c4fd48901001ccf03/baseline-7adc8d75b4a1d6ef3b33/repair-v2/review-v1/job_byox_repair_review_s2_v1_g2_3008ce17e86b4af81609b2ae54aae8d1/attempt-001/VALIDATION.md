# Independent validation

Review date: 2026-09-02. CANDIDATE was treated as immutable. Commands in this record were run from
CANDIDATE unless noted; temporary output was placed in the sibling .review-tmp and .review-export
directories and removed after inspection.

## Toolchain and host

    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import sys; print(sys.executable); print(sys.version.split()[0])'
    /usr/bin/unshare --version

All exited 0. Observed:

    Python 3.11.5
    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
    3.11.5
    unshare from util-linux 2.32.1

The bounded host probe was:

    /usr/bin/timeout --signal=KILL 15 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/check_host.py

It exited 0 and printed:

    {"linux": true, "probe_exit_code": 0, "python": "3.11.5", "unshare_path": "/usr/bin/unshare", "user_namespace_probe": "AVAILABLE"}

Python was the only configured language toolchain relevant to this Python-only pack. The listed
Java, ARM compilers, QEMU, Node, Go, NASM, GCC/binutils, flex, bison, and glib roots were not needed
and were not used. No relevant configured toolchain was unavailable. rg and git were absent from
PATH, so inspection used find, grep, sed, hashes, and Python.

## Deterministic replay

A workspace-local scratch directory was created first:

    mkdir ../.review-tmp

The core commands were:

    /usr/bin/timeout --signal=KILL 60 /usr/bin/env TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
    /usr/bin/timeout --signal=KILL 60 /usr/bin/env TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.checkpoints -v
    /usr/bin/timeout --signal=KILL 60 /usr/bin/env TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.checkpoints -v
    /usr/bin/timeout --signal=KILL 60 /usr/bin/env TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
    /usr/bin/timeout --signal=KILL 60 /usr/bin/env TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s adversarial -v

Observed results:

| Check | Exit | Result |
|---|---:|---|
| Public discovery | 0 | 10 tests, OK |
| Untouched-starter checkpoints | 1 | 4 tests: 1 expected failure, 3 expected NotImplementedError errors |
| Reference checkpoints | 0 | 4 tests, OK |
| Sealed reference discovery | 0 | 38 tests, OK; 2 Linux tests skipped because opt-in was unset |
| Adversarial discovery | 0 | 4 tests, OK |

Pack and syntax checks:

    /usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_pack.py
    /usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import ast,pathlib; roots=(pathlib.Path("starter"),pathlib.Path("public_tests"),pathlib.Path("environment"),pathlib.Path("sealed"),pathlib.Path("adversarial"),pathlib.Path("debugging"),pathlib.Path("review_exercises"),pathlib.Path("benchmarks")); files=sorted(p for root in roots for p in root.rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"),filename=str(p)) for p in files]; print(f"AST_OK: {len(files)} Python files")'
    /usr/bin/sha256sum PROVENANCE.json
    /usr/bin/sha256sum -c environment/PROVENANCE.sha256

All exited 0. The verifier reported 70 canonical source files; syntax output was
AST_OK: 42 Python files. The provenance digest was
1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611 and the declaration checked OK.

## Export and progressive disclosure

    /usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/export_views.py create "$PWD/../.review-export"
    /usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/export_views.py verify "$PWD/../.review-export/learner" --role learner
    /usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/export_views.py verify "$PWD/../.review-export/instructor" --role instructor

All exited 0. Creation and verification agreed on:

    {"files": 27, "manifest_sha256": "39b2ea17760f674f2a3749df51d48bff8f42b3342b25c0dbd2bb8a37475b1ab7", "role": "learner"}
    {"files": 70, "manifest_sha256": "bd42353e73f14ae9f1c8c7865978ea188f4ea23f066a5d46a6ce77c731a8b2cd", "role": "instructor"}

Both exported verify_pack.py programs exited 0 and reported 28 learner and 71 instructor canonical
files respectively, including each generated view manifest. The exported learner public suite ran
10 tests and passed.

An independent hashlib/json recomputation, not the candidate verifier, compared every declared
learner file path, size, and SHA-256 and every directory:

    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import hashlib,json,pathlib,sys; v=pathlib.Path(sys.argv[1]); m=json.loads((v/"environment/VIEW_MANIFEST.json").read_text()); actual={p.relative_to(v).as_posix():(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in v.rglob("*") if p.is_file() and p.relative_to(v).as_posix() != "environment/VIEW_MANIFEST.json"}; declared={x["path"]:(x["size"],x["sha256"]) for x in m["files"]}; dirs=sorted(p.relative_to(v).as_posix() for p in v.rglob("*") if p.is_dir()); print(json.dumps({"actual_files":len(actual),"declared_files":len(declared),"files_match":actual==declared,"directories_match":dirs==m["directories"],"role":m["role"]},sort_keys=True)); raise SystemExit(0 if actual==declared and dirs==m["directories"] else 1)' "$PWD/../.review-export/learner"

It exited 0:

    {"actual_files": 27, "declared_files": 27, "directories_match": true, "files_match": true, "role": "learner"}

Direct top-level inventory printed exactly:

    AGENTS.md
    CONCEPTS.md
    DESIGN_QUESTIONS.md
    MANIFEST.yaml
    README.md
    REQUIREMENTS.md
    environment
    public_tests
    starter

A direct search found no learner directory named sealed, adversarial, debugging, review_exercises,
benchmarks, reference, reference_tests, hidden_tests, solution, solutions, or answers.

## Kernel and supervision probes

The opt-in disposable-rootfs suite was:

    /usr/bin/timeout --signal=KILL 45 /usr/bin/env MINICTR_LINUX_INTEGRATION=1 TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest sealed.reference_tests.test_linux_integration -v

It exited 0: both tests passed in 0.602 seconds. A separate setup-only probe copied /bin/true and its
two runtime libraries into workspace scratch, then called build_preflight_plan and Runner. It
returned:

    {"actionable_unsupported": true, "exit_code": 69, "supported": false, "timed_out": false}

Thus this host rejected the default read-only remount before workload launch. This is a capability
limitation, not evidence that read-only execution succeeded.

An actual process probe used Runner on a Python program that forked and slept:

    /usr/bin/timeout --signal=KILL 10 /usr/bin/env TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json,signal,sys,time; from minictr.planner import LaunchPlan; from minictr.runner import Runner; p=LaunchPlan((sys.executable,"-B","-c","import os,time; os.fork(); print(1,flush=True); time.sleep(30)"),(("LANG","C"),),0.2); started=time.monotonic(); r=Runner().run(p,b"{}"); print(json.dumps({"elapsed_lt_5s":time.monotonic()-started<5,"exit_code":r.exit_code,"stdout_lines":len(r.stdout.splitlines()),"timed_out":r.timed_out},sort_keys=True)); raise SystemExit(0 if r.timed_out and r.exit_code == -signal.SIGKILL else 1)'

It exited 0:

    {"elapsed_lt_5s": true, "exit_code": -9, "stdout_lines": 2, "timed_out": true}

A bounded two-thread probe opened separate Registry connections and synchronized simultaneous
claim_start calls. It exited 0 with one claimed and one rejected outcome, both threads stopped, and
one durable winning PID.

## Reviewer counterexamples

The transition trigger was tested after adding an ordinary policy row:

    /usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import os,tempfile; from pathlib import Path; from minictr.registry import Registry; from minictr.spec import ContainerSpec; t=tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"]); r=Registry(Path(t.name)/"state.sqlite3"); s=ContainerSpec.from_mapping({"id":"bypass","rootfs":"/tmp/root","command":["/bin/true"]}); r.create(s,"2026-01-01T00:00:00Z"); r.connection.execute("INSERT INTO allowed_transitions(old_state,new_state) VALUES (?,?)",("CREATED","EXITED")); r.connection.execute("UPDATE containers SET state=? WHERE id=?",("EXITED","bypass")); print(r.get("bypass").state); r.close(); t.cleanup()'

It exited 0 and printed EXITED, demonstrating acceptance of the forbidden CREATED-to-EXITED
transition.

The public filesystem boundary returned an unstable exception:

    /usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'from minictr.paths import validate_rootfs; validate_rootfs(".")'

It exited 1 with AttributeError: 'str' object has no attribute 'is_absolute', rather than
ValidationError.

The bounded JSON path was given 2,000 nested arrays and a process factory that would raise
AssertionError if reached:

    /usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'from minictr.planner import LaunchPlan; from minictr.runner import Runner; Runner(popen_factory=lambda *_a,**_kw: (_ for _ in ()).throw(AssertionError("launcher reached"))).run(LaunchPlan(("/bin/false",),(("LANG","C"),),1.0),("["*2000+"]"*2000).encode())'

It exited 1 with RecursionError from json.loads; the launcher assertion was not reached.

A Registry create using 2026-01-02T03:04:60Z exited 0 and returned a CREATED record, showing that an
impossible UTC leap-second timestamp is accepted.

Finally, the validation record's heredoc environment pattern was replayed:

    /usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/../.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
    print("not reached")
    PY

It exited 1 before Python:

    /bin/bash: cannot create temp file for here-document: Read-only file system

TMPDIR is applied to the child command, too late for the invoking Bash process that materializes the
heredoc.

## Immutability and limitations

Before and after all checks:

    /usr/bin/find . -type f -print0 | /usr/bin/sort -z | /usr/bin/xargs -0 /usr/bin/sha256sum | /usr/bin/sha256sum

printed:

    593e40fc2af6449f3d2e0a31d3ff982f7b486fb658f900f9da55e91c80381413  -

There were 70 regular files, no symlinks, and no __pycache__, .pyc, or .pyo entries.

The immutable catalog baseline and linked upstream repository were unavailable, so provenance and
license assertions could be checked only for internal consistency and explicit boundaries. No
fuzzing, controlled benchmark, transfer verification, hostile-workload validation, or production
assessment was performed or inferred.
