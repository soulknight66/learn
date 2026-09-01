# Repair-generation builder validation

Date: 2026-08-31  
Repair generation: 1  
Manifest status: **GENERATED**  
Manifest labels: **GENERATED**, **PARTIAL**

This is builder-controlled evidence from the repaired pack. It does not award `BUILDS`, `TESTED`,
`FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`. Fresh independent
validation remains mandatory. The deterministic learner projection excludes this file.

The command launcher emitted repeated warnings that the numeric uid/gid had no names. Those warnings
came from the job launcher before the commands below; they were not MiniCTR diagnostics and are not
repeated in each outcome.

## Repair coverage

This generation made the following review-driven changes:

- prospective state-path components are parsed without a here-string or temporary shell object;
- name validation is forced to the C locale in both starter scaffolding and the reference;
- liveness requires a matching PID/start token and a process state other than `Z` or `X`;
- the default isolator uses `unshare --kill-child=TERM`, with a real-host TERM-aware payload probe;
- the environment check creates and removes a private temporary-directory probe;
- an exact learner allowlist, projector, recursive exclusion verifier, and transfer check were added;
- generated material now has an explicit MIT grant, including complete terms in learner-visible
  `README.md`;
- a reproducible artifact inventory covers the explicit pack roots; and
- public/debugging tests were strengthened for locale behavior, layout-independent overlap checks,
  start-gated duplicate create, nonzero argv-helper status, and loser non-overwrite.

## Temporary storage and environment

The host had no `/tmp`. The exact default inventory therefore failed honestly:

```bash
./environment/check.sh
```

Observed: exit 1, `required temporary-storage missing`, and
`environment check: cannot resolve temporary directory: /tmp`.

A private workspace-local scratch base was created for bounded checks:

```bash
mkdir -p .validation-tmp
chmod 700 .validation-tmp
TMPDIR="$PWD/.validation-tmp" ./environment/check.sh
TMPDIR="$PWD/.validation-tmp" ./environment/check.sh --require-isolation-tools
```

Both checks with explicit `TMPDIR` returned 0. Bash, `cp`, `env`, `find`, `mkdir`, `mktemp`, `rm`,
`rmdir`, `sort`, `timeout`, `unshare`, `chroot`, and `mount` were available. The host reported Linux
and Bash `4.4.20(1)-release`. ShellCheck, Bats, and BusyBox were missing. Tool presence alone did not
establish namespace permission.

## Syntax and immutable metadata

Every artifact file whose first line was the Bash shebang was checked:

```bash
roots=(AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE LICENSE_BOUNDARY.md MANIFEST.yaml \
  PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md adversarial benchmarks debugging \
  environment public_tests review_exercises sealed starter)
count=0; failures=0
while IFS= read -r -d '' file; do
  if IFS= read -r first < "$file" && [[ $first == '#!/usr/bin/env bash' ]]; then
    count=$((count+1))
    bash -n "$file" || failures=$((failures+1))
  fi
done < <(find "${roots[@]}" -type f -print0)
printf 'bash_shebang_files=%d syntax_failures=%d\n' "$count" "$failures"
```

Observed: exit 0, `bash_shebang_files=37 syntax_failures=0`.

Metadata commands:

```bash
python3 -m json.tool MANIFEST.yaml >/dev/null
python3 -m json.tool PROVENANCE.json >/dev/null
sha256sum MANIFEST.yaml PROVENANCE.json
cmp -s MANIFEST.yaml PRIOR_BUILD/MANIFEST.yaml
cmp -s PROVENANCE.json PRIOR_BUILD/PROVENANCE.json
```

All returned 0. Observed hashes:

```text
4c518df8fff17d4ec3dab9a954ba9c6cdfe948e335d7cf4479dc60e3cfe87743  MANIFEST.yaml
1e3cf194f1724459eff9ce466c43c648953bb8fc7820b001b3e76c618d9d0ca0  PROVENANCE.json
```

A Python semantic check compared the manifest with the authoritative nine-field object, serialized
the embedded `{"project": ..., "source": ...}` object with sorted compact JSON, and asserted matching
project/source IDs. Observed:

```text
manifest_exact=yes
status=GENERATED
validation_labels=GENERATED,PARTIAL
canonical_project_source_sha256=ed760f2a06241ed32edb3cc27610fe8ef57cfe8aee2ffa2aa37c2f9bf1d90ac6
```

## Supplied and targeted execution

All commands were bounded externally and used the private temporary base.

```bash
TMPDIR="$PWD/.validation-tmp" timeout --kill-after=3s 120s \
  bash sealed/reference_tests/run.sh
```

Observed: exit 0, `22 passed; 0 failed`. The named passing regressions included
`test_name_validation_is_locale_independent`, `test_disjoint_check_survives_unusable_tmpdir`, and
`test_zombie_owner_is_stale_for_ps_run_and_delete`; the last exercises `ps`, `run`, and `delete` while
a Python fixture holds a real zombie with its matching Linux start token.

```bash
TMPDIR="$PWD/.validation-tmp" MINICTR_BIN="$PWD/sealed/reference/minictr" \
  timeout --kill-after=3s 120s bash public_tests/test_minictr.sh
```

Observed: exit 0, `9 passed, 0 failed`, including the locale check, layout-independent overlap
snapshots, and synchronized duplicate-create entry gate.

```bash
TMPDIR="$PWD/.validation-tmp" timeout --kill-after=3s 120s \
  bash adversarial/run.sh sealed/reference/minictr
```

Observed: exit 0, `34 passed; 0 failed`.

The untouched incomplete starter was kept intentionally non-green:

```bash
TMPDIR="$PWD/.validation-tmp" timeout --kill-after=3s 120s \
  bash public_tests/test_minictr.sh
```

Observed: exit 1, `3 passed, 6 failed`; every functional failure reported the starter's status 70
TODO path. This is expected challenge progression, not a passing implementation claim.

Focused review reproductions against the repaired reference were also run with disposable paths:

```bash
TMPDIR="$PWD/.validation-tmp/missing" \
MINICTR_HOME="$PWD/.validation-tmp/targeted/tmpfail/rootfs/state" \
  sealed/reference/minictr create overlap "$PWD/.validation-tmp/targeted/tmpfail/rootfs"

LC_ALL=en_US.utf8 TMPDIR="$PWD/.validation-tmp" \
MINICTR_HOME="$PWD/.validation-tmp/targeted/locale/state" \
  sealed/reference/minictr create 'é' "$PWD/.validation-tmp/targeted/locale/rootfs"
```

The first returned 1 with first diagnostic
`minictr: state directory and rootfs must be disjoint`; no nested state path was created. The second
returned 1 with first diagnostic `minictr: invalid container name: é`; no state path was created.

The opt-in real-host probe was bounded separately:

```bash
TMPDIR="$PWD/.validation-tmp" MINICTR_RUN_REAL_TESTS=1 \
  timeout --kill-after=5s 60s bash sealed/reference_tests/real_integration.sh
```

Observed exit 0 and exactly these result lines:

```text
PASS: rootless user/mount/PID/UTS/IPC/network namespace probe
PASS: real default isolator delivered TERM to the payload and restored state
```

The second result came from a locally compiled static x86-64 payload that installed a TERM handler,
printed readiness, ran through the real default isolator, and printed `payload-received-TERM` before
the wrapper returned 143. This is one host observation, not portable isolation assurance.

## Exercise and benchmark harnesses

Each debugging test was run once against its deliberately broken specimen and once against its sealed
repair, with 20-second outer bounds:

```text
01-argv-boundaries broken=1 fixed=0
02-atomic-create   broken=1 fixed=0
03-exit-status     broken=1 fixed=0
```

The first fixed run preserved helper status 23 as well as exact argv. The second derived the winning
rootfs from the successful process and verified that the losing process did not overwrite it.

A three-iteration runner/summarizer smoke was executed:

```bash
TMPDIR="$PWD/.validation-tmp" timeout --kill-after=3s 120s \
  bash benchmarks/run.sh sealed/reference/minictr 3 \
  >.validation-tmp/benchmark.tsv 2>.validation-tmp/benchmark.log
awk -f benchmarks/summarize.awk .validation-tmp/benchmark.tsv
```

Both commands returned 0; all nine raw operation statuses were 0. The observed summary was:

```text
operation  samples  min_us  mean_us  max_us
create     3        63593   74602.3  90818
ps         3        35769   67107.0  126510
delete     3        38822   43484.0  46104
```

These transient timings only show that the harness ran and do not support a `BENCHMARKED` label.

## Learner projection

The production pack was projected into a new scratch directory and checked twice:

```bash
bash environment/project_learner_view.sh .validation-tmp/learner-view
bash .validation-tmp/learner-view/environment/verify_learner_view.sh \
  .validation-tmp/learner-view
```

Both returned 0. The view contained 19 regular files and exactly these top-level entries:

```text
AGENTS.md
CONCEPTS.md
DESIGN_QUESTIONS.md
MANIFEST.yaml
README.md
REQUIREMENTS.md
environment
public_tests
starter
```

A recursive path scan found zero `sealed`, `reference`, `reference_tests`, `hidden_tests`, `solution`,
`solutions`, or `answers` components. As a negative control, a scratch
`starter/sealed/` directory was inserted; the verifier returned 1, after which the scratch directory
was removed. No production pack file was changed by projection testing.

## Structure, license, inventory, and credential scan

An array-based audit used all 23 authoritative required paths and all 22 authoritative forbidden paths,
then checked the explicit artifact roots for links and special files. Observed:

```text
required_regular=23 missing=0 forbidden_present=0 artifact_regular_files=75 unsafe_nodes=0
```

`LICENSE` contains the MIT text. The same copyright, permission grant, conditions, and warranty
disclaimer are embedded in learner-visible `README.md`; no rights are asserted for the linked resource
whose license is `NOASSERTION`.

The deterministic inventory was generated and independently recomputed:

```bash
sealed/production/build_artifact_inventory.sh
TMPDIR="$PWD/.validation-tmp" sealed/production/verify_artifact_inventory.sh
sha256sum ARTIFACT_INVENTORY.sha256
```

Observed: all commands returned 0, `73 entries recomputed and verified`, and:

```text
0a1034c196408ccb00331560953e99162bce60bf9b38a7682eefcbb98309f6fe  ARTIFACT_INVENTORY.sha256
```

The inventory intentionally excludes itself and mutable `VALIDATION.md`; the scope and limitation are
documented in `LICENSE_BOUNDARY.md` and the production scripts.

The credential scan used all artifact files, including the inventory and this record. Regex fragments
were split in the command text so this evidence did not contain a synthetic key signature:

```bash
roots=(AGENTS.md ARTIFACT_INVENTORY.sha256 CONCEPTS.md DESIGN_QUESTIONS.md LICENSE \
  LICENSE_BOUNDARY.md MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md \
  adversarial benchmarks debugging environment public_tests review_exercises sealed starter)
private_key='-----BE''GIN ''(RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'
aws_key='(A''KIA|A''SIA)[0-9A-Z]{16}'
openai_key='s''k-(proj-)?[A-Za-z0-9_-]{20,}'
github_key='g''h[pousr]_[A-Za-z0-9]{30,}'
find "${roots[@]}" -type f -exec \
  grep -IlE -- "$private_key|$aws_key|$openai_key|$github_key" {} +
find "${roots[@]}" \( -name .env -o -name '*.pem' -o -name '*.key' \
  -o -name credentials.json -o -name secrets \) -print
```

Observed: both searches returned no paths (`credential_signature_matches=0`,
`risky_credential_names=0`). This is a high-confidence signature/name scan, not a proof that arbitrary
prose cannot encode sensitive information.

## Limitations and disposition

- `/tmp` was absent; successful checks used the explicit private workspace-local temporary base.
- ShellCheck, Bats, and BusyBox were unavailable.
- The real integration result applies only to this x86-64 kernel, util-linux build, compiler, and host
  policy. It is not an escape test or production security result.
- The public duplicate-create barrier synchronizes candidate entry without assuming a private layout;
  it cannot pause arbitrary learner code at an unknown internal statement. The focused atomic-create
  exercise separately gates both processes inside the known vulnerable interval.
- No fuzz campaign, hostile-rootfs assessment, load/soak study, external source comparison, production
  deployment, or independent transfer validation was performed.
- The immutable provenance path was retained exactly as required and is excluded from the learner view.

The artifact remains **GENERATED + PARTIAL**, `productionized: false`, and subject to a fresh
independent review.
