# Study Task: Build a Fail-Closed Authorization Boundary

## Scenario

Build a local Python component for a fictional multi-tenant document service. It receives an authenticated principal, a requested action, and trusted resource metadata, then returns an authorization decision. A small command-line adapter exists only to exercise the boundary with invented JSON data.

In the intended architecture, authentication middleware establishes the principal and the document store establishes resource metadata. The action is requested by an untrusted client. The demonstration CLI necessarily reads all three from standard input, so it validates structure but cannot establish their authenticity. Document this mismatch; do not present the CLI as a deployable authorization service.

Do not add networking, persistence, cryptography, or a web framework. Use only the Python standard library.

## Functional contract

Implement a deterministic policy entry point equivalent to:

```text
authorize(principal, action, resource) -> decision
```

The exact Python types are your design choice. A decision must contain an `allowed` Boolean and one stable `reason` code.

A principal has:

- `subject_id`: an identifier;
- `tenant_id`: an identifier; and
- `role`: exactly one of `member`, `auditor`, or `admin`.

A resource has:

- `resource_id`: an identifier;
- `tenant_id`: an identifier; and
- `owner_id`: an identifier.

The supported actions are `read`, `write`, and `delete`. Apply these rules in order:

1. Invalid input never reaches the policy function and never produces an allow decision.
2. If principal and resource tenants differ, deny the request.
3. Within one tenant, an `admin` may perform any supported action.
4. Within one tenant, an `auditor` may read any resource and may not write or delete.
5. Within one tenant, a `member` may read or write a resource only when `subject_id` equals `owner_id`; a member may not delete.
6. Deny every remaining valid request.

Use these exact reason codes at the external boundary:

- allowed: `allow_admin`, `allow_auditor_read`, or `allow_owner`;
- denied: `deny_cross_tenant` or `deny_insufficient_privilege`; and
- malformed input: `invalid_input`.

The ordering above also resolves reason-code precedence. For example, a valid cross-tenant request is classified before any same-tenant role rule is considered.

## Strict JSON boundary

Provide `src/authz/` as an importable package with a `__main__.py`. This command must read exactly one JSON document from standard input:

```bash
PYTHONPATH=src python3 -m authz
```

The only accepted shape is:

```json
{
  "principal": {
    "subject_id": "alice",
    "tenant_id": "tenant-a",
    "role": "member"
  },
  "action": "read",
  "resource": {
    "resource_id": "doc-1",
    "tenant_id": "tenant-a",
    "owner_id": "alice"
  }
}
```

Treat that object as an example of shape, not as an expected test result. Enforce all of these boundary rules:

- the UTF-8 input is at most 4,096 bytes, including whitespace;
- the input is one JSON object, with only trailing JSON whitespace permitted;
- duplicate keys at any nesting level are invalid;
- the top-level and nested objects contain exactly the shown keys;
- every field value is a JSON string, not `null`, a number, a Boolean, a list, or an object;
- identifiers match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`; and
- roles and actions belong to their declared finite sets.

For a structurally valid request, write one JSON object containing exactly `allowed` and `reason`, followed by a newline, and exit with status 0. A policy denial is a valid decision and therefore also exits 0.

For any malformed, empty, oversized, non-UTF-8, duplicate-key, or schema-invalid input, write `{"error":"invalid_input"}` followed by a newline and exit with status 2. Do not emit a partial decision, raw input, identifiers, an uncaught traceback, or a different error response for different parse failures.

Keep JSON parsing/validation separate from the pure authorization policy so the two can be tested independently.

## Engineering evidence

Create the following artifacts:

- `src/authz/`: implementation of models, strict parsing, policy, and CLI adapter;
- `tests/`: deterministic `unittest` tests;
- `notes.md`: threat model, design decisions, decision table, assumptions, non-goals, and your answers to `COMPREHENSION.md`;
- `submission.md`: artifact map, exact commands run, observed results, and known limitations; and
- `debugging-log.md`: chronological hypotheses and experiments.

The review handoff carries these three Markdown files, so `submission.md` must be a compact evidence packet rather than a bare completion claim. Include:

- an inventory of every source and test file with its SHA-256 hash;
- the exact test and CLI commands, exit statuses, and captured standard output/error (label output as learner-captured, not independently verified);
- the policy entry point and the relevant strict-parser and CLI error-handling excerpts, with their source paths;
- representative table-driven and invariant-test excerpts, plus the discovered test count;
- a table of malformed-input classes with the observed response and exit status; and
- a clear list of unrun checks, failures, uncertainty, and remaining limitations.

Keep excerpts focused on this unit; do not paste third-party or unavailable course content. The hashes and transcript improve traceability but do not turn self-reported execution into harness-verified evidence.

Your threat model in `notes.md` must identify protected assets, plausible actors, trust boundaries, the provenance assumed for principal and resource fields, at least four abuse or misuse cases, fail-open/fail-closed behavior, and what remains outside this toy component.

Use this deterministic test command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Tests must include:

1. all 36 combinations formed by 3 roles, 3 actions, same-owner versus other-owner, and same-tenant versus cross-tenant;
2. explicit checks for allowed/denied reason codes and cross-tenant precedence;
3. programmatic invariant checks over the finite policy space, including tenant isolation, auditor non-mutation, and member ownership limits;
4. malformed boundary cases covering empty input, invalid JSON, invalid UTF-8, duplicate keys, missing keys, extra keys, wrong JSON types, invalid identifiers, unknown roles, unknown actions, trailing non-whitespace, and an oversized document; and
5. subprocess-level CLI checks for output shape and exit status on an allow, a policy denial, and malformed input.

Subprocess tests must use an argument array rather than a shell command, set a bounded timeout, and capture output. Test names and failure messages should make the violated rule identifiable. Do not use real names, credentials, tenant data, network access, or nondeterministic randomness.

In `debugging-log.md`, preserve at least three genuine engineering investigations. Each entry should state a hypothesis, the exact experiment or command, the observation, and the resulting change or conclusion. A planned boundary probe or deliberately injected local fault counts; an invented failure does not.

## Timebox

A suggested allocation is:

- 60–90 minutes: threat model, contract interpretation, and decision table;
- 2 hours: domain model, policy, and strict parser;
- 2–3 hours: systematic unit and process-boundary tests;
- 1 hour: refactoring and diagnostics review; and
- 1 hour: evidence, comprehension responses, and limitations.

Stop after 10 hours. If something remains incomplete, preserve the failing check or minimal reproducer and describe the gap honestly instead of expanding the scope.

## Submission boundary

Submit only this local kickoff work. Do not claim that it implements authentication, protects a deployed service, proves production security, completes an official MIT assignment, or completes MIT 6.858. Do not download missing course material for this task.
