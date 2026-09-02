# Review: identifier lowering

Review `unsafe.js`. Assume `emitDeclaration` receives AST fields produced from attacker-controlled source or a deserialized tool protocol; the caller then executes the returned JavaScript in a trusted test process.

Submit findings with severity, triggering examples, impact, and a remediation. Address at least:

- JavaScript reserved words;
- syntactically active text in a handcrafted AST;
- collisions with runtime helper names;
- consistency between declarations and reads;
- the difference between identifier validation and safe lowering.

Do not merely add a blacklist. Propose tests and a representation that stays safe if the source language later expands its identifier grammar.
