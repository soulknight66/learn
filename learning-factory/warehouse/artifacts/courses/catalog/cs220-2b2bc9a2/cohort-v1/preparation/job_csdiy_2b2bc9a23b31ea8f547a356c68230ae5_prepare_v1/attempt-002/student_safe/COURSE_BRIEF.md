# CS220 Rust Engineering Kickoff

## What this packet is

This is a six-hour first study unit for **CS220: Programming Principles**. It is a kickoff, not the whole course. The unit was written by the course manager from a CSDIY catalog snapshot; it is **not** an official KAIST assignment and does not claim to reproduce the official course sequence.

The catalog describes CS220 as an introductory Rust course for learners who already know another programming language. This unit assumes you are comfortable with directed graphs and topological sorting. The algorithm should feel familiar so you can concentrate on software-engineering decisions in Rust.

## Unit focus

You will build a small dependency-planning library and command-line program. The work emphasizes:

- borrowing input while returning owned results;
- separating parsing, domain logic, and process I/O;
- using enums and `Result` for expected failures;
- specifying deterministic behavior rather than relying on collection iteration order;
- writing tests around contracts and boundary cases;
- using the formatter, compiler, test runner, and linter as an engineering feedback loop.

Budget about six focused hours. If Rust syntax is new, time-box syntax lookup and keep the implementation standard-library-only.

## Material boundary

Everything required for the kickoff is in this learner-safe packet. The catalog links to the KAIST course repository, course slides, the assignment collection, and *The Rust Programming Language*, but those linked contents were not retrieved or verified for this job. They are optional pointers, not assumed readings:

- Course repository: <https://github.com/kaist-cp/cs220>
- Course slides: <https://docs.google.com/presentation/d/17G3SwkE_tq0H3lTt9N0ysIbHhqDZBfHkoWD5LwwAKSo/edit#slide=id.p>
- Assignment collection: <https://github.com/kaist-cp/cs220/tree/main/src/assignments>
- Rust Book: <https://doc.rust-lang.org/book/>

The catalog explicitly lists no lecture recordings. Do not wait for recordings to begin this unit, and do not treat any linked collection as an assigned official unit unless a later course update verifies it.

## Working approach

Start from the public contract in `STUDY_TASK.md`, make one small behavior work end to end, and then grow the tests and implementation together. Prefer explicit, readable ownership and error choices over clever compression. Keep notes about design changes while you work; they will make the reflection and comprehension prompts more concrete.

You may use tools for syntax help if your learning setting permits it. You remain responsible for checking every suggestion, explaining the submitted code, and disclosing substantive assistance in your reflection.

Completing these activities can establish completion of this kickoff unit only after independent validation. It cannot establish completion of CS220 as a whole.
