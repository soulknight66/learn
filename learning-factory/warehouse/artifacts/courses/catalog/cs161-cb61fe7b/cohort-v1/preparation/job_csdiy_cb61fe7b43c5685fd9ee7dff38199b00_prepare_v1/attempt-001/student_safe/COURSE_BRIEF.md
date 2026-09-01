# UCB CS161: Computer Security — Kickoff Unit

This is a bounded, course-manager-authored kickoff inspired by the catalog scope of UC Berkeley CS161. It is not an official UC Berkeley lesson or assignment, and completing it does not mean completing CS161.

## Why this unit comes first

Security work begins by deciding what a system promises, who may act, and where trust enters. Strong algorithmic reasoning helps with invariants, but reliable security software also demands explicit boundaries, controlled state changes, careful APIs, adversarial tests, and reproducible evidence.

You will apply those habits to a small Go authorization core. The code is intentionally much smaller than a production file-sharing system so that you can inspect every security-relevant decision.

## Learning goals

By the end of this unit, you should be able to:

- describe assets, actors, trust boundaries, assumptions, and exclusions;
- turn an authorization matrix into invariants and fail-closed behavior;
- prevent callers from mutating stored data through Go slice aliasing;
- reason about atomic security-relevant transitions under concurrency;
- design negative and adversarial tests, not only happy-path examples; and
- attach command output to engineering claims.

## Scope and assumptions

The exercise is a single-process, in-memory policy component. A trusted adapter has already established the caller's identity. Authentication, networks, databases, persistence, encryption, key management, and user interfaces are outside this unit.

Those exclusions matter: the resulting package may enforce its stated in-process policy, but it is not a complete secure storage or file-sharing product.

## Available material

Everything required is local:

- [STUDY_TASK.md](STUDY_TASK.md) defines the build and evidence requirements.
- [COMPREHENSION.md](COMPREHENSION.md) contains the reasoning prompts.

The catalog also names a Summer 2020 course website, a textbook site, recordings, assignments, and a supplemental repository. Their contents were not retrieved or verified for this kickoff, so none is required and no missing external item should block your work.

## Suggested schedule

Budget about nine focused hours:

1. Threat model and policy table — 1.5 hours
2. API and state design — 1 hour
3. Implementation — 2.5 hours
4. Adversarial, collision, and concurrency tests — 2.5 hours
5. Comprehension responses and evidence — 1.5 hours

Stop at the stated boundary. Record a tempting extension as future work instead of silently expanding the system.

## What completion means

Submitting the listed artifacts makes the kickoff eligible for independent validation. Only a worker-harness-controlled validation result can mark this unit complete. Even a passing result applies only to this first unit; the broader course remains unexpanded and incomplete.
