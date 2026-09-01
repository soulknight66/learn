# Kickoff notes: threat models and a tested authorization boundary

## Scope

This work covers only the manager-authored kickoff unit described in the three learner-safe files. It is a local exercise, not an official MIT assignment and not evidence of completing MIT 6.858 or any wider course.

## Initial threat model

### Protected assets

- The confidentiality boundary between tenants: one tenant must not receive an allow decision for another tenant's resource.
- Document integrity as represented by write and delete authorization decisions.
- The integrity and provenance of `subject_id`, `tenant_id`, `role`, resource tenancy, and ownership.
- The integrity and stability of allow/deny decisions and their reason codes.
- Availability at the input boundary, within the explicit 4,096-byte limit.
- Diagnostic confidentiality: malformed input must not echo input, identifiers, or a traceback.
- The reproducibility of this unit's source, tests, hashes, and learner-captured results.

The component returns decisions; it does not hold or modify actual documents.

### Actors

- An ordinary or malicious client requesting an action.
- Authentication middleware, trusted in the intended architecture to establish the principal.
- A document store or metadata layer, trusted in the intended architecture to establish resource metadata.
- The service integration that calls the policy and later performs an operation.
- An operator or test harness running the demonstration CLI.
- A compromised, unavailable, or misconfigured upstream identity or metadata component.

### Trust boundaries and provenance

In the intended architecture, the requested action crosses an untrusted client boundary. The principal must come from authentication middleware rather than client claims, and resource tenancy and ownership must come from the document store for the exact resource that will be used. Those two sources are assumptions of this component, not facts it can prove.

The demonstration CLI has a different boundary: every byte on standard input, including the principal and resource objects, is untrusted. `src/authz/parsing.py` can establish byte length, UTF-8 validity, unambiguous JSON, exact schema, string types, identifier grammar, and finite role/action membership. It cannot authenticate a subject, prove a role assignment, or prove that metadata describes a real/current document.

The parser-to-policy boundary carries only `AuthorizationRequest` values containing `Role` and `Action` enums. The policy-to-operation boundary is also important: the later operation must use the same resource and current metadata on which the decision was based. This exercise has no operation layer, so it cannot enforce that condition.

### Assumptions

- In a real integration, authentication middleware supplies an authentic, current principal and role.
- The resource store supplies authentic, current metadata for the resource that will actually be operated on.
- Identifiers are case-sensitive opaque strings under the declared ASCII grammar.
- A request has exactly one role and one supported action.
- A decision is consumed promptly and only for its corresponding request.
- The local Python process and source are trusted; host compromise is outside this model.

### Abuse and misuse cases

1. A CLI caller claims `role: admin`. The JSON is structurally valid and the policy may allow it within the claimed tenant. This demonstrates why the CLI is not an authentication boundary.
2. An admin, auditor reader, or owning member targets a different tenant. The first policy check returns `deny_cross_tenant`, before any apparent privilege can allow the request.
3. A caller repeats an authority-bearing key, such as two `role` or `subject_id` keys, hoping different components choose different values. The object-pairs hook rejects duplicates at every nesting level.
4. A caller supplies a missing/extra field, a non-string value, a strange identifier, or an unknown role/action and hopes for coercion or a permissive default. Exact schema/type/enum checks return the one generic malformed response.
5. A caller supplies invalid UTF-8, deeply nested JSON, concatenated documents, or more than 4,096 bytes to trigger exceptional behavior. The boundary rejects these without invoking policy or emitting a traceback.
6. Resource ownership or tenancy changes after authorization but before use. The decision can then apply to stale metadata; a real integration needs transactional coupling or versioned revalidation.
7. Identity or metadata infrastructure is unavailable and the integration substitutes caller claims or stale/default metadata. Such substitution would fail open; the integration should instead deny or return unavailable.

### Fail-closed behavior and non-goals

Malformed input never reaches `authorize`: the CLI emits exactly `{"error":"invalid_input"}\n` and exits 2. A well-formed policy denial is a valid decision, so it emits `allowed: false` and exits 0. In a real integration, missing or unverifiable principal/resource provenance must not be converted into an allow. That security choice reduces availability during upstream outages.

Non-goals include authentication, document lookup, persistence, networking, cryptography, audit-log storage, rate limiting, revocation, concurrency control, atomic document operations, deployment hardening, and protection from a compromised host or trusted upstream. The CLI is only an invented-data adapter.

## Design

`src/authz/models.py` contains immutable tuple-like domain values and finite enums. `src/authz/policy.py` contains the pure `authorize(request) -> Decision` function and does no I/O. `src/authz/parsing.py` owns raw-byte decoding, duplicate detection, JSON/schema validation, and conversion to domain values. `src/authz/__main__.py` bounds input before parsing and maps every `InvalidInput` to the same external response.

The boundary counts raw bytes, reads only through byte 4,097 to detect overflow, decodes UTF-8 strictly, and uses `JSONDecoder.raw_decode`. Only JSON whitespace (`space`, tab, carriage return, newline) may surround the single document. An object-pairs hook rejects duplicates before dictionaries are constructed. Exact key sets prevent both missing and added fields; no value is coerced. Identifiers use the specified full-match expression, while roles and actions are converted to enums.

The policy assumes those validations already succeeded. Keeping it pure makes the 36 valid combinations easy to enumerate and keeps parse failures out of authorization logic. Stable output serialization is explicit rather than relying on dictionary order in Python 3.6.

## Decision table

The tenant check has precedence over every row below.

| Tenant relation | Role | Action | Ownership | Decision and reason |
|---|---|---|---|---|
| Cross-tenant | Any | Any | Either | deny, `deny_cross_tenant` |
| Same tenant | `admin` | Any | Either | allow, `allow_admin` |
| Same tenant | `auditor` | `read` | Either | allow, `allow_auditor_read` |
| Same tenant | `auditor` | `write` or `delete` | Either | deny, `deny_insufficient_privilege` |
| Same tenant | `member` | `read` or `write` | Owner | allow, `allow_owner` |
| Same tenant | `member` | `read` or `write` | Other | deny, `deny_insufficient_privilege` |
| Same tenant | `member` | `delete` | Either | deny, `deny_insufficient_privilege` |

`tests/test_policy.py::ExhaustivePolicyTests.test_all_36_policy_combinations` enumerates role × action × ownership × tenancy. Separate invariant tests range over tenant isolation, auditor non-mutation, member ownership/delete limits, and same-tenant admin behavior.

## Comprehension responses

### 1. Intended and demonstration boundaries

In the intended architecture, the client controls the requested action; authentication middleware establishes all principal fields, and the document store establishes resource fields. The CLI must treat all three objects as caller input. Its strict parser proves only syntactic and finite-domain properties. It can never authenticate the role or attest to resource ownership. This mismatch is explicit in the threat model and is why the CLI is labelled a demonstration adapter.

### 2. Caller-selected role

If an attacker sends a syntactically valid CLI principal with `role: admin`, the parser converts it to `Role.ADMIN`. For a same-tenant resource, `authorize` then permits any supported action with `allow_admin`; structural validation is not provenance. A real service must remove principal construction from the request body and accept it only from trusted authentication middleware. It must likewise fetch resource metadata from the trusted store instead of trusting the body.

### 3. Meaning and limits of all 36 cases

The exhaustive table establishes that this implementation maps every value in the declared valid role/action/ownership/tenancy product to the specified Boolean and reason. It also fixes cross-tenant precedence. It does not test authentication, correctness of upstream metadata, malformed bytes, the later operation, concurrency or TOCTOU, deployment configuration, side channels, dependency outages, or behavior after the policy is extended. Parser and subprocess tests address some separate local concerns, but still do not prove production security.

### 4. Rule ordering and reason precedence

An owning member reading across tenants appears to match the owner rule, and a cross-tenant admin appears to match the admin rule. Both must receive `deny_cross_tenant` because tenant isolation is evaluated first. Stable precedence prevents an accidental allow and gives operations one consistent classification for cross-tenant attempts. `test_cross_tenant_reason_precedes_role_and_ownership_rules` fixes this behavior for admin, auditor-read, and owner-member examples.

### 5. Parser/policy separation

The parser deals with representation and trust-boundary ambiguity; the policy deals with already typed meaning. Policy-only tests would miss a parser silently keeping the last duplicate `role`. CLI-only tests could report only an unexpected final denial if the auditor-write rule were wrong, making it harder to tell whether parsing, enum conversion, policy, or serialization caused the defect. Direct parser and policy tests localize those failures, while subprocess tests cover their composition.

### 6. Duplicate JSON names

If an edge component keeps the first `role` while the authorization process keeps the last, the same bytes can mean member to one component and admin to another. That creates both privilege and incident-analysis ambiguity. The object-pairs hook rejects a repeated key before constructing any object. `test_duplicate_keys_at_every_object_level_are_rejected` and the CLI malformed matrix include duplicates whose values are otherwise individually valid; the observed external result is the generic error and status 2.

### 7. Safe diagnostics

The current adapter deliberately emits no internal diagnostic, only a generic external error. A real service could record an internal event category such as `duplicate_key` or `invalid_utf8`, a bounded request/correlation token generated by the service, component version, and aggregate counters. Logs should have access controls, retention limits, and rate limiting. They should not contain raw input, identifiers, secrets, exception text derived from input, or schema-path detail returned to the caller. The external response must remain constant so categories do not become an oracle.

### 8. Time of check versus time of use

Suppose a member is authorized to write document `r` because metadata says that member owns it. Before the write, another transaction transfers ownership or moves/replaces the document, but the operation uses the old decision. A real system should authorize and mutate against the same database snapshot/transaction, lock the row where appropriate, or include a version and re-read/re-authorize immediately before an atomic conditional update.

### 9. A time-limited `support` role

New trusted data would include a grant identifier, subject, tenant/resource scope, allowed action, issuer, activation/expiry times, revocation state/version, and a trusted current time. Grant transitions would include issued → active → expired or revoked, with atomic persistence and audit evidence. Failure modes include stale cached grants, clock skew, revocation races, over-broad scope, and treating grant-service outage as active. Tests would cover tenant isolation, scope, exact activation/expiry boundaries, revocation before use, malformed grants, stale versions, clock behavior, outage fail-closed behavior, and concurrent revoke/use. No support role was added in this unit.

### 10. Dependency outage

Fail-open identity behavior would accept a caller-asserted or stale principal when the identity provider is unavailable; fail-open metadata behavior would use guessed/stale ownership. That preserves some availability but can grant unauthorized access. Fail-closed behavior denies the operation or returns service unavailable until authentic principal and current resource metadata can be obtained. It protects authorization at the cost of blocking legitimate work. This toy has no such dependencies, so it only documents the required integration behavior.

### 11. Debugging observation that changed my model

The managed `python3` was Python 3.6.8 and exposed `sys.executable == ''`. After the compatibility rewrite, subprocess tests still failed with `PermissionError: [Errno 13] Permission denied: ''`; a direct probe showed `shutil.which("python3")` resolved an executable. This changed my model from “a running Python process can always relaunch itself through `sys.executable`” to “interpreter identity is environment data that must be checked.” The test helper now uses `sys.executable or shutil.which("python3")`, and the exact required command subsequently discovered 23 passing tests. Details and the failed transcripts are in `debugging-log.md`.

### 12. Precise claims

This kickoff demonstrates a local standard-library implementation of the stated finite policy, strict boundary behavior for the tested malformed classes, reproducible unit/subprocess checks, and an explicit threat model for this component. Learner-captured runs passed on the workspace's Python 3.6.8 and the available Python 3.11.5.

It cannot support a claim that a deployed service is secure, that authentication/resource provenance is implemented, that document operations are atomic, that every denial-of-service or side-channel behavior is covered, that learning transfers to another system, that any official MIT lab or assignment was completed, or that MIT 6.858/the broader course was completed.
