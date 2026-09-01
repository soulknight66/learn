# ASU CSE466 catalog kickoff: Linux process boundaries

## What this unit is

This is a bounded, course-manager-authored kickoff inspired by the catalog topic “Linux commandline: Program misuse, program interaction.” You will build and test a small Linux command runner. The focus is not an exploitation trick; it is the engineering discipline needed whenever one program starts and supervises another.

The catalog describes ASU CSE466 as a difficult, challenge-based systems-security course using C, Python, and x86 assembly. It reports 13 modules and 358 challenges, but the snapshot does not contain their names, order, challenge bodies, recording index, or validators. This kickoff is therefore **not** presented as an official ASU or pwn.college module. Completing it cannot establish completion of CSE466.

No external course page, video, textbook, repository, stream, or chat is required. The catalog says there is no textbook. Other links are discovery leads only and were not retrieved or verified for this unit.

## Why this is a useful first step

Strong algorithmic reasoning helps you define states, invariants, and bounds. Production systems add complications that a clean abstract model can hide: arguments cross a trust boundary, output pipes can block, child processes can outlive parents, clocks advance, signals race with exits, and logs can consume unbounded memory. The lab asks you to make those cases observable and testable.

By the end of this unit, you should be able to:

- distinguish an argument vector from a shell command string;
- describe a child process using explicit exit, signal, timeout, and spawn-failure states;
- bound retained output while continuing to supervise the process;
- clean up a timed-out local process tree and reap it;
- make behavioral claims through repeatable tests and captured evidence; and
- explain where an algorithmic invariant depends on an operating-system guarantee.

## Working assumptions

Use a local Linux environment with Python 3 and only the Python standard library. You should already be comfortable reading Python, using a terminal, writing basic tests, and reasoning about asymptotic space. Prior security-course content is not assumed.

Plan for six to eight focused hours. Stop at the specified boundary: one runner, harmless local fixtures, its tests, its evidence, and the written responses. Do not expand into shellcode, exploitation, privilege escalation, network scanning, or third-party targets.

## Safety and authorization boundary

Run only programs that you wrote as fixtures for this lab or ordinary local utilities used solely to check benign behavior. Do not use real services, other users' processes or files, course infrastructure, challenge endpoints, privileged execution, containers you do not control, or network targets. Do not paste secrets into arguments or evidence. Tests that create sleeping child processes must identify and clean them up.

If your implementation leaves a process behind, treat that as a failed test and clean it up before continuing. If a requirement appears to need elevated privileges or external access, it has been misunderstood: neither is part of this unit.

## What comes next—and what does not

The independent examiner will evaluate the submitted behavior and evidence. A passing result records only this manager-authored kickoff. Later course expansion must first retrieve and classify public official materials with provenance; the current catalog snapshot is not enough to reconstruct the course.
