# Unit brief: Lab 1 record — bounded memory-corruption model

## Identity and classification

- Course: MIT 6.858: Computer System Security
- Batch sequence: 1
- Unit ID: `unit_8b2011001dc8b37c0dff9f1dd438e897`
- Source-record title: Lab 1
- Record classification: `explicit_official_course_unit`
- Source metadata availability: `DESCRIBED`
- Source reference: `docs/系统安全/MIT6.858.en.md#L15`
- Prepared-packet classification: original agent-generated practice material

The supplied snapshot explicitly classifies the normalized Lab 1 record as an official course unit. That classification is preserved here. It does **not** mean that official Lab 1 material is present: the snapshot supplies only a one-sentence catalog description relating the Zoobar application and buffer-overflow attacks.

No official specification, starter code, environment instructions, tests, lecture material, or course-site content is available in this workspace. None was fetched. This packet is not an MIT assignment, a reconstruction of one, or a substitute that can confer official credit.

## What is available

This packet provides a newly authored, self-contained implementation and debugging exercise. You will build a deterministic Python model of a small byte frame, demonstrate how an unchecked copy can corrupt adjacent authorization metadata, and implement a fail-closed boundary check. The model is intentionally memory-safe: it teaches boundary reasoning without asking you to exploit native memory, a real application, or a remote system.

## Learning targets

By the end of the task, your submitted evidence should make it possible to inspect how you:

- translate a memory-layout description into explicit ranges and invariants;
- connect an out-of-bounds write to an authorization-integrity failure;
- separate byte-frame mutation, authorization policy, and request handling;
- validate before mutation and reject rather than silently truncate;
- test boundary partitions and request isolation deterministically;
- design diagnostics that are useful without retaining untrusted payload bytes; and
- explain what a semantic model can and cannot establish about native memory safety.

The supplied learner profile suggests comfort with algorithms and mathematical reasoning, so the task omits elementary Python guidance. It emphasizes architecture, maintainability, debugging evidence, and operationally safe diagnostics. That profile is used only to set emphasis; it is not a claim of mastery.

## Scope and safety boundary

Work entirely with the local Python semantic model defined in `LEARNING_TASK.md`.

- Do not access a network service or course website.
- Do not probe Zoobar, MIT infrastructure, or any third-party target.
- Do not use native unsafe-memory interfaces, real credentials, or copied exploit code.
- Do not seek hidden tests, examiner files, other learners' work, or unstaged course material.
- Use only Python's standard library.

The exercise models one integrity failure. It does not model a C ABI, stack direction, compiler behavior, address randomization, control-flow hijacking, authentication, deployment, or the full security of a web application.

## Completion boundary

Preparing or reading this packet is not evidence that you studied, passed, demonstrated transfer, completed an official lab, or completed the course. A self-check is reflective only. Any evaluation must come from independently validated examiner evidence and remains limited to this generated practice task.
