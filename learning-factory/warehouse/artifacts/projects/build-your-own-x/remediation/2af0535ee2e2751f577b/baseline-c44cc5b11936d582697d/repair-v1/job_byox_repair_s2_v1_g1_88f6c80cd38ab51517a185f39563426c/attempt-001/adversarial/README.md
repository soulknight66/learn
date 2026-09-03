# Adversarial corpus generator

This harness-controlled directory describes deterministic edge inputs used to challenge a completed implementation. It contains no reference outputs or solution code.

`generate_cases.py OUTPUT_DIRECTORY` creates regular `.sprig` files for numeric overflow, declaration capacity, instruction capacity, parser nesting, long identifiers, invalid bytes, comment handling, and right-heavy stack use. It refuses a nonempty output directory so stale cases are not silently mixed in.

Generation alone proves no label. Each case must still be run with a bounded harness and judged against `REQUIREMENTS.md`; independent validators may add other cases.
