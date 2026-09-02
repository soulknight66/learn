# Public tests

`test_cinder.py` contains black-box examples for arithmetic, stack effects, parsing, definitions,
structured control flow, recursion, output, and representative failures. It invokes the executable
with an argv array, captures all streams, and enforces a three-second timeout.

Set `CINDER_BIN` to an absolute or relative executable path, then use unittest discovery as shown in
the root README. These cases are illustrative, not exhaustive; capacity edges, malformed nesting,
integer boundaries, and nontermination are independently checked elsewhere.
