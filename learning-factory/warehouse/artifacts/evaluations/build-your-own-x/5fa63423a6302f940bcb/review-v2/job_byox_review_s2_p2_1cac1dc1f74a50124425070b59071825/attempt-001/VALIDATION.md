# Independent validation record

Review date: 2026-09-03  
Candidate: CANDIDATE/ (kept immutable)  
Project: project_a39dec7bd5caf7524c0e9df3e14a2c8b  
Builder job: job_byox_build_s2_f8c33d02dd9481f2eaed146a0d7edd33

All builds ran against a scratch copy. Candidate content was hashed before and after testing.

## Tool identity

~~~sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version
/usr/bin/timeout --version
~~~

Observed first lines:

~~~text
gcc (GCC) 15.2.0
Python 3.11.5
GNU Make 4.2.1
timeout (GNU coreutils) 8.30
~~~

GCC and Python were invoked by absolute path from configured read-only toolchain roots. Make and timeout were host utilities.

## Immutability and structure

~~~sh
find CANDIDATE -type f -print0 | sort -z |
  xargs -0 /usr/bin/sha256sum | /usr/bin/sha256sum
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/audit_pack.py CANDIDATE
find CANDIDATE ! -type d ! -type f -print
~~~

Observed before and after all tests:

~~~text
1aee76bbf7bd57e2c7f08fc11fa67bba8e44ebe5ded25ff58390e8de2ff73e46  -
pack audit: PASS (23 required files, 21 forbidden paths absent, 50 text files scanned)
non-regular entry count: 0
~~~

An independent JSON check confirmed consistent project ID, source ID, source commit, snapshot link, CC0 catalog license, NOASSERTION linked-resource license, and linked_content_copied=false. It observed:

~~~text
canonical provenance sha256=1bfdb2c3fd69ba8b002ae897ba75fc03684b636e83ee1541aaefb3eeaff8ce7e
PROVENANCE.json file sha256=db099025b423f3c701e4ea26ef35bddacc94bf7be3320f90cf5a45bdf8d0cce0
metadata consistency: PASS
~~~

Those local checks cannot authenticate the unavailable upstream snapshot.

## Scratch setup

~~~sh
test ! -e .review-work
mkdir .review-work
cp -a CANDIDATE/. .review-work/
chmod -R u+w .review-work
~~~

The first build attempt, before chmod, exited 2 because the copy preserved the review submission's 0555 directories and GCC could not create an object file. Only the scratch copy was made writable; all reported build results below are the rerun.

## Starter baseline

~~~sh
/usr/bin/timeout --signal=KILL 30s /usr/bin/make \
  -C .review-work/starter clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
~~~

Observed: exit 0; all four translation units compiled and linked.

~~~sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
MAKE=/usr/bin/make \
/usr/bin/timeout --signal=KILL 30s \
  .review-work/public_tests/run.sh .review-work/starter
~~~

Observed: exit 1 with 15 public core checks failed. This is the documented deliberately incomplete baseline.

## Reference suites

~~~sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
MAKE=/usr/bin/make \
/usr/bin/timeout --signal=KILL 45s \
  .review-work/public_tests/run.sh .review-work/sealed/reference
~~~

Observed: exit 0.

~~~text
public core tests: PASS
public CLI tests: PASS
~~~

~~~sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
MAKE=/usr/bin/make \
/usr/bin/timeout --signal=KILL 60s \
  .review-work/sealed/reference_tests/run.sh \
  .review-work/sealed/reference
~~~

Observed: exit 0.

~~~text
sealed reference unit tests: PASS
sealed CLI tests: PASS
sealed PTY test: PASS
~~~

This independently reproduces the finite suite outcomes, including its 220-pipeline low-descriptor case and one PTY Ctrl-C path. It does not make those builder-owned tests exhaustive or assign a validation label.

## Reviewer-authored behavior checks

A reviewer-authored inline Python program invoked the scratch minish through subprocess argv arrays with a five-second timeout per case. It made 12 assertions covering:

- last-stage pipeline status in both success/failure orders;
- quoted empty arguments, quoted operator bytes, and comment boundaries;
- syntax-error recovery;
- 128-plus-signal status mapping;
- acceptance of exactly 4096 bytes and rejection of 4097;
- input-redirection precedence plus truncate/append;
- cd using HOME;
- exit using the last completed status;
- background notification containing a numeric process-group ID; and
- no prompt in noninteractive mode.

Invocation:

~~~sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c '
import os, pathlib, re, subprocess, tempfile
binary = pathlib.Path(".review-work/sealed/reference/minish").resolve()
checks = 0
def invoke(script, env=None):
    return subprocess.run(
        [str(binary)], input=script, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=5, check=False, env=env,
    )
def require(condition, detail):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(detail)
r = invoke("/bin/false | /bin/true\n")
require(r.returncode == 0, ("last-success", r.returncode, r.stderr))
r = invoke("/bin/true | /bin/false\n")
require(r.returncode == 1, ("last-failure", r.returncode, r.stderr))
r = invoke(
    "/usr/bin/printf \"<%s><%s>\" \"a b\" \"\" # ignored\n"
    "/usr/bin/printf %s a#b\n"
)
require(
    r.returncode == 0 and r.stdout == "<a b><>a#b",
    ("lexical-boundaries", r.returncode, r.stdout, r.stderr),
)
r = invoke("/usr/bin/printf broken |\n/bin/true\n")
require(
    r.returncode == 0 and "syntax" in r.stderr.lower(),
    ("syntax-recovery", r.returncode, r.stderr),
)
r = invoke(
    "/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 "
    "-c \"import os,signal;os.kill(os.getpid(),signal.SIGTERM)\"\n"
)
require(r.returncode == 143, ("signal-status", r.returncode, r.stderr))
accepted = "/bin/true" + " " * (4096 - len("/bin/true") - 1) + "\n"
r = invoke(accepted)
require(r.returncode == 0, ("4096-byte-line", r.returncode, r.stderr))
oversized = "/bin/true" + " " * (4097 - len("/bin/true") - 1) + "\n"
r = invoke(oversized)
require(
    r.returncode == 2 and "exceeds 4096" in r.stderr,
    ("4097-byte-line", r.returncode, r.stderr),
)
with tempfile.TemporaryDirectory(prefix="review-minish-") as directory:
    target = pathlib.Path(directory) / "out"
    r = invoke(
        f"/usr/bin/printf ignored | /bin/cat < /dev/null\n"
        f"/usr/bin/printf a > {target}\n"
        f"/usr/bin/printf b >> {target}\n"
        f"/bin/cat < {target}\n"
    )
    require(
        r.returncode == 0 and r.stdout == "ab",
        ("redir-precedence-append", r.returncode, r.stdout, r.stderr),
    )
    env = os.environ.copy()
    env["HOME"] = directory
    r = invoke("cd\n/bin/pwd\n", env)
    require(
        r.returncode == 0 and r.stdout.strip() == directory,
        ("cd-home", r.returncode, r.stdout, r.stderr),
    )
r = invoke("/bin/false\nexit\n")
require(r.returncode == 1, ("exit-last-status", r.returncode, r.stderr))
r = invoke("/bin/true &\n")
require(
    r.returncode == 0
    and re.search(r"\[background [0-9]+\]", r.stderr) is not None,
    ("background-notice", r.returncode, r.stderr),
)
require(
    "minish$" not in r.stdout and "minish$" not in r.stderr,
    ("noninteractive-prompt", r.stdout, r.stderr),
)
print(f"reviewer edge checks: PASS ({checks} assertions)")
'
~~~

Observed:

~~~text
reviewer edge checks: PASS (12 assertions)
exit 0
~~~

An initial draft of this reviewer program failed because its printf format contained unquoted angle brackets, which minish correctly parsed as redirection. After quoting that format, the program above passed; the discarded result was a test-authoring error, not candidate evidence.

## Independently reproduced defect

The following reviewer probe launches minish with inherited fd 1 closed, then requests an explicit output redirection:

~~~sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c '
import os, pathlib, subprocess, tempfile
b = pathlib.Path(".review-work/sealed/reference/minish").resolve()
with tempfile.TemporaryDirectory(prefix="review-fd-edge-") as d:
    target = pathlib.Path(d) / "out"
    r = subprocess.run(
        [str(b)],
        input=f"/usr/bin/printf payload > {target}\n",
        text=True,
        stdout=None,
        stderr=subprocess.PIPE,
        timeout=5,
        check=False,
        preexec_fn=lambda: os.close(1),
    )
    print(r.returncode, target.stat().st_size, repr(r.stderr))
'
~~~

Observed:

~~~text
exit=1
target size=0
stderr='/usr/bin/printf: write error: Bad file descriptor\n'
~~~

Inspection explains the result: open returns fd 1, dup2(1, 1) is a no-op, and the implementation then closes fd 1. This is a candidate defect, not an environmental limitation.

## Sanitizers

~~~sh
/usr/bin/timeout --signal=KILL 30s \
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c17 -D_POSIX_C_SOURCE=200809L \
  -Wall -Wextra -Wpedantic -Werror -O1 -g \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I.review-work/sealed/reference/include \
  .review-work/sealed/reference_tests/test_reference.c \
  .review-work/sealed/reference/src/lexer.c \
  .review-work/sealed/reference/src/parser.c \
  .review-work/sealed/reference/src/execute.c \
  -o .review-work/.review-san/test_reference
~~~

Observed compile exit: 0.

~~~sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1 \
/usr/bin/timeout --signal=KILL 30s \
  .review-work/.review-san/test_reference
~~~

Observed: exit 0, sealed unit PASS, and no ASan/UBSan diagnostic.

~~~sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1 \
/usr/bin/timeout --signal=KILL 30s \
  .review-work/.review-san/test_reference
~~~

Observed: exit 1.

~~~text
LeakSanitizer has encountered a fatal error.
LeakSanitizer does not work under ptrace (strace, gdb, etc)
~~~

Leak checking is therefore inconclusive.

## Focused static analysis

~~~sh
/usr/bin/timeout --signal=KILL 30s \
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c17 -D_POSIX_C_SOURCE=200809L \
  -Wall -Wextra -Wpedantic -fanalyzer \
  -Werror=analyzer-fd-double-close -Wno-analyzer-fd-leak \
  -O0 -g -I.review-work/sealed/reference/include \
  .review-work/sealed/reference/src/main.c \
  .review-work/sealed/reference/src/lexer.c \
  .review-work/sealed/reference/src/parser.c \
  .review-work/sealed/reference/src/execute.c \
  -o .review-work/.review-san/minish-analyzed
~~~

Observed: exit 1. GCC traced the EINTR branch in close_checked from the first close to a second close and emitted analyzer-fd-double-close. A separate source scan found no system(), popen(), or /bin/sh -c execution pattern.

## Limitations and label discipline

- Upstream content was unavailable, so catalog/source hashes and the independent-authorship assertion were checked only for internal consistency.
- LeakSanitizer was blocked by the ptrace environment.
- No fuzz, benchmark, coverage threshold, deterministic failure injection, broad PTY matrix, or long-duration concurrency campaign was run.
- The Java, Node, Go, ARM, QEMU, NASM, flex, and bison roots were unrelated to this POSIX C artifact and were not exercised.
- The sealed directory layout was inspected, but the orchestrator's actual student-view filter was unavailable.
- Nothing in this record promotes BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED. Only an orchestrator-captured acceptance validator can publish REVIEWED.
