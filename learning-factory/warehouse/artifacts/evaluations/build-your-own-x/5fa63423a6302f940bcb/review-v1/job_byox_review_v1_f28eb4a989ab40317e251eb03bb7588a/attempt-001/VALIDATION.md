# Independent validation record

Review date: 2026-08-31 (`America/Chicago`). Commands were run from the review workspace root unless a
different directory is shown. `CANDIDATE/` was never edited: builds and runtime checks used
`.review-work/candidate`, made by `cp -a`, and that disposable copy was removed afterward.

The command runner prefixed many commands with identity lookup warnings for numeric UID 532319 and GID
500275. Those warnings came from the runner, not from candidate code.

## Host tools

```sh
cc --version | sed -n '1,2p'
make --version | sed -n '1,2p'
python3 --version
```

Observed: GCC 8.5.0, GNU Make 4.2.1, and Python 3.6.8. `timeout`, GNU/procps `ps`, and the standard
fixture utilities were present. `rg` was unavailable, so bounded `find`, `grep`, `sed`, `awk`, and
`nl` inspection was used instead.

## Immutability, structure, and metadata

Before and after all review work:

```sh
LC_ALL=C find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
find CANDIDATE -type f | wc -l
```

Observed both times:

```text
3cb91203c1dcea839ca03804994da38cd9692fdb7928b6462b4e9444f0e1df2c  -
62
```

There were no symlinks or special files and no group/other-writable candidate files. An independent
JSON/link check observed exact manifest keys, `GENERATED`/`PARTIAL`, `productionized: false`,
`independent_validation: REQUIRED`, ten resolvable local Markdown links, and no broken local link. The
canonical digest computed from parsed, sorted compact `PROVENANCE.json` was:

```text
0343524004b914e47b5ad2522b50dedc30016985a996823676752128998bf4d9
```

The submitted integrity script was also run from the clean copy:

```sh
timeout 15s python3 sealed/reference_tests/audit_pack.py
```

Exit status: 0. It reported `pack audit: PASS`, 23 required files, 0 forbidden paths, 6 locally sealed
exercise answers, 0 symlinks/special files, and 62 credential-scanned files. This is a
candidate-authored structural check, not independent functional evidence. A separate read check found
23 readable files under solution-bearing `sealed` paths; no rendered student view was available.

## Starter boundary

From the disposable copy:

```sh
timeout 30s make -C starter clean all check
```

Exit status: 0. All three starter translation units compiled with
`-std=c11 -Wall -Wextra -Wpedantic -Werror -g`; output ended with:

```text
baseline parser contract: PASS
```

The intentionally later milestone check was run separately:

```sh
timeout 30s make -C starter check-milestones
```

Exit status: 2. The test executable ran and reported exactly `17 milestone assertion(s) failed`.
These failures match the documented incomplete starter boundary and are not treated as an unexpected
regression.

## Sealed reference and submitted tests

```sh
timeout 45s make -C sealed/reference clean all
timeout 90s make -C sealed/reference_tests test
timeout 45s make -C public_tests cli SHELL_UNDER_TEST=../sealed/reference/byosh
```

Observed exit statuses: 0, 0, 0. The reference compiled with
`-D_POSIX_C_SOURCE=200809L -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -g`. The private suite result
was:

```text
Ran 32 tests in 3.336s
OK
```

No test was skipped. The public harness ended with `completed-shell public smoke tests: PASS`.

For completeness, an earlier reviewer invocation explicitly overrode `SHELL_UNDER_TEST` with the
relative value `../reference/byosh`. Twenty-nine tests passed and three cwd-changing tests errored with
`FileNotFoundError`. This was reviewer misuse, not a candidate defect: the README asks for an absolute
override, and the Makefile's default uses `$(abspath ../reference/byosh)`. The exact default command
above subsequently passed all 32 cases.

## Exercise compilation

The three intentionally faulty debugging programs were compiled but not executed, and the three
review excerpts were compiled without linking:

```sh
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror debugging/exercise_01_pipe_eof/buggy.c -o ../exercise-build/debug_01
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror debugging/exercise_02_wait_status/buggy.c -o ../exercise-build/debug_02
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror debugging/exercise_03_sigchld_race/buggy.c -o ../exercise-build/debug_03
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -c review_exercises/exercise_01_parser_ownership/candidate.c -o ../exercise-build/review_01.o
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -c review_exercises/exercise_02_terminal_handoff/candidate.c -o ../exercise-build/review_02.o
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -c review_exercises/exercise_03_builtin_context/candidate.c -o ../exercise-build/review_03.o
```

All six commands exited 0 with no compiler diagnostics.

## Independent failing probe: ENOEXEC host-shell fallback

From the disposable candidate copy after building the reference:

```sh
timeout 15s python3 - <<'PY'
import os, pathlib, subprocess, tempfile
shell = os.path.abspath('sealed/reference/byosh')
with tempfile.TemporaryDirectory(prefix='review-enoexec-') as directory:
    fixture = pathlib.Path(directory) / 'plain-executable'
    fixture.write_text("printf 'HOST_SHELL_FALLBACK\\n'\n")
    fixture.chmod(0o700)
    result = subprocess.run(
        [shell, '-c', str(fixture)], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
    print('returncode={}'.format(result.returncode))
    print('stdout={!r}'.format(result.stdout))
    print('stderr={!r}'.format(result.stderr))
PY
```

Observed exit status: 0 for the probe runner, with target result:

```text
returncode=0
stdout='HOST_SHELL_FALLBACK\n'
stderr=''
```

Static inspection found `execvp(command->argv[0], command->argv)` at
`sealed/reference/jobs.c:735`. The behavior demonstrates ENOEXEC interpretation beyond byosh's
documented grammar and conflicts with `REQUIREMENTS.md:22` unless that fallback is explicitly carved
out.

## Independent failing probe: zombie during foreground wait

The probe started the shell in a private session, submitted an immediate background command and a
two-second foreground command, then boundedly polled only direct children with `ps`:

```sh
timeout 12s python3 - <<'PY'
import os, shutil, subprocess, time
shell = os.path.abspath('sealed/reference/byosh')
tools = {name: os.path.abspath(shutil.which(name)) for name in ('true', 'sleep', 'ps')}
p = subprocess.Popen([shell], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, universal_newlines=True,
                     start_new_session=True)
p.stdin.write("'{}' &\n'{}' 2\n".format(tools['true'], tools['sleep']))
p.stdin.flush()
deadline = time.monotonic() + 1.5
observed = ''
while time.monotonic() < deadline:
    q = subprocess.run(
        [tools['ps'], '-o', 'pid=', '-o', 'ppid=', '-o', 'stat=',
         '-o', 'comm=', '--ppid', str(p.pid)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, timeout=1)
    observed = q.stdout
    states = [line.split()[2] for line in observed.splitlines()
              if len(line.split()) >= 4]
    if (any(state.startswith('Z') for state in states) and
            any(state.startswith(('S', 'R')) for state in states)):
        break
    time.sleep(0.02)
print(observed.rstrip())
p.stdin.close()
p.stdin = None
stdout, stderr = p.communicate(timeout=5)
print('returncode={}'.format(p.returncode))
print('stderr={!r}'.format(stderr))
PY
```

Observed while the foreground child was still live:

```text
Z    true <defunct>
S    sleep
returncode=0
stderr="[1] ...\n[1] Done '/usr/bin/true' &\n"
```

The PID columns are omitted here because they are ephemeral. Source inspection confirms that the
foreground loop waits only on `-job->pgid`; the all-child nonblocking sweep occurs after that loop.

## Diagnostic and harness checks

The exact sanitizer build was attempted:

```sh
timeout 45s make -C sealed/reference clean all \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -g -fno-omit-frame-pointer -fsanitize=address,undefined' \
  LDFLAGS='-fsanitize=address,undefined'
```

Exit status: 2. Instrumented compilation succeeded, but linking failed because
`/usr/lib64/libasan.so.5.0.0` and `/usr/lib64/libubsan.so.1.0.0` were absent. The normal reference was
rebuilt successfully afterward. `valgrind`, `clang`, `gdb`, and `cppcheck` were unavailable. `strace`
was installed, but even its ptrace capability probe failed with `PTRACE_TRACEME: Operation not
permitted`; no syscall-trace evidence is claimed.

The benchmark harness received one bounded smoke iteration:

```sh
timeout 45s python3 benchmarks/run_bench.py \
  --shell ./sealed/reference/byosh --warmups 0 --iterations 1 --timeout 5
```

Exit status: 0. It emitted schema-version-1 JSON explicitly classified as `unvalidated local
measurement`, with five workloads and a target digest. No output file or performance conclusion was
retained. This verifies only that the harness starts and completes; it does not establish
`BENCHMARKED`.

## Limitations

- The upstream catalog checkout and linked tutorial were not readable, so copying, close paraphrase,
  source-commit authenticity, and the linked license were not independently compared.
- Sanitizer execution, valgrind, and syscall tracing were unavailable as described above.
- No fuzzing, allocator/process fault injection, exhaustive adversarial campaign, or non-Linux/
  non-procps portability run was performed.
- No independently materialized learner view was supplied, so sealed-file transfer isolation is
  inconclusive even though learner-facing source files contained no direct sealed-path markers.
- The benchmark command was a smoke run only. Production suitability was not assessed and is not
  claimed.
