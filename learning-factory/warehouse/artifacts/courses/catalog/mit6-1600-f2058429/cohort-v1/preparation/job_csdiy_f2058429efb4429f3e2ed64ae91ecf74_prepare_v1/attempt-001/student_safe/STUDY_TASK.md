# Study Task: Engineer a Local Credential Verifier

## Goal

Build a small Python 3 component that can enroll a synthetic local user and later decide whether a supplied password matches the stored credential. Treat security properties, failure behavior, testability, and documentation as part of the implementation.

Use only the Python standard library. Your component is educational and local: it must not open sockets, call external services, collect real credentials, or become a web application.

## Deliverables

Create these files:

```text
authn/verifier.py
tests/test_verifier.py
THREAT_MODEL.md
ENGINEERING_NOTE.md
COMPREHENSION_RESPONSES.md
```

The test suite must run from the submission root with:

```bash
python3 -m unittest discover -s tests -v
```

## Required public behavior

Expose a `CredentialStore` with these operations (minor naming differences are acceptable if documented and used consistently):

```text
enroll(user_id: str, password: str) -> None
verify(user_id: str, password: str) -> bool
```

Define and document the following behavior before implementation:

- what constitutes a valid user identifier and password, including explicit size limits;
- what happens on a duplicate enrollment (it must not silently replace a credential);
- which invalid inputs raise a programming/input error;
- that a well-formed attempt with a wrong password or unknown user returns the same public result;
- how Python strings become bytes and whether any Unicode normalization is performed; and
- which aspects of stored credential state are private implementation details.

## Security and state requirements

Your implementation must satisfy all of these constraints:

1. Store no plaintext password and no reversibly encoded password.
2. Derive the stored verifier with `hashlib.pbkdf2_hmac` using SHA-256. Do not implement a hash, cipher, password KDF, or comparison algorithm yourself.
3. Generate a fresh salt of at least 16 bytes for every enrollment using `os.urandom`, `secrets`, or an injectable callable whose production default uses an operating-system source.
4. Make the iteration count part of each stored record. Use a configurable default of at least 600,000 iterations for this exercise, and validate the configuration. Treat this as an exercise baseline, not a timeless production recommendation.
5. Give every record an explicit format/version and algorithm identifier so malformed or unsupported state can fail closed.
6. Compare derived verifiers with `hmac.compare_digest` rather than ordinary equality.
7. For an unknown user, perform one dummy derivation with the configured algorithm before returning `False`. Do not claim that this makes the whole operation perfectly constant-time.
8. Return the same public failure value for an unknown user and a wrong password. Do not log or print user passwords, derived verifiers, or salts.
9. Refuse malformed stored records and unsupported versions rather than guessing or authenticating.
10. Keep storage in memory. Persistence, concurrency, work-factor upgrades, and account lifecycle are analysis topics, not implementation requirements.

Nondeterministic values must come through a small test seam. The production path must still choose secure random bytes by default. You may choose the private record representation, but your tests and engineering note must explain how its invariants are observed without adding an unsafe production API.

## Work sequence

### 1. Write the threat model

In `THREAT_MODEL.md`, identify:

- the assets this component handles;
- trusted and untrusted inputs;
- the component's trust boundary;
- at least four plausible misuse or failure cases, including disclosure of stored state and user enumeration; and
- controls implemented here versus controls explicitly deferred to a larger system.

Keep the model tied to this local component. Do not describe attacks on a real service.

### 2. Freeze the contract and invariants

Before coding, add a short contract section to `ENGINEERING_NOTE.md`. State the public behavior above and at least five invariants for a stored record. Include your input-limit and Unicode decisions. If you revise a decision while testing, record the revision and why.

### 3. Implement the component

Write the smallest implementation that meets the stated contract. Separate input validation, derivation, record handling, and public operations enough that each can be reasoned about. Keep dependencies and mutable global state out of the design.

### 4. Build deterministic tests

Your suite must include independent tests for:

- successful enrollment and verification;
- rejection of a wrong password and an unknown user;
- duplicate enrollment behavior;
- invalid and boundary-size inputs;
- distinct salts for two enrollments of the same synthetic password;
- deterministic behavior when a controlled byte source is injected;
- absence of the plaintext password from stored state and text representations;
- malformed record and unsupported-version failure;
- use of a dummy derivation on the unknown-user path; and
- configuration validation.

Do not use wall-clock timing assertions; they are noisy and do not prove side-channel resistance. Use a mock, spy, or another deterministic observation to check that the derivation path runs.

### 5. Review the engineering gap

Finish `ENGINEERING_NOTE.md` with:

- the command you ran and its observed test result;
- a mapping from each threat-model control to implementation and test evidence;
- two design alternatives you rejected and the tradeoff for each;
- production concerns intentionally omitted from this unit; and
- one safe next change, including the new tests it would require.

Answer the separate comprehension prompts in `COMPREHENSION_RESPONSES.md`. Base each response on your own design and point to a relevant function, invariant, or test where requested.

## Definition of submitted

The work is ready for independent checking when every deliverable exists, the documented command passes from a clean local process, no test depends on real time or a network, and the written claims match the code. A passing self-written suite alone does not establish completion.
