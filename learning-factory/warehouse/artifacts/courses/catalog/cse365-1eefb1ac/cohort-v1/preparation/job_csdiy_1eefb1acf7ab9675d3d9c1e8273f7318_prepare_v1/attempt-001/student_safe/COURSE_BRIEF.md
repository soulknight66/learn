# ASU CSE365 kickoff: safe process boundaries

## Where this unit fits

The catalog describes CSE365 as an introductory cybersecurity course spanning Linux command-line misuse and privilege boundaries, web fundamentals, assembly, cryptography, and command, HTML, SQL, and stack injection. It also describes a challenge-led course with eight modules and 444 challenges.

This package is much smaller. It is a course-manager-authored kickoff aligned with the catalog's Linux command-line topic. It is not an official ASU or pwn.college unit, does not reproduce an official challenge, and does not establish progress through the rest of CSE365.

The supplied catalog snapshot contains links and short descriptions, not the lecture bodies or individual challenges. No external reading or account is needed for this unit.

## The engineering problem

An algorithm can be correct while the software around it is unsafe. A program that computes the right result may still confuse input with command syntax, follow a path outside its intended workspace, wait forever for a child process, leak ambient environment state, or report success without durable evidence.

You will build one deliberately small process adapter around a trusted local inspection helper. The adapter receives an action and a workspace-relative target from an untrusted caller. Your job is to turn that request into a narrow, testable interface while preserving the boundary between data and executable behavior.

## Outcomes

By the end of the kickoff, you should be able to:

- draw the trust boundary for a local subprocess call;
- state and enforce invariants for actions, arguments, paths, working directory, environment, process-group lifetime, time, and output;
- distinguish an argument vector from a shell command language;
- test behavior with hostile-looking but harmless filenames, path escapes, failures, and timeouts;
- leave reproducible implementation and test evidence for an independent reviewer.

## Boundaries and safety

Work only in a disposable local directory that you own. Use a helper program created for this exercise. Do not target system files, other users, external services, course infrastructure, or privileged commands. Do not disable host protections, change permissions outside the disposable directory, or use real credentials or secrets.

The work is intentionally bounded to roughly six hours. If the maximum eight-hour timebox expires, preserve the failing tests and describe the remaining gap instead of broadening the project.

Finishing this kickoff can count only toward this kickoff after independent validation. It cannot complete the course.
