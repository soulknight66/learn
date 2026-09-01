# Reference review

## Correctness review

The implementation follows the published grammar and evaluates compiled code only after a complete
successful parse. Scope resolution is reverse linear search and declaration insertion happens after
the initializer. Branch patching preserves an empty statement-level stack. Arithmetic checks precede
all potentially undefined signed operations.

The reference suites cover the public examples, all signed arithmetic fault classes, short-circuit
suppression of faults, shadowing, name lifetime, exact keyword matching, CRLF positions, repeated
execution, failure atomicity, and selected caller limits.

## Safety review

Dynamic array growth checks logical limits and multiplication size before allocation. Every VM operand
is range-checked before indexing. The CLI caps input before adding its terminator. Programs own their
code and constants; compiler-only borrowed names are gone before the API returns.

Known hardening gaps remain. Parser recursion has no separate syntactic nesting limit and can exhaust
the C call stack on hostile deeply nested input before the 1 MiB input cap. Diagnostics do not detect
write failure consistently. The CLI does not use stat to require a regular file and can block on a
special input on less restricted hosts. Allocation failures are grouped as system errors without
allocator injection tests.

## Portability review

The build targets C11 and uses fixed-width integer macros. It assumes an implementation provides
int64_t, as the public contract itself does. Source is treated as bytes. Output uses the portable
PRId64 format. The C API test was adapted to named workspace scratch files because anonymous tmpfile
creation was unavailable on the observed sandbox.

## Verdict

The implementation is a credible educational reference, not a production compiler. Its observed tests
support local confidence only. It has not been independently validated, fuzzed, benchmarked, audited,
or transfer-verified, so the artifact remains GENERATED and PARTIAL.
