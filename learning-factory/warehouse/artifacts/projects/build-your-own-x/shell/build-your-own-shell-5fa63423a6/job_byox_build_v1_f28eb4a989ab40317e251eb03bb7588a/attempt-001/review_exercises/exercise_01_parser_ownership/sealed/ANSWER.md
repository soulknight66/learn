# Sample review: parser ownership and capacity

## High: every argv pointer dangles and aliases

`current` is one stack object reused on every loop iteration. Every assignment
stores the same `current.text` address, so later tokens overwrite earlier
arguments; after return, all pointers refer to dead stack storage. Seeing valid
text inside the loop does not establish postcondition validity. Depending on
stack reuse, execution can receive the last word repeatedly or arbitrary bytes.

For the starter's documented borrowing contract, decoded words can be compacted
into the caller's writable input line and argv can point at their stable starts;
the caller already promises that line outlives execution. For an owning parser
like the sealed reference, duplicate each argument into command-owned storage
and free it through the pipeline destructor. Adding inline word storage is a
third fixed-capacity option if the public struct may be extended. Each strategy
must check length and terminate. An explicitly empty WORD is a present pointer
to a zero-length string, not the NULL pointer terminating argv.

## Medium: capacity failure is checked after mutation

For the ninth argument, `argc` is 8 and the assignment writes slot 8, which was
reserved for the terminating NULL, then increments to 9. With these exact array
dimensions the write is not out of bounds, and the function returns before a
slot-9 terminator write; it nevertheless leaves malformed partial output. On a
fifth command, `command_index` and `command_count` become invalid before the
function returns, though this exact code returns before indexing `commands[4]`.
These are error-postcondition bugs rather than demonstrated memory corruption.
All prospective counts and indices should still be checked before mutation or
write, especially so a later refactor cannot turn them into an overrun.

Capacity policy should be tested at limit-1, exactly the limit, and limit+1,
with a canary around the output object under ASan/UBSan.

## High: no argv terminator is established after words

The initial `memset` happens to leave unused pointer slots NULL, but exactly
`MAX_ARGS + 1` writes and error returns make this implicit and unsafe. More
importantly, pointer ownership is already invalid. A successful append routine
should write the argument into owned storage, increment `argc`, and explicitly
set `argv[argc] = NULL` as one checked operation.

## High: empty commands are accepted

Leading, adjacent, and trailing PIPE tokens all create commands with `argc ==
0`. Passing their argv to execution violates the grammar and can lead to a NULL
program name. Parsing must reject a pipe unless the current command already has
a command word, and it must verify the final command after the loop. A zero
token input is also not a one-command pipeline; it should be classified as an
empty input/no-op or parse error by the documented caller contract.

## Medium: error output is partially populated

Every error leaves counts and pointers in a partly mutated object. The safest
fixed-capacity pattern is to parse into a local zeroed candidate and assign it
to `*output` only after full validation. Alternatively, document and enforce a
reset-on-error postcondition. In either case execution must be gated strictly on
parse success.

Regression cases should include empty quoted arguments, maximum-length owned
words, reused source/token buffers after parsing, all invalid pipe placements,
and all capacity boundaries.
