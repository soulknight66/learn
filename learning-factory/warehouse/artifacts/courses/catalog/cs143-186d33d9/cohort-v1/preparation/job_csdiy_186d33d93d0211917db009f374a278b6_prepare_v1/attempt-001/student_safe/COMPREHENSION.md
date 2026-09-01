---
course_id: course_186d33d93d0211917db009f374a278b6
unit_id: unit_01_minicool_lexer_engineering
audience: learner
provenance: manager-authored comprehension prompts for the MiniCOOL-0 kickoff
validation_label: LEARNER_SAFE_PREPARED_UNVALIDATED
---

# Comprehension prompts

Answer each prompt concisely in your submission. Do not give only general compiler definitions: cite at least one relevant source file, function or class, and test name for prompts 2–6.

1. Draw or describe where the lexer sits in a complete compiler pipeline. What information does it remove, preserve, and add for a future parser? Name two later compiler responsibilities that deliberately remain outside this unit.

2. Identify one input where consuming a valid token immediately would conflict with longest match. Trace how your implementation decides the token boundary and point to a test that would fail if it chose too early.

3. State a loop invariant for your main scanning loop. Use it to argue both that token positions are correct and that scanning terminates even after malformed input.

4. Explain how your representation handles nested block comments. Give tight time and auxiliary-space bounds in terms of input length and maximum nesting depth, and connect each bound to concrete operations in your code.

5. Choose one recovery case—invalid character, invalid string escape, unterminated string, or unterminated comment. Explain the recovery boundary, show why it cannot duplicate or skip an unrelated later token, and cite two tests that distinguish your behavior from plausible faulty implementations.

6. Suppose a later parser needs token values and structured diagnostics without parsing CLI text. Describe the smallest interface change, if any, that you would make. Explain how your current component boundaries and tests reduce the risk of that change.

7. Report your exact clean-build and test commands and their observed result. Identify one remaining limitation or uncertain design choice. If none remains, name the strongest untested assumption instead. This is an evidence report, not a claim that the wider course is complete.
