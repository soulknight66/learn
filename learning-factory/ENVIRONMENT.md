# Environment audit — 2026-08-31

- Host: RHEL 8.10, Linux 4.18, x86-64, 16 CPUs, about 93 GiB RAM.
- Workspace: NFSv3 with ample capacity; SQLite uses rollback journal, FULL sync, and short locks.
- Python: 3.11.5; SQLite runtime/CLI 3.26.0. PyYAML exists, but the runtime has no external dependency.
- Tests: standard-library `unittest`; pytest/Hypothesis are not installed.
- Git: 2.9.3. GCC/G++ 8.5, Make 4.2.1, CMake 3.26.5.
- Missing: Go, Rust, Java, Node, Docker/Podman, clang, valgrind, gdb.
- Isolation: Codex's beta Linux permission-profile runner is installed and host-tested; bubblewrap 0.4.0
  and user/PID/network namespaces work underneath the available tooling, but no container runtime exists.
- Codex: CLI 0.146.0; stable `codex exec --json`, resume, output schema, and last-message output.
  App-server and exec-server are present but experimental. Native multi-agent and hooks are available.
- Factory Codex profile: standalone `codex exec --json`, ARM provider base
  `https://openai-api-proxy.geo.arm.com/api/providers/openai/v1`, Responses transport, WebSockets
  disabled, `gpt-5.6-sol`, `ultra` reasoning, ephemeral sessions, and a 1,800-second default timeout.
  Model and reasoning remain configurable per job.
- Operated concurrency: 12 globally, bounded to five reference builders, two course managers, two
  students, and three examiners for the principal graph; a continuous `run --until-idle` controller is
  active.
- `/tmp` is capacity-constrained; durable state stays in the project warehouse and scratch is bounded.

## Verified Codex route and current operation

The versioned backend-capability gate completed through the ARM provider and passed its external output
validator. The provider reuses Codex authentication (`requires_openai_auth = true`); no credential is
stored in `factory.toml`, SQLite payloads, prompts, logs, or this document. The configured wire API is
Responses and WebSockets are explicitly disabled. Historical jobs blocked while using the old default
endpoint remain blocked until an operator deliberately retries them; durable history is not rewritten
when routing changes.

The normalized catalog currently has 82 active CSDIY courses and 359 active BYOX entries. Durable jobs
cover all of them with bounded kickoff cohorts and builder/reviewer pairs, but coverage is not completion.
The generic BYOX Docker builder is retrying after its first candidate failed validation for containing a
forbidden root `.git`; that failed candidate was not published. Two earlier v1 review jobs completed
without deterministic verdict evidence and therefore do not count as accepted; v2 remediation preserves
and supersedes that history.

New Codex jobs use `factory-isolated` instead of the legacy `--sandbox` flag. The strict invocation
denies the root and `CODEX_HOME`, grants workspace-only writes and reads only a minimal runtime plus
`/arm/tools/python/python/3.11.5/rhe8-x86_64`, disables tool networking and environment inheritance, and
turns off hosted/web, MCP, browser/computer-use, plugin, hook, skill, and native subagent surfaces. The
host probe confirms sibling-file, auth-file, environment, and socket denial. The runner is beta and the
requested `/proc` denial is not treated as complete because the backend itself uses an inherited
`/proc/self/fd/...` output descriptor. A container/VM remains necessary for hostile code or secrets.

`seed-course-next` can extend eligible courses one normalized record at a time after verified examiner
PASS evidence. It materializes durable work; it does not claim that the student completed the official
course or demonstrated transfer.

Artifact staging is created under the final artifact's parent directory, so the final rename remains
on one filesystem. The implementation issues file and directory `fsync` calls before and after rename;
that is the durability protocol exercised by the tests, not a claim that NFS can survive every possible
server or storage failure. Scheduler startup therefore verifies published v2 artifact trees and
logically quarantines inconsistent records.

## Authorized sources

| Source | Local path | Commit | Upstream | License |
|---|---|---|---|---|
| CS Self-Learning / CSDIY | `../cs-self-learning` | `adce8e13789dc16aa6d1fbe163e9541736defae4` | `https://github.com/PKUFlyingPig/cs-self-learning` | MIT for repository-authored content |
| Build Your Own X | `../build-your-own-x` | `aa17439b62f384511a5561ce308e9598b94d8989` | `https://github.com/codecrafters-io/build-your-own-x` | CC0 declaration in README; linked works retain their licenses |

Both sources were clean at audit time. They are ordinary vendored subtrees of the single top-level Git
repository, with no nested `.git` directories or `.gitmodules`. The committed `../SOURCE_PINS.json`
binds each subtree to its audited upstream commit, exact root-tree object, remote, and branch. The two
recorded tree objects were independently checked against those upstream commits during consolidation.

Base ingestion is local-only and does not fetch linked material. Adapters verify that the subtree in the
outer repository's committed `HEAD` still has the locked tree object, then read its blobs from the Git
object database while retaining the upstream commit identity. Dirty or untracked working-tree bytes
therefore do not alter the normalized snapshot, and a committed subtree change without an updated audited
pin fails closed. The database retains superseded snapshots for provenance while exposing only one active
commit per canonical source path to current consumers.
