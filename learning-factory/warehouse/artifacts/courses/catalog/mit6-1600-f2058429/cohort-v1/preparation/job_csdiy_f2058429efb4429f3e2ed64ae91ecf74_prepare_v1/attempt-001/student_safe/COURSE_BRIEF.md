# MIT6.1600 Foundations of Computer Security — Kickoff Brief

## Status and boundary

This pack prepares one **manager-authored kickoff unit**, not an official MIT unit and not evidence that you have completed an MIT module or course. The catalog describes a roughly 50-hour course spanning authentication, transport, platform, software, and human/end-user security. This unit covers one small authentication component in about five hours.

The catalog linked course websites and described recordings, lecture notes, and six labs. Those materials were not retrieved for this workspace. You do not need them for this unit, and you should not try to access gated or restricted material.

## Your unit

**Authentication Boundary: Engineer a Local Credential Verifier**

You will turn a compact threat model into a tested Python component that enrolls and verifies local password credentials. The point is not to build a complete login service. It is to practice the engineering work around an algorithm: defining a contract, protecting state, handling failures, controlling nondeterminism, and collecting executable evidence.

By the end of the unit, you should be able to:

- translate assets, adversary capabilities, and trust boundaries into component requirements;
- use an established standard-library password-derivation primitive without inventing cryptography;
- specify state invariants and externally visible failure behavior;
- test success, negative cases, malformed state, and randomness deterministically; and
- distinguish this educational component from a production authentication system.

## Expected background

You should be comfortable with discrete mathematics, basic computer systems, Python 3, functions and classes, byte strings, and `unittest`. No prior security course is assumed.

## Timebox

- Threat model and contract: 60 minutes
- Implementation: 90 minutes
- Tests and defect fixing: 90 minutes
- Engineering note and comprehension responses: 60 minutes

Stop after roughly five hours and document unresolved issues instead of silently widening the project.

## Safety and scope

Work only with synthetic users and passwords in a local process. Do not send credentials over a network, probe a service, reuse a real password, or test another person's account. Sessions, authorization, recovery, MFA, rate limiting, databases, web frameworks, and distributed deployment are deliberately out of scope.

Completing the files is a submission, not a completion decision. Completion requires independent validation of the artifacts and their behavior.
