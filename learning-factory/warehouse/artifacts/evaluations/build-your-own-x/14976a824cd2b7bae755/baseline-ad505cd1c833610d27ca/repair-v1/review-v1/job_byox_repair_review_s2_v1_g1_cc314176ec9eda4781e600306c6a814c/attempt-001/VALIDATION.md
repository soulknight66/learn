# Independent validation record

Date: 2026-09-02 (America/Chicago)

All commands ran from the review workspace root unless a different working directory is stated.
`CANDIDATE/` was not modified. Its directories are intentionally read-only, so bounded runtime tests
used the writable parent workspace as `TMPDIR`. The login wrapper printed these lines before every
invocation; they are environment warnings, not candidate output:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

## Toolchains

Commands:

```bash
/usr/bin/bash --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
```

All exited 0. Observed first lines:

```text
GNU bash, version 4.4.20(1)-release (x86_64-redhat-linux-gnu)
Python 3.11.5
gcc (GCC) 15.2.0
```

The Python and GCC executables were invoked from the configured read-only toolchain roots by their
exact absolute paths.

Availability command:

```bash
for tool in shellcheck rg git; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '%s AVAILABLE %s\n' "$tool" "$(command -v "$tool")"
    else
        printf '%s UNAVAILABLE\n' "$tool"
    fi
done
```

Observed:

```text
shellcheck UNAVAILABLE
rg UNAVAILABLE
git UNAVAILABLE
```

## Inventory, syntax, and immutable content

Commands:

```bash
find CANDIDATE -type f | wc -l
/usr/bin/find CANDIDATE -type f -name '*.sh' -exec /usr/bin/bash -n '{}' +
find CANDIDATE -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
```

Observed: 42 files; shell parsing exited 0 with no command-produced output; the aggregate file-content
digest was:

```text
69f379e90f3afc2a3fee5839d231163e4d85f7c3553d17f4e2cc06b4014d06cc  -
```

`find` inventory showed only regular files and directories, with no symlink or special artifact
entry. A targeted search found no directory named `sealed`, `reference`, `reference_tests`,
`hidden_tests`, `solution`, or `solutions` beneath `starter/`, `public_tests/`, or `environment/`.

## Independent manifest and provenance parsing

The configured Python interpreter strictly parsed both objects with a duplicate-key hook, computed
raw and canonical SHA-256 digests, and compared their identifiers. Command body:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 <<'PY'
import hashlib
import json
from pathlib import Path

root = Path("CANDIDATE")

def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key: " + key)
        result[key] = value
    return result

objects = {}
for name in ("MANIFEST.yaml", "PROVENANCE.json"):
    raw = (root / name).read_bytes()
    obj = json.loads(raw, object_pairs_hook=unique,
                     parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode()
    objects[name] = obj
    print(name, hashlib.sha256(raw).hexdigest(), hashlib.sha256(canonical).hexdigest())

manifest = objects["MANIFEST.yaml"]
provenance = objects["PROVENANCE.json"]
print(manifest["project_id"] == provenance["project"]["project_id"])
print(manifest["source_id"] == provenance["source"]["source_id"])
print(manifest["source_commit"] == provenance["source"]["commit_hash"])
print(manifest["provenance_sha256"] == provenance["snapshot_sha256"])
print(manifest["provenance_sha256"] ==
      hashlib.sha256((root / "PROVENANCE.json").read_bytes()).hexdigest())
PY
```

Observed exit 0 and:

```text
MANIFEST.yaml b0005f38f7cef3f36e2bb88b22c0180da88a4acc62b575aadfd199a95e002028 13eed8f5a9ec33abe9ae646fc5e45285db68165576e433f1bdb7444d36df5e29
PROVENANCE.json 6c6ad5fe82b5d44f8aac9c06cb78b0b97b97a63536d8ae379dc986784f064768 7b2dac00b3a612eeeb3afa49141c02949998504331dbc852cd174d0bb32b2426
True
True
True
True
False
```

Thus IDs and the factory snapshot relationship agree. The manifest's provenance field is not the
raw digest of the accompanying file; this semantic distinction is noted in `REVIEW.md`.

## Reproduction of candidate-supplied checks

These scripts are submitted material, so their success is supporting evidence rather than label
proof. Each runtime command was independently bounded:

```bash
/usr/bin/env TMPDIR="$PWD" /usr/bin/timeout 30s /usr/bin/bash \
  CANDIDATE/public_tests/test_contract.sh CANDIDATE/sealed/reference/tinybox.sh
/usr/bin/env TMPDIR="$PWD" /usr/bin/timeout 30s /usr/bin/bash \
  CANDIDATE/sealed/reference_tests/test_reference.sh
/usr/bin/env TMPDIR="$PWD" /usr/bin/timeout 30s /usr/bin/bash \
  CANDIDATE/sealed/reference_tests/test_adversarial.sh
/usr/bin/env TMPDIR="$PWD" /usr/bin/timeout 30s /usr/bin/bash \
  CANDIDATE/environment/check.sh
/usr/bin/env TMPDIR="$PWD" /usr/bin/timeout 30s /usr/bin/bash \
  CANDIDATE/sealed/reference_tests/test_real_runner.sh
/usr/bin/env TMPDIR="$PWD" /usr/bin/timeout 30s /usr/bin/bash \
  CANDIDATE/public_tests/test_contract.sh CANDIDATE/starter/tinybox.sh
```

Observed results:

| Check | Exit | Observed result |
|---|---:|---|
| Public contract / reference | 0 | 8/8 passed |
| Sealed lifecycle suite | 0 | nested public 8/8 and sealed 9/9 passed |
| Adversarial suite | 0 | 6/6 passed |
| Environment probe | 0 | all listed tools available; unprivileged user namespace supported |
| Real runner | 0 | create, true, hostname, PID-1 `ps`, and inspect passed |
| Public contract / starter | 1 | help passed; checks 2–8 failed as intentionally disclosed |

Real-runner output included:

```text
CREATE_OUTPUT=live
CREATE_STATUS=0
TRUE_STATUS=0
HOSTNAME_OUTPUT=live
HOSTNAME_STATUS=0
PS_OUTPUT=      1 ps
PS_STATUS=0
INSPECT_STATUS=0
name=live
status=EXITED
exit_code=0
PASS real namespace runner completed the probe
```

The candidate structural audit was also run from `CANDIDATE/`:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/verify_pack.py
```

It exited 0 and reported 23 required regular files, 21 absent forbidden paths, regular artifact
entry types, strict pinned manifest/provenance objects, and a passing credential-pattern scan. This
is not treated as independent proof because both the audit and expectations are candidate-supplied.

## Independently authored controller probe

The probe used `/usr/bin/printf` as a format-sensitive runner, then `/usr/bin/false`, so it did not
depend on either candidate test runner. Its temporary state was constrained to a `mktemp` directory
and deleted by a validated trap. The executed invocation was:

```bash
/usr/bin/timeout 30s /usr/bin/bash <<'REVIEW_PROBE'
set -eu
probe_root=$(/usr/bin/mktemp -d "$PWD/reviewer-independent.XXXXXX")
cleanup() {
    case "$probe_root" in
        "$PWD"/reviewer-independent.*) /usr/bin/rm -rf -- "$probe_root" ;;
        *) return 1 ;;
    esac
}
trap cleanup EXIT HUP INT TERM
controller=$PWD/CANDIDATE/sealed/reference/tinybox.sh
/usr/bin/mkdir -p "$probe_root/source/etc" "$probe_root/outside"
state_dir="$probe_root/state|%s|%s|%s|%s|%s|%s|"
export TINYBOX_STATE_DIR=$state_dir

create_output=$(/usr/bin/bash "$controller" create alpha "$probe_root/source")
printf 'CREATE_STATUS=0\nCREATE_OUTPUT=%s\n' "$create_output"

set +e
run_output=$(TINYBOX_RUNNER=/usr/bin/printf /usr/bin/bash "$controller" \
    run alpha -- /bin/tool 'two words' '*' 'semi;colon' '')
run_status=$?
set -e
printf 'ARGV_RUN_STATUS=%s\nARGV_RUN_OUTPUT=%s\n' "$run_status" "$run_output"
/usr/bin/bash "$controller" inspect alpha

set +e
TINYBOX_RUNNER=/usr/bin/false /usr/bin/bash "$controller" run alpha -- /bin/false >/dev/null
false_status=$?
set -e
printf 'FALSE_RUN_STATUS=%s\n' "$false_status"
/usr/bin/bash "$controller" inspect alpha

/usr/bin/bash "$controller" create beta "$probe_root/source" >/dev/null
printf 'LIST_BEGIN\n'
/usr/bin/bash "$controller" list
printf 'LIST_END\n'

set +e
invalid_output=$(/usr/bin/bash "$controller" create ../escape "$probe_root/source" 2>&1)
invalid_status=$?
set -e
printf 'INVALID_STATUS=%s\nINVALID_OUTPUT=%s\n' "$invalid_status" "$invalid_output"

/usr/bin/bash "$controller" delete alpha >/dev/null
if [ -d "$probe_root/outside" ] && [ ! -e "$state_dir/containers/alpha" ]; then
    printf 'DELETE_SCOPE_OK=yes\n'
else
    printf 'DELETE_SCOPE_OK=no\n'
    exit 1
fi
REVIEW_PROBE
```

The executed probe exited 0. Material observations (the random prefix is shortened) were:

```text
CREATE_OUTPUT=alpha
ARGV_RUN_STATUS=0
ARGV_RUN_OUTPUT=<workspace>/reviewer-independent.<random>/state|alpha|/bin/tool|two words|*|semi;colon||/containers/alpha/rootfs
name=alpha
status=EXITED
exit_code=0
FALSE_RUN_STATUS=1
name=alpha
status=EXITED
exit_code=1
alpha<TAB>EXITED
beta<TAB>CREATED
INVALID_STATUS=3
INVALID_OUTPUT=tinybox: invalid container name: ../escape
DELETE_SCOPE_OK=yes
```

The six `%s` conversions prove that `alpha`, `/bin/tool`, `two words`, `*`, `semi;colon`, and the
empty string reached the runner as six distinct arguments.

## Independently authored namespace probe

An initial attempt to use `gcc -static` exited 1 with `/usr/bin/ld: cannot find -lc`; static libc is
not installed in the configured toolchain. The bounded probe was then compiled dynamically and its
reported absolute dependencies copied into a temporary rootfs. Its C assertions required PID 1,
mapped UID 0, hostname `reviewhost`, cwd `/`, readable `/proc/self/status`, and exact argv values.

Command outline (the actual source assertions are shown):

```bash
/usr/bin/timeout 30s /usr/bin/bash <<'NAMESPACE_PROBE'
set -eu
probe_root=$(/usr/bin/mktemp -d "$PWD/reviewer-namespace.XXXXXX")
cleanup() {
    case "$probe_root" in
        "$PWD"/reviewer-namespace.*) /usr/bin/rm -rf -- "$probe_root" ;;
        *) return 1 ;;
    esac
}
trap cleanup EXIT HUP INT TERM
/usr/bin/mkdir -p "$probe_root/rootfs/bin"
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -O2 -x c \
    -o "$probe_root/rootfs/bin/probe" - <<'C'
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(int argc, char **argv) {
    char hostname[128] = {0};
    char cwd[256] = {0};
    if (gethostname(hostname, sizeof(hostname) - 1) != 0) return 20;
    if (getcwd(cwd, sizeof(cwd)) == NULL) return 21;
    int proc_ok = access("/proc/self/status", R_OK) == 0;
    printf("PID=%ld UID=%ld HOSTNAME=%s CWD=%s PROC=%s ARGC=%d\n",
           (long)getpid(), (long)getuid(), hostname, cwd,
           proc_ok ? "readable" : "missing", argc);
    for (int i = 0; i < argc; ++i) printf("ARGV%d=<%s>\n", i, argv[i]);
    int ok = getpid() == 1 && getuid() == 0 && strcmp(hostname, "reviewhost") == 0
        && strcmp(cwd, "/") == 0 && proc_ok && argc == 5
        && strcmp(argv[1], "two words") == 0 && strcmp(argv[2], "*") == 0
        && strcmp(argv[3], "semi;colon") == 0 && strcmp(argv[4], "") == 0;
    return ok ? 0 : 22;
}
C
/usr/bin/ldd "$probe_root/rootfs/bin/probe" | /usr/bin/awk '{
    for (field = 1; field <= NF; field++) if ($field ~ /^\//) print $field
}' | /usr/bin/sort -u | while IFS= read -r dependency; do
    [ -f "$dependency" ] || continue
    /usr/bin/mkdir -p "$probe_root/rootfs$(/usr/bin/dirname -- "$dependency")"
    /usr/bin/cp -L -- "$dependency" "$probe_root/rootfs$dependency"
done
/usr/bin/bash "$PWD/CANDIDATE/sealed/reference/runner.sh" \
    "$probe_root/rootfs" reviewhost /bin/probe 'two words' '*' 'semi;colon' ''
NAMESPACE_PROBE
```

Observed exit 0:

```text
PID=1 UID=0 HOSTNAME=reviewhost CWD=/ PROC=readable ARGC=5
ARGV0=</bin/probe>
ARGV1=<two words>
ARGV2=<*>
ARGV3=<semi;colon>
ARGV4=<>
```

This proves only the enumerated behavior on this host. It does not prove containment, IPC isolation,
mount hardening, cross-kernel portability, or production safety.

## Limitations

- Candidate-supplied scripts do not establish a promotion label; independent probes above cover only
  a bounded subset of the contract.
- The immutable catalog source and linked repository were unavailable, and restricted network access
  prevented external provenance/originality comparison.
- Only the full pack was available. Directory separation was inspected, but no downstream learner
  view was generated or transfer-tested.
- ShellCheck, `rg`, and `git` were unavailable. Static libc was also unavailable to GCC.
- No fuzzing, benchmark, cross-kernel/filesystem matrix, crash/fault injection, hostile-workload
  analysis, long-duration contention, or production qualification was performed.
