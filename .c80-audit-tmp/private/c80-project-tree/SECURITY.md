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
- Generic CSDIY examiners receive one controller-projected, checksum-bound textual student view.
  Projection rejects rubric, hidden, sealed, reference, and other-student-shaped content; excludes known
  staged inputs and mutable caches; and retains source/test inventory evidence. The projected tree hash
  must exactly equal the descriptor-pinned projection hash, and the path-manifest digest is strict
  SHA-256. The controller opens every root and child relative to held no-follow directory descriptors,
  requires single-link regular files, revalidates names/inodes before and after reading, and rejects
  races, invalid UTF-8, NULs, special files, or limit overflow without truncation. Candidate, rubric,
  novel-check, and prior-evaluation files are never mounted: every verified dependency is a length-framed
  prompt projection. The examiner workspace is empty and root-denied, with command, artifact, code-mode,
  deferred-executor, hosted, browser, MCP, plugin, and network capabilities disabled.
- Before that projection, student submissions receive a complete bounded streaming preflight and no
  destination is allocated on entry/file/byte/depth or separation failure. Dependency trees use the
  same descriptor-relative bounded snapshot logic rather than `copytree`. The CSDIY caps are shared
  across both stages and the projector; hard-linked regular files fail closed and only ordinary rwx mode
  bits are propagated.
- A CSDIY examiner cannot create its authoritative result files. It returns one schema-constrained JSON
  object through a private bounded final-message channel outside its filesystem view. The CLI writes a
  fixed-name hard-link alias in a dedicated launch directory beneath the job log, while the randomized
  inode/path is beneath a separate controller-private per-job/attempt root. The controller holds a
  read-only no-follow descriptor for the alias and supplies outer Codex only its ephemeral parent-procfd
  pathname; Codex does not inherit that descriptor. The installed permission runner proves an inner tool
  given the exact pathname cannot open, read, write, or truncate it. The launch directory contains only
  the fixed alias during execution; the randomized token is absent from argv, environment, cwd,
  provenance, retained-log topology, and inherited descriptor paths. Durable argv uses a symbolic
  placeholder, and numeric PID/FD pathnames are redacted from retained output and errors. Every transport and alias ancestor
  is component-walked without symlink following before mutation. The controller retains the fixed private
  transport anchor and alias directory capabilities, parks nonce-bearing descendant descriptors while
  the CLI runs, and restores them only by no-follow relative opens that match captured device/inode/type/
  mode/owner/link-count bindings. Creation, hard-linking, reading, unlinking, recovery, and empty-directory
  removal are all descriptor-relative; a re-resolved absolute path is never a cleanup authority. Binding
  uncertainty preserves evidence rather than guessing, so an ancestor replacement cannot redirect an
  operation into a victim tree. The controller removes the alias by its held directory descriptor,
  requires the private file to return to one link, and rejects replacement, extra-entry, extra-link, and
  parent-swap races. POSIX cannot make `unlinkat`/`rmdirat` conditional on an inode binding, so final
  check-to-removal assumes the mode-`0700` invocation directories are quiescent after the trusted CLI and
  descendants are reaped. A hostile same-UID process rewriting an entry inside an already-held directory
  in that interval is outside this boundary; replacing an ancestor still cannot redirect cleanup. The backend
  reaps the original process group and detached descendants before accepting the channel, then
  the controller alone creates `evaluation.json` and `feedback.md`. Workspace files cannot forge this
  channel. Evaluation archives contain only those controller-created outputs, and an unbound legacy
  verdict cannot update learner state or unlock course progression.
- Result-channel nonces come from an independent 256-bit random capability, not a durable identifier.
  Persistent policy, invocation, event, run, and artifact records contain only the v3 nonce-free
  contract and no private-path, numeric PID/FD, or nonce digest. Result content is retained only after exit through the
  normal bounded redacted output path; it is not embedded in provenance. Startup recovery is bounded and
  deletes only exact verified 64-hex leftovers in the current attempt root; it fails closed on ambiguous
  aliases or unsafe structure, never recursively removes an unknown directory, and never scans another
  job or attempt. Old-attempt roots require control-plane-confirmed retention cleanup rather than inference
  from path age.
- The installed outer Codex CLI is trusted same-UID host infrastructure. This topology prevents the
  worker/model-visible cwd, argv, environment, provenance, and log tree from disclosing the private
  capability, and the inner permission profile denies the controller tree. It is not secrecy against a
  compromised host CLI that recursively scans controller-owned storage or searches the filesystem by
  inode; hostile same-UID infrastructure requires a separately administered container or VM boundary.
- New Codex jobs use the strict `factory-isolated` permission profile rather than `--sandbox`: deny the
  filesystem root, write only the job workspace, read only the minimal runtime and exact allowlisted
  toolchain roots, disable tool network, and inherit no shell environment.
- Every catalog-scale BYOX/CSDIY `codex_task`, including course progression, revisions, and BYOX
  remediation, is checked again immediately before launch. Seed kind, stable job-ID shape, and artifact
  type independently identify protected work; changing one JSON marker cannot bypass the requirement
  for `exec`, `factory-isolated`, `gpt-5.6-sol`, `ultra`, and the exact approved ARM provider/base URL
  with authentication enabled and WebSockets disabled. Legacy payloads need not be rewritten, while
  any explicit conflicting or unknown partial declaration fails closed. Only exact historical omitted,
  BYOX quality-only, and kickoff-revision requirement shapes remain compatible; both partial forms must
  also match their exact role, artifact, worker, and job/revision identity.
- The scheduler defaults to refusing the legacy unsandboxed host-command validator path. Jobs carrying
  either a `command` validator or command-mode `review_acceptance`, plus malformed validator envelopes,
  remain unclaimed in `READY` while deterministic structural jobs continue. This fence must remain active
  in production until the replacement command sandbox and immutable-grader integration pass independent
  adversarial review.
- The worker applies the same policy to the validators actually returned by every handler immediately
  before validation. This covers handler-generated commands and malformed envelopes that payload-only
  scheduler inspection cannot classify; blocked work launches no validator process.
- The job tool boundary denies `CODEX_HOME` (including the authentication file) and disables hosted/web,
  MCP, browser/computer-use, plugin, hook, skill-discovery, and native subagent surfaces.
- Start-time run provenance stores only allowlisted values, paths, counts, and SHA-256 fingerprints. It
  never copies raw TOML, environment values, prompt/payload text, source-file contents, or authentication
  material; common assignment, bearer, API-key, and URL-userinfo forms are redacted before persistence.
- Validated artifacts are copied to same-filesystem staging, reject symlinks/special files, are fsynced,
  renamed atomically, and use the framed `tree-sha256-v2` tree checksum.
- The Codex backend capability gate is claimable without host commands and is not trusted merely because
  its exact marker once hashed correctly. The controller installs a fresh-inode snapshot first, then binds
  deterministic content validation and publication to the cutover and archive checksums.
- Every BYOX structural candidate uses an earlier authoritative cutover. Ordinary packs copy their
  complete output and repair packs copy selected outputs plus protected inputs through no-follow
  descriptors into fresh factory-private inodes. Excluded repair roots are retained only as bounded
  capture-time hashes. The fresh tree replaces the allocated attempt path before any validator runs;
  the original worker tree is retired and removed. The isolated worker's bind mount and retained file
  descriptors remain attached to the retired object and cannot resolve the replacement or artifact
  store. The worker binds post-validation, projection, and archive-preparation checksums to the cutover
  record, and structural BYOX jobs cannot mix in an executable validator.
- BYOX repair output additionally uses a projection-aware cutover: selected outputs and protected inputs are
  copied once through no-follow descriptors into fresh factory-private inodes, while excluded roots are
  retained only as bounded capture-time hashes. The fresh tree replaces the allocated attempt path before
  any validator runs; the original worker tree is retired and removed. One inode namespace detects links
  across selected, staged, and excluded roots, staged manifests are revalidated exactly, and artifact,
  projection, validation-workspace, and cutover hashes must agree before publication. The isolated worker's
  bind mount remains attached to the retired directory object across the host rename, so a retained worker
  path or descriptor cannot resolve or modify the replacement. Host and deterministic retained-descriptor
  probes verify this inode boundary; it does not rely on same-UID mode bits for isolation. Sequential
  rescans are integrity checks over that detached object, not a security claim about a reachable writer.
- Source activation, optional learner/evaluator state, artifact evidence, and fenced job success publish
  in one SQLite transaction; a stale lease, cancellation, or callback failure rolls the transaction back.
- Destructive operations are restricted to the configured factory warehouse.

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
multi-tenant isolation. The profile requests `/proc` denial. A live no-tool regression scans every
readable `/proc/*/{cmdline,environ,fd,cwd,root}` entry for the randomized result token and finds none,
but Linux process-filesystem mediation still makes a blanket “all process information is impossible”
claim unjustified.
The Codex parent also necessarily retains its ARM model connection even though worker tools have network
disabled. Use a separately administered container or VM before placing hostile code or secrets in scope.

Codex and validator commands run in their own process sessions so normal timeout and
cancellation can terminate the complete group. The exec backend temporarily becomes a Linux child
subreaper, refuses installation if it already owns an unrelated direct child, and reconciles newly
reparented detached descendants before accepting the final-message channel. A live regression covers a
candidate that calls `setsid`, brute-forces inherited descriptors, ignores `SIGTERM`, and attempts a late
write. If the supervising worker itself is unrecoverably killed, however, cleanup cannot run and no
cgroup or parent-death signal presently contains those descendants. Operators must audit the host
process table after such a hard kill; lease recovery alone is not operating-system process containment.

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
