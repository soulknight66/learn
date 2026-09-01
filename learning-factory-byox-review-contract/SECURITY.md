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
- Seeded BYOX reviewers contain no command validator. Their exact deterministic verdict contract v2
  requires nonempty evidence/check arrays and nonempty exactly trimmed evidence, check, and limitation
  entries; the separate acceptance validator is closed and non-executable. Attempt-zero pending rows may
  converge in place, while attempted or terminal legacy rows are preserved and superseded by version.
- BYOX remediation accepts only integer contract version `2` and canonical, claim-free validation rows.
  It requires the exact current-attempt required-files PASS for `EVALUATION.json`, `REVIEW.md`, and
  `VALIDATION.md`. One bounded no-follow descriptor pass reads every regular, singly linked archive file,
  computes the complete `tree-sha256-v2` checksum, and retains the three required documents and their
  hashes from those same reads. Initial directory enumeration retains no more than the remaining global
  entry budget, and each final name check consumes at most its expected entries plus one mismatch
  sentinel. A complete descriptor-relative name/inode/metadata and absolute-root revalidation closes
  namespace and checksum sandwiches. The builder archive receives an independent pass under the same
  limits; its observed type, path, checksum algorithm, checksum, owner, attempt, ordered validation-status
  string, and normalized label rows must agree with its admitted artifact profile. Every gate, builder,
  and review path must also resolve through the pinned no-follow chain below the managed artifact root
  derived from the database location; an outside tree with matching bytes is rejected. Runtime schema
  and verdict validation bound `EVALUATION.json` at 1 MiB before allocation.
- Absolute path components stay descriptor-pinned for the entire snapshot. Shared ancestors are checked
  for device/inode identity, while the artifact root and its tree additionally require stable metadata.
  A transient rename followed by restoration of the same shared-ancestor inode is therefore tolerated:
  reads continue through the already-open descriptors and cannot enter a temporary replacement tree.
  A persistent replacement, symlink, or changed inode fails the final identity check.
- A base review is eligible only when its immutable reviewer payload is exactly canonical, its
  dependencies are exactly the configured capability gate and builder, and every canonical candidate
  subpath maps beneath the sole protected `CANDIDATE` root. Generic builders must equal their current
  catalog-derived complete job specification, including the job ID/type/worker, priority and score
  inputs, retry bound, model/reasoning, sole gate dependency, and full payload. Only the exact historical
  model-only payload and its exact current backend-policy transformation are admitted; reviewer
  expectations are derived from that reconstructed payload rather than stored mutable fields. Specialized
  builders must equal one of the five complete shared seed specifications reconstructed from the active
  catalog, including their historical terminal envelope and dependency set. The archived staging manifest
  must bind every mapping to
  the same observed builder artifact identity, type, checksum, algorithm, and attempt. Missing, extra,
  direct, deformed, or coherently type-switched inputs publish no repair job, dependency, or event.
- Remediation reads and strictly normalizes the active BYOX catalog, applies requested-project and scan
  bounds, reconstructs canonical specs, and publishes on one `BEGIN IMMEDIATE` connection. Ingestion
  cannot commit a source/project revision between selection and publication. Reviewers must retain
  canonical `codex_task`/examiner/model/reasoning identity. Generic builders, completed repair builders,
  and reviewers must have the canonical attempt ceiling, an integer successful attempt within that
  ceiling, ordered finite terminal timestamps, cleared ownership/lease/retry/failure state, and no
  cancellation before a reviewer or later generation can be published;
  coherently changing the job, artifact, staged binding, labels, or review validations to an impossible
  attempt still publishes nothing.
- Specialized KV v1/v2, HTTP, allocator, and bytecode builders are authorized from the same deterministic
  active-catalog constructors used by their original seed paths. Remediation exact-matches the complete raw
  job definition, dependencies, and reachable success envelope before reading its artifact; no mutable
  stored row supplies canonical payload data. Historical payloads that omitted `artifact_type` remain
  exact, and only the independently verified type is added to a fresh reviewer-facing copy.
- Stored job payloads used for seeding, claiming, and BYOX remediation share a bounded strict JSON decoder.
  It accepts only exact built-in `str` or `bytes` inputs and applies explicit lexical nesting, token, node,
  string, number, and sign-aware integer bounds before recursive decoding. Those limits do not inherit
  mutable interpreter integer or recursion settings. Duplicate object keys at any level, unpaired
  surrogates in keys or values, non-finite numbers, excessive integer literals, and pathological nesting
  are errors and are never silently canonicalized. Valid Unicode and paired surrogate escapes remain
  valid. Artifact bindings also compare JSON types exactly, so boolean or floating-point attempts cannot
  match an integer attempt.
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

## Remediation evidence boundary

Creating new BYOX jobs requires an exact, externally validated backend gate and a complete chain of
source, job, artifact, and review evidence. The controller rejects aliases, extra authority files,
noncanonical workspaces, stale validations, unsupported labels, self-reported success, and inventories
that disagree with descriptor-pinned bytes. Reviewer input records include their own file/tree checksums
and are reconstructed from the builder artifact rather than trusted from review metadata.

Repair input trees are copied read-only before validation, so staged tree checksums deliberately hash
write bits removed from regular files. The validation-workspace checksum includes `PRIOR_BUILD` and
`PRIOR_REVIEW`; the published artifact checksum excludes them. Equality between those hashes is rejected.
The small pre-cutover compatibility registry is provenance, not a general legacy mode, and includes the
exact deployed attempt number to prevent replay under a newly fabricated attempt.
