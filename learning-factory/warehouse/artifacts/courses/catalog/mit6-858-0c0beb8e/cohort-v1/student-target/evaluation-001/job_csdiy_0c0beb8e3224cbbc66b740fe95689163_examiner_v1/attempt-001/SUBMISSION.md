# Kickoff evidence packet

## Validation label and scope

**Validation label:** learner-captured local execution on 2026-08-31; not independently verified by a worker harness.

This packet covers only the bounded kickoff unit, **Threat Models and a Tested Authorization Boundary**. It does not claim production security, completion of an official MIT assignment, or whole-course completion. The only course inputs read were `COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`; no network or unavailable course material was used.

The required `python3` command resolved to CPython 3.6.8. A supplemental run used the available CPython 3.11.5 executable.

## Artifact map

| Artifact | Purpose |
|---|---|
| `src/authz/__init__.py` | Public package exports |
| `src/authz/models.py` | Immutable request/decision values and finite role/action enums |
| `src/authz/parsing.py` | Bounded UTF-8 JSON decoding, duplicate rejection, exact schema validation |
| `src/authz/policy.py` | Pure deterministic `authorize` policy |
| `src/authz/__main__.py` | Standard-input adapter, generic malformed response, stable serialization |
| `tests/test_policy.py` | All 36 valid combinations, precedence examples, and finite-space invariants |
| `tests/test_boundary.py` | Parser, short-read, malformed-input, and bounded subprocess checks |
| `notes.md` | Threat model, decisions, decision table, assumptions/non-goals, comprehension responses |
| `debugging-log.md` | Chronological hypotheses, failed runs, experiments, and conclusions |
| `submission.md` | This evidence packet |

## Source and test inventory

SHA-256 values were produced with this exact command:

```bash
sha256sum src/authz/__init__.py src/authz/__main__.py src/authz/models.py src/authz/parsing.py src/authz/policy.py tests/test_boundary.py tests/test_policy.py
```

| File | SHA-256 |
|---|---|
| `src/authz/__init__.py` | `7fe317dc30cdd7405fd2d5c0c91fc5f90d8a1b172875bfde0e5537680738cf07` |
| `src/authz/__main__.py` | `9f928be83630b708cd8e3850764900d4f70402bf5f469ba48cece404b562fbfe` |
| `src/authz/models.py` | `225ae21ce5553db6d8b06b2e9b7407c80d2d2c4c427e4a7c7830875a3654822f` |
| `src/authz/parsing.py` | `a296a7b98317161a2fed9451a9b735351dfe698fc7b052043b8816ed3c14d609` |
| `src/authz/policy.py` | `17c00ace19d9a7e714bd0fd4d5886349da52799bdd57bed11895753b51d3c4d3` |
| `tests/test_boundary.py` | `eb698fd7c73c414f5a42e8b88cc3902b6c57031b7dbcb37a007a5a76a1ecb453` |
| `tests/test_policy.py` | `1b99eed53c3746895af3f9d3d835a50dba1bd2aa7105749ba3d88fcd3f312384` |

## Test transcript

Exact required command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Learner-captured exit status: `0`

Learner-captured standard output: empty. `unittest` wrote its verbose report to standard error.

Learner-captured standard error:

```text
test_short_reads_are_joined_until_eof (test_boundary.BoundedReadTests) ... ok
test_short_reads_stop_after_overflow_detection_byte (test_boundary.BoundedReadTests) ... ok
test_cli_allow_has_exact_shape_and_success_status (test_boundary.CliBoundaryTests) ... ok
test_cli_malformed_input_is_generic_and_status_two (test_boundary.CliBoundaryTests) ... ok
test_cli_policy_denial_is_a_successful_decision (test_boundary.CliBoundaryTests) ... ok
test_deeply_nested_malformed_input_has_controlled_rejection (test_boundary.StrictParserTests) ... ok
test_duplicate_keys_at_every_object_level_are_rejected (test_boundary.StrictParserTests) ... ok
test_empty_invalid_json_and_non_object_roots_are_rejected (test_boundary.StrictParserTests) ... ok
test_every_field_rejects_non_string_json_types (test_boundary.StrictParserTests) ... ok
test_identifiers_must_match_declared_ascii_grammar (test_boundary.StrictParserTests) ... ok
test_invalid_utf8_and_non_json_constants_are_rejected (test_boundary.StrictParserTests) ... ok
test_missing_and_extra_keys_are_rejected_at_each_level (test_boundary.StrictParserTests) ... ok
test_size_limit_counts_bytes_and_accepts_exact_limit (test_boundary.StrictParserTests) ... ok
test_trailing_non_whitespace_and_concatenated_documents_are_rejected (test_boundary.StrictParserTests) ... ok
test_unknown_role_and_action_are_rejected (test_boundary.StrictParserTests) ... ok
test_valid_request_becomes_typed_domain_values (test_boundary.StrictParserTests) ... ok
test_all_36_policy_combinations (test_policy.ExhaustivePolicyTests) ... ok
test_cross_tenant_reason_precedes_role_and_ownership_rules (test_policy.ExhaustivePolicyTests) ... ok
test_same_tenant_allowed_reason_codes_are_stable (test_policy.ExhaustivePolicyTests) ... ok
test_admin_same_tenant_invariant (test_policy.PolicyInvariantTests) ... ok
test_auditor_non_mutation_invariant (test_policy.PolicyInvariantTests) ... ok
test_member_ownership_and_delete_invariants (test_policy.PolicyInvariantTests) ... ok
test_tenant_isolation_invariant (test_policy.PolicyInvariantTests) ... ok

----------------------------------------------------------------------
Ran 23 tests in 0.735s

OK
```

The discovered count is 23 test methods. One method, `test_all_36_policy_combinations`, contains 36 named subtests formed by 3 roles × 3 actions × 2 ownership relations × 2 tenancy relations. The discovered method count must not be confused with the finite-case count.

Supplemental exact command:

```bash
PYTHONPATH=src /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s tests -v
```

Learner-captured result: exit `0`, 23 tests, `OK` (verbose report on stderr; stdout empty). The full chronological record, including two earlier failed runs, is in `debugging-log.md`.

## Direct CLI transcripts

### Allow

Exact command:

```bash
printf '%s' '{"principal":{"subject_id":"subject-a","tenant_id":"tenant-a","role":"member"},"action":"read","resource":{"resource_id":"resource-a","tenant_id":"tenant-a","owner_id":"subject-a"}}' | PYTHONPATH=src python3 -m authz
```

Learner-captured exit: `0`  
Learner-captured stdout:

```json
{"allowed":true,"reason":"allow_owner"}
```

Learner-captured stderr: empty.

### Policy denial

Exact command:

```bash
printf '%s' '{"principal":{"subject_id":"auditor-a","tenant_id":"tenant-a","role":"auditor"},"action":"delete","resource":{"resource_id":"resource-a","tenant_id":"tenant-a","owner_id":"subject-a"}}' | PYTHONPATH=src python3 -m authz
```

Learner-captured exit: `0`  
Learner-captured stdout:

```json
{"allowed":false,"reason":"deny_insufficient_privilege"}
```

Learner-captured stderr: empty.

### Malformed duplicate key

Exact command:

```bash
printf '%s' '{"principal":{"subject_id":"subject-a","subject_id":"subject-b","tenant_id":"tenant-a","role":"member"},"action":"read","resource":{"resource_id":"resource-a","tenant_id":"tenant-a","owner_id":"subject-a"}}' | PYTHONPATH=src python3 -m authz
```

Learner-captured exit: `2`  
Learner-captured stdout:

```json
{"error":"invalid_input"}
```

Learner-captured stderr: empty.

## Malformed-input observations

`CliBoundaryTests.test_cli_malformed_input_is_generic_and_status_two` ran every row below as a separate subprocess subtest. Each used an argv array, a minimal environment, captured streams, a three-second timeout, and a new process session. The passing method asserts the exact response, status, and empty stderr for each row.

| Input class | Learner-observed stdout | Exit | Stderr |
|---|---|---:|---|
| Empty input | `{"error":"invalid_input"}\n` | 2 | empty |
| Invalid JSON | `{"error":"invalid_input"}\n` | 2 | empty |
| Invalid UTF-8 | `{"error":"invalid_input"}\n` | 2 | empty |
| Duplicate key in nested object | `{"error":"invalid_input"}\n` | 2 | empty |
| Missing required key | `{"error":"invalid_input"}\n` | 2 | empty |
| Extra key | `{"error":"invalid_input"}\n` | 2 | empty |
| Wrong JSON value type | `{"error":"invalid_input"}\n` | 2 | empty |
| Invalid identifier | `{"error":"invalid_input"}\n` | 2 | empty |
| Unknown role | `{"error":"invalid_input"}\n` | 2 | empty |
| Unknown action | `{"error":"invalid_input"}\n` | 2 | empty |
| Trailing non-whitespace | `{"error":"invalid_input"}\n` | 2 | empty |
| 4,097-byte document | `{"error":"invalid_input"}\n` | 2 | empty |

Direct parser tests additionally cover whitespace-only input, non-object JSON roots, `NaN`/`Infinity`, duplicates at top/principal/resource levels, each field with `null`/number/Boolean/list/object values, invalid identifiers in each identifier field, concatenated documents, Unicode non-breaking trailing space, deeply nested input, and a valid request padded to exactly 4,096 bytes. A process probe recorded 4,096 bytes as decision/status 0 and 4,097 bytes as malformed/status 2; see `debugging-log.md`.

## Focused implementation excerpts

### Pure policy entry point — `src/authz/policy.py`

```python
def authorize(request: AuthorizationRequest) -> Decision:
    principal = request.principal
    resource = request.resource

    if principal.tenant_id != resource.tenant_id:
        return Decision(False, "deny_cross_tenant")
    if principal.role is Role.ADMIN:
        return Decision(True, "allow_admin")
    if principal.role is Role.AUDITOR:
        if request.action is Action.READ:
            return Decision(True, "allow_auditor_read")
        return Decision(False, "deny_insufficient_privilege")
    if principal.role is Role.MEMBER:
        is_owner = principal.subject_id == resource.owner_id
        if is_owner and request.action in (Action.READ, Action.WRITE):
            return Decision(True, "allow_owner")
    return Decision(False, "deny_insufficient_privilege")
```

### Duplicate rejection and one-document parsing — `src/authz/parsing.py`

```python
def _object_without_duplicates(pairs: Iterable[Tuple[str, Any]]) -> Dict[str, Any]:
    result = {}  # type: Dict[str, Any]
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result

_DECODER = json.JSONDecoder(
    object_pairs_hook=_object_without_duplicates,
    parse_constant=_reject_non_json_constant,
    strict=True,
)

def _decode_one_document(raw: bytes) -> Any:
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise InvalidInput from None
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise InvalidInput from None
    start = 0
    while start < len(text) and text[start] in JSON_WHITESPACE:
        start += 1
    if start == len(text):
        raise InvalidInput from None
    try:
        value, end = _DECODER.raw_decode(text, start)
    except (json.JSONDecodeError, _DuplicateKey, _NonJsonConstant, RecursionError, ValueError):
        raise InvalidInput from None
    if any(character not in JSON_WHITESPACE for character in text[end:]):
        raise InvalidInput from None
    return value
```

The remainder of `parse_request` requires exact top/principal/resource key sets, string leaf values, full identifier matches, and successful `Role`/`Action` enum conversion before constructing `AuthorizationRequest`.

### Bounded read and CLI error mapping — `src/authz/__main__.py`

```python
INVALID_RESPONSE = '{"error":"invalid_input"}\n'

def _read_bounded(stream) -> bytes:
    chunks = []
    remaining = MAX_INPUT_BYTES + 1
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)

def main() -> int:
    raw = _read_bounded(sys.stdin.buffer)
    try:
        request = parse_request(raw)
    except InvalidInput:
        sys.stdout.write(INVALID_RESPONSE)
        return 2
    decision = authorize(request)
    allowed_json = "true" if decision.allowed else "false"
    reason_json = json.dumps(decision.reason, ensure_ascii=True)
    sys.stdout.write(
        '{"allowed":' + allowed_json + ',"reason":' + reason_json + "}\n"
    )
    return 0
```

## Focused test excerpts

### Exhaustive table — `tests/test_policy.py`

```python
dimensions = itertools.product(Role, Action, (False, True), (False, True))
for role, action, same_owner, same_tenant in dimensions:
    with self.subTest(
        role=role.value,
        action=action.value,
        same_owner=same_owner,
        same_tenant=same_tenant,
    ):
        decision = authorize(make_request(role, action, same_owner, same_tenant))
        expected_allowed, expected_reason = expected_decision(
            role, action, same_owner, same_tenant
        )
        self.assertIs(type(decision.allowed), bool)
        self.assertEqual(expected_allowed, decision.allowed)
        self.assertEqual(expected_reason, decision.reason)
        self.assertEqual({"allowed", "reason"}, set(decision.as_dict()))
    observed_cases += 1
self.assertEqual(36, observed_cases)
```

### Representative invariant — `tests/test_policy.py`

```python
def test_tenant_isolation_invariant(self) -> None:
    for role, action, same_owner in itertools.product(Role, Action, (False, True)):
        with self.subTest(role=role.value, action=action.value, owner=same_owner):
            decision = authorize(make_request(role, action, same_owner, False))
            self.assertEqual((False, "deny_cross_tenant"), (decision.allowed, decision.reason))
```

Separate programmatic invariants cover auditor non-mutation, member ownership/delete limits, and same-tenant admins.

### Process boundary — `tests/test_boundary.py`

```python
return subprocess.run(
    [PYTHON_EXECUTABLE, "-m", "authz"],
    cwd=PROJECT_ROOT,
    env={"PYTHONPATH": str(SRC_ROOT)},
    input=raw,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    timeout=3,
    check=False,
    start_new_session=True,
)
```

## Failures, uncertainty, unrun checks, and limitations

No check was failing at final capture. Two earlier failures are retained in `debugging-log.md`: unsupported modern syntax/dataclasses under Python 3.6, and an empty `sys.executable` causing subprocess launch errors. Both have minimal reproductions and regression coverage or a verified fallback.

Unrun checks and uncertainty:

- No external fuzzer, load/resource benchmark, alternate JSON implementation, alternate operating system, non-CPython runtime, web integration, or deployed-service test was run.
- No authentication provider, metadata store, document operation, concurrency/TOCTOU transaction, grant revocation, rate limiter, durable audit log, or dependency-outage behavior was implemented or tested.
- Detailed internal diagnostics were designed in the threat model but intentionally not implemented; the toy CLI emits only the required external response.
- The hashes and transcripts establish traceability for learner-created local files, not independent harness validation.
- Exhaustion of the declared finite policy space says nothing about values outside the validated domain or future policy extensions.

Remaining security limitations:

- The CLI accepts caller-supplied principal and resource fields. It validates their shape but cannot establish their truth, so it is not a deployable authorization service.
- The component returns a decision but cannot ensure that a later operation uses the same, unchanged resource metadata.
- A compromised host, authentication layer, metadata layer, or consuming service is outside this component's protection.
- Passing local tests cannot prove absence of implementation defects, side channels, denial-of-service paths, or unsafe integration behavior.

Accordingly, this handoff supports evidence for this kickoff unit only.
