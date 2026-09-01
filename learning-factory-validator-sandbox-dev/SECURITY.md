# Security and data boundaries

- Allowed source roots are explicit command arguments; adapters never traverse sibling repositories.
- Source normalization reads tracked blobs from the enqueued Git commit, excluding dirty and untracked
  working-tree content. Superseded snapshots remain immutable provenance; current consumers query only
  the single active snapshot for each canonical repository path.
- Git remotes are recorded as provenance but not fetched during local ingestion.
- Prompts receive staged source excerpts, not arbitrary home-directory content.
- Logs redact common credential assignments and never intentionally record environment variables.
- Job creation canonicalizes payloads once and, before opening a database transaction, rejects any
  exact credential-classified controller-environment value found in those bytes. The check returns a
  generic error and never logs, hashes, persists, or identifies the matching credential. Direct SQL
  inserts remain outside this defense-in-depth guard.
- Subprocess commands are argv arrays with no shell interpolation.
- Student exercise views copy only allowlisted public files and reject symbolic links.
- Hidden validators and references remain outside student views; their checksums and results are recorded.
- New Codex jobs use the strict `factory-isolated` permission profile rather than `--sandbox`: deny the
  filesystem root, write only the job workspace, read only the minimal runtime and exact allowlisted
  toolchain roots, disable tool network, and inherit no shell environment.
- The job tool boundary denies `CODEX_HOME` (including the authentication file) and disables hosted/web,
  MCP, browser/computer-use, plugin, hook, skill-discovery, and native subagent surfaces.
- Start-time run provenance stores only allowlisted values, paths, counts, and SHA-256 fingerprints. It
  never copies raw TOML, environment values, prompt/payload text, source-file contents, or authentication
  material; common assignment, bearer, API-key, and URL-userinfo forms are redacted before persistence.
- Validated artifacts are copied to same-filesystem staging, reject symlinks/special files, are fsynced,
  renamed atomically, and use the framed `tree-sha256-v2` tree checksum.
- Source activation, optional learner/evaluator state, artifact evidence, and fenced job success publish
  in one SQLite transaction; a stale lease, cancellation, or callback failure rolls the transaction back.
- Destructive operations are restricted to the configured factory warehouse.
- The quarantined validator-command primitive requires verified kernel cgroup memory/pids accounting
  and zero swap; nominal systemd scope metadata does not suffice. It masks trusted PID 1, makes its
  command supervisor non-dumpable, closes inherited setup descriptors, denies anonymous-memory and
  unsafe address-family syscalls, and exposes no blanket `/usr` or `/usr/local`. It still does not
  promote artifacts, and known-pattern redaction cannot make secret-bearing untrusted code safe.

The filesystem rename and SQLite commit are necessarily separate durability domains. Startup verifies
all published `VERIFIED_V2` trees and logically quarantines missing or mismatched artifacts as
`LEGACY_UNVERIFIED`/`PARTIAL`; it does not repair them or erase forensic bytes. A crash between rename
and database publication may leave an unreferenced artifact directory, but it cannot create an
authoritative artifact row or successful job without the fenced SQLite commit.

The host runs all local processes as one Unix account, but new Codex tool processes are additionally
confined by the installed Linux permission-profile runner. A live integration probe verifies that a
worker can read its job input while a sibling sealed file and the Codex auth file are unreadable, an
operator sentinel is absent from its environment, and a network socket cannot be created. This is an
enforced boundary rather than a natural-language request.

The runner is nevertheless beta, and `ISOLATED_VIEW` is not a claim of formally verified hostile
multi-tenant isolation. The profile requests `/proc` denial, but bounded last-message capture passes an
inherited file descriptor named through `/proc/self/fd/...`; Linux process-filesystem mediation and
already-open descriptors make a blanket “all `/proc` information is impossible” claim unjustified. The
Codex parent also necessarily retains its ARM model connection even though worker tools have network
disabled. Use a separately administered container or VM before placing hostile code or secrets in scope.

Codex and validator commands run in their own process sessions so normal timeout and
cancellation can terminate the complete group. If the supervising worker is itself
unrecoverably killed, session descendants are not yet tied to a cgroup or Linux
parent-death signal and may outlive it. Only the supervisor/worker process identity is durably
recorded, not a complete descendant inventory. Operators must audit the host process table after such
a hard kill; the factory does not claim that lease recovery alone kills orphaned OS processes.

The enabled model worker is a separate `codex exec` process configured for `gpt-5.6-sol` with `ultra`
reasoning. It uses the custom ARM provider base
`https://openai-api-proxy.geo.arm.com/api/providers/openai/v1`, the Responses transport, and WebSockets
disabled. Configuration accepts only absolute HTTP(S) backend endpoints without user information,
queries, fragments, or control characters, preventing a credential-bearing URL from entering durable
run state. `requires_openai_auth` delegates credential retrieval to Codex's existing authentication;
credentials are never embedded in configuration, prompts, logs, database payloads, or generated
artifacts. The job permission profile prevents model-invoked tools from reading that auth storage. A
bounded exact-output gate has succeeded through this route under independent validation.
Older `blocked_authentication` rows remain durable historical evidence and require deliberate manual
retry; they do not describe the availability of the verified route. Operators must continue to respect
access controls, rate limits, and credential-handling policy.
