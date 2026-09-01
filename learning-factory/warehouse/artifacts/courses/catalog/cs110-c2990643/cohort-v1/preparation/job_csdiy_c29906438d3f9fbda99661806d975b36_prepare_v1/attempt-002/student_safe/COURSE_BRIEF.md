# CS110: Principles of Computer Systems — Kickoff Brief

## What this packet is

This is one manager-authored kickoff unit inspired by the catalog description of Stanford's CS110. It is not presented as Stanford course material or as the official first unit. The catalog describes a much larger, approximately 150-hour course about program behavior, system components, parallel execution, and software spanning machines. Completing this packet completes neither that course nor any Stanford requirement.

The supplied catalog contains descriptions and external links, but their contents were not retrieved or verified for this packet. You do not need those links to do the work below.

## Audience and assumptions

This unit is for a learner who is already strong at algorithms and can write moderately complex programs, navigate a larger codebase, reason about memory, and use Unix, GDB, Valgrind, and Make. You should be comfortable with C or C++; the implementation target here is C++17 on a POSIX-compatible Unix system.

## Unit focus

You will build a small but serious process supervisor. The algorithm is not the hard part. The work is in defining observable behavior, handling operating-system failure modes, preserving argument boundaries, managing process lifetime, and producing tests another engineer can trust.

By the end of the unit, you should be able to:

- explain the distinction between a process, a program image, and a process group;
- launch a program without invoking a command shell;
- redirect child file descriptors without accidentally changing the parent;
- distinguish normal exit, signal termination, launch failure, and timeout;
- guarantee that the direct child is reaped along every parent control path;
- turn lifecycle and failure requirements into automated integration tests;
- document design tradeoffs so a new maintainer can audit the implementation.

## Boundary

This unit does not attempt to cover threads, synchronization primitives, filesystems, networking, distributed systems, or the complete CS110 schedule. It also does not reproduce any linked lecture, textbook, lab, assignment, starter framework, test suite, or solution.

Plan for about ten focused hours. Stop at the stated interface and deliverables; expanding the tool into a general shell, daemon, container runtime, or distributed scheduler is outside this unit.
