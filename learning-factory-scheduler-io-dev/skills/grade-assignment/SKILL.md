---
name: grade-assignment
description: Independently grade a course or project submission using immutable tests, a rubric, and recorded evidence. Use for canonical assignments, revisions, hidden evaluations, conceptual exams, and adversarial validation where the student must not control success.
---

# Grade an assignment

1. Verify that the submission workspace contains no grader, reference, or other-student material.
2. Snapshot and hash the submission before evaluation.
3. Run the immutable grader in a separate network-disabled workspace with bounded time and resources.
4. Preserve commands, exit codes, test output, sanitizer/fuzzer evidence, and rubric observations.
5. Distinguish infrastructure failure from a wrong answer. Never rewrite the submission while grading.
6. Use conceptual judgment only after deterministic evidence; cite concrete locations and behavior.
7. Return PASS, REVISE, FAIL, PARTIAL, or BLOCKED with score, evidence, and missing coverage.
8. Let the orchestrator apply completion policy. Do not mark the authoritative job state yourself.
