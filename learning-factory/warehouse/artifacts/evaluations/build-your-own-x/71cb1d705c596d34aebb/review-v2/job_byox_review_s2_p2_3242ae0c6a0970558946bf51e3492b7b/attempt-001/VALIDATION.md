# Independent validation record

Review date: 2026-09-03 (America/Chicago)  
Review workspace:

    /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_3242ae0c6a0970558946bf51e3492b7b/attempt-001

CANDIDATE was treated as immutable. All compilation and executable testing used this separate scratch copy:

    /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_3242ae0c6a0970558946bf51e3492b7b/attempt-001/.review-scratch.DEkdF9

The recurring /usr/bin/id warnings about unmapped numeric user/group IDs came from the managed execution wrapper and did not change command exit statuses.

## Tool identity

Commands:

~~~sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version | sed -n '1p'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version | sed -n '1p'
~~~

Observed:

~~~text
gcc (GCC) 15.2.0
Python 3.11.5
GNU Make 4.2.1
~~~

The other configured cross, Java, Node, Go, QEMU, assembler, parser-generator, and GLib roots were not relevant to this native C/Python project and were not invoked.

## Immutable inventory and package checks

Commands:

~~~sh
find CANDIDATE -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
find CANDIDATE -type l -print
find CANDIDATE -xdev ! -type d ! -type f ! -type l -print
find CANDIDATE -type f -print0 | LC_ALL=C sort -z | xargs -0 wc -l
PYTHONDONTWRITEBYTECODE=1 /bin/sh CANDIDATE/environment/check.sh
PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/audit.py
~~~

Observed:

- 41 regular files, no symlink, and no special non-directory entry.
- Aggregate digest before testing: 076abc6af3de93b50a3a95bee319845ba35c2198f401b36aaa2f93638b664383.
- The environment check exited 0 and printed GCC 15.2.0, Python 3.11.5, and “environment prerequisites present.”
- The candidate-authored audit exited 0:

~~~text
required files: 23 present
forbidden paths: 0 present
generated entries audited: 56
regular files scanned for credential patterns: 41
metadata: strict JSON; manifest object exact; provenance binding consistent
~~~

That audit was not treated as independent proof. The inventory, type checks, metadata parse, digest calculation, and pattern searches were also performed directly.

## Builds in the scratch copy

Setup:

~~~sh
mktemp -d -p "$PWD" .review-scratch.XXXXXX
cp -R CANDIDATE/. .review-scratch.DEkdF9/
~~~

The first build attempt returned 2 because copying preserved the review artifact's immutable 0444/0555 modes; GCC reported “Cannot create temporary file in ./: Permission denied.” This was a scratch-setup property, not a source compilation result. Only the scratch copy was made writable:

~~~sh
chmod -R u+w .review-scratch.DEkdF9
TMPDIR="$PWD/.review-scratch.DEkdF9" \
  /usr/bin/make -C .review-scratch.DEkdF9/starter clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
TMPDIR="$PWD/.review-scratch.DEkdF9" \
  /usr/bin/make -C .review-scratch.DEkdF9/sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
~~~

Both commands then exited 0. Compilation used:

~~~text
-D_POSIX_C_SOURCE=200809L -Iinclude
-std=c11 -Wall -Wextra -Wpedantic -Werror -g
~~~

No compiler warning was emitted.

An additional static analyzer compile also exited 0 with no diagnostic:

~~~sh
TMPDIR="$PWD/.tmp" \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -D_POSIX_C_SOURCE=200809L -Isealed/reference/include \
  -std=c11 -Wall -Wextra -Wpedantic -Werror -fanalyzer \
  -c sealed/reference/src/msh.c -o .tmp/msh-analyzer.o
~~~

That command ran from the scratch root.

## Submitted test suites

Commands, run from the scratch root:

~~~sh
mkdir -p .tmp
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  public_tests/test_shell.py
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/test_reference.py
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  adversarial/test_boundaries.py
~~~

Observed exit status was 0 for each:

~~~text
Ran 9 tests in 0.047s
OK
Ran 12 tests in 0.428s
OK
Ran 4 tests in 0.045s
OK
~~~

The PTY test ran and did not skip.

The public suite was also run against the starter:

~~~sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" \
  MSH_BIN="$PWD/starter/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  public_tests/test_shell.py
~~~

Observed exit status: 1. It ran 9 tests, passing blank-line and syntax-no-launch checks and failing the other 7. This matches the disclosed execution TODO; it is not evidence of a completed learner solution.

## Additional ordinary-environment contract matrix

A self-contained assertion-only Python here-document was launched with:

~~~sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
# The harness used subprocess argv arrays, per-call timeouts of 3 or 4 seconds,
# TemporaryDirectory under TMPDIR, and explicit assertions for the matrix below.
PY
~~~

The 25 passing assertions covered:

- three invalid invocation shapes returning 2;
- byte quoting, escaping, empty/literal operator behavior;
- seven malformed inputs returning 2, containing syntax:, and launching no marker command;
- last-stage pipeline and signal status mapping;
- 126 permission error and 127 not-found behavior;
- 0666 output creation filtered to 0640 by umask 0027;
- EOF delivery through a 41-stage pipeline;
- parent versus child contexts for cd and exit;
- missing HOME, prior-status exit, invalid exit continuation;
- parent built-in input/output redirection restoration;
- monotonic ordered job IDs, default fg selection, and invalid fg continuation; and
- two pipeline children having one new PGID equal to the first child PID.

Final observed output:

~~~text
independent contract checks: 25 passed
~~~

The first version of this reviewer-authored matrix used equal 0.3-second background jobs and incorrectly expected job 1 to remain available after waiting for job 2. It exited 1 because job 1 legitimately completed and was removed at the next safe point. Durations were corrected to 0.8 and 0.2 seconds, after which the complete matrix passed. That initial assertion was not counted as a candidate defect.

## Focused contract-failure probes

After restoring the normal build, this exact bounded probe ran from the scratch root:

~~~sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import os
from pathlib import Path
import signal
import subprocess
import tempfile

binary = os.environ["MSH_BIN"]

result = subprocess.run(
    [binary, "-c", "printf '<%s>\\n' a\rb"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3, check=False,
)
print("CR_WORD", result.returncode, result.stdout.hex(),
      result.stderr.decode(errors="replace").strip())

def close_stdin():
    os.close(0)

def close_stdout():
    os.close(1)

def ignore_sigchld():
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

with tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"]) as directory:
    root = Path(directory)
    source = root / "input"
    source.write_text("payload\n")
    result = subprocess.run(
        [binary, "-c", f"cat < {source}"], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        preexec_fn=close_stdin, timeout=3, check=False,
    )
    print("CLOSED_STDIN_REDIR", result.returncode, repr(result.stdout),
          "Bad file descriptor" in result.stderr)

    target = root / "output"
    result = subprocess.run(
        [binary, "-c", f"printf payload > {target}"], text=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        preexec_fn=close_stdout, timeout=3, check=False,
    )
    print("CLOSED_STDOUT_REDIR", result.returncode,
          repr(target.read_text()), "Bad file descriptor" in result.stderr)

result = subprocess.run(
    [binary, "-c", "/bin/sh -c 'exit 7'"], text=True,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    preexec_fn=ignore_sigchld, timeout=3, check=False,
)
print("IGNORED_SIGCHLD_STATUS", result.returncode, repr(result.stderr))

result = subprocess.run(
    [binary, "-c", "exit ' 7'"], text=True,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3, check=False,
)
print("LEADING_SPACE_EXIT", result.returncode, repr(result.stderr))
PY
~~~

Observed exit status of the probe harness: 0. Its observations were:

~~~text
CR_WORD 0 3c613e0a3c623e0a
CLOSED_STDIN_REDIR 1 '' True
CLOSED_STDOUT_REDIR 1 '' True
IGNORED_SIGCHLD_STATUS 0 ''
LEADING_SPACE_EXIT 7 ''
~~~

Interpretation:

- Hex 3c613e0a3c623e0a is <a> newline <b> newline. The specified grammar instead requires one argument containing carriage return, which would produce hex 3c610d623e0a.
- Both closed-standard-descriptor redirections should have succeeded but failed with EBADF.
- The inherited-SIGCHLD case should have propagated 7 but returned 0.
- The documented decimal operand grammar does not include a quoted leading blank, but that operand was accepted.

## Sanitizers and disclosed runtime limitations

Instrumented build:

~~~sh
TMPDIR="$PWD/.tmp" /usr/bin/make -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
~~~

Observed exit status: 0.

Without a runtime path:

~~~sh
./sealed/reference/msh -c true
~~~

Observed exit status 127 and the disclosed libasan.so.8 loader failure.

The three suites were then rerun with the same commands as the normal runs plus:

~~~sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
UBSAN_OPTIONS=halt_on_error=1
~~~

Observed exit status was 0 for each, no sanitizer diagnostic, and:

~~~text
Ran 9 tests in 0.310s
OK
Ran 12 tests in 0.797s
OK
Ran 4 tests in 0.453s
OK
~~~

Leak detection probe:

~~~sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
  UBSAN_OPTIONS=halt_on_error=1 \
  ./sealed/reference/msh -c true
~~~

Observed exit status: 1.

~~~text
LeakSanitizer has encountered a fatal error.
HINT: LeakSanitizer does not work under ptrace (strace, gdb, etc)
~~~

This independently confirms the candidate's stated LeakSanitizer limitation. It is not a leak pass.

## Metadata, license boundary, and disclosure structure

Independent strict-JSON parsing checked project ID, source ID, and commit equality across the two metadata files. It observed:

~~~text
project_id_match: True
source_id_match: True
source_commit_match: True
manifest_to_snapshot_value_match: True
manifest_to_provenance_file_digest_match: False
conservative_labels: True
linked_license_unasserted: True
actual_provenance_file_sha256: 8aa702b8b64241bda70f3a63e3d1b9a681e7dc87f4d5930b9b4f764f584e5dad
~~~

The candidate's value 5cf87366... is therefore an internally matched snapshot value, not a digest of the provenance document. The source material needed to recompute snapshot_sha256, material_baseline_sha256, content_sha256, and the CC0 evidence was unavailable. The upstream URL was deliberately not fetched.

Commands used for static leakage and credential-pattern review:

~~~sh
find CANDIDATE -mindepth 1 -maxdepth 1 -printf '%f %y\n' | LC_ALL=C sort
grep -RInE --exclude='VALIDATION.md' --exclude='audit.py' \
  '(api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd|private[_-]?key)[[:space:]]*[:=]|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|https?://[^/[:space:]@:]+:[^@[:space:]/]+@' \
  CANDIDATE
grep -RInE 'https?://' CANDIDATE
grep -RInE \
  '(sealed/reference|sealed/reference_tests|sealed/debugging|sealed/review_exercises)' \
  CANDIDATE/starter CANDIDATE/public_tests CANDIDATE/README.md \
  CANDIDATE/REQUIREMENTS.md CANDIDATE/CONCEPTS.md \
  CANDIDATE/DESIGN_QUESTIONS.md CANDIDATE/AGENTS.md
~~~

Observed:

- no credential-pattern hit;
- one URL, the declared GitHub upstream reference in PROVENANCE.json; and
- no named sealed implementation/test/answer path in learner-facing roots.

This establishes static separation only. The factory's actual student-view projection was outside this workspace and remains an external control.

## Test-harness source inspection

The PTY test was read with numbered lines:

~~~sh
nl -ba CANDIDATE/sealed/reference_tests/test_reference.py | sed -n '130,192p'
~~~

Observed:

- read_until uses a monotonic deadline and select;
- after the expected one-second read timeout, lines 178-180 call blocking waitpid(child, 0);
- the ordinary exit path also calls blocking waitpid at line 169; and
- final cleanup kills child, the shell PID, rather than a created process group.

Thus successful reference execution was bounded in practice, but the test's failure behavior is not deterministically bounded and its descendant cleanup is incomplete.

The public suite defines nine tests. Its sole jobs use is an empty jobs command for descriptor restoration; background launch, job states/IDs, fg, and terminal control appear only in sealed tests.

## Final immutability check and unclaimed work

The candidate aggregate digest was recomputed after all review work and remained:

~~~text
076abc6af3de93b50a3a95bee319845ba35c2198f401b36aaa2f93638b664383
~~~

No candidate file was changed. No benchmark was run, no coverage-guided fuzzing was performed, no network source was fetched, and no portability or production-readiness label was inferred.

After recording the results, the explicitly validated .review-scratch.DEkdF9 directory and its build products were deleted with find -depth -delete. The three review artifacts and immutable CANDIDATE are the only retained task material.
