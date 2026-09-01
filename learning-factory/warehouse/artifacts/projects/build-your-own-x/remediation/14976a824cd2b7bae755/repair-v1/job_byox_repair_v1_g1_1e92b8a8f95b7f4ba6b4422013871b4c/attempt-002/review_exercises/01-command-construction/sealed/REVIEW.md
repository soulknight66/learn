# Model review

## Critical: state-path escape

`name` is appended before it is validated. Values such as `../peer` or an
absolute component can address data outside the intended container entry.
`delete` then recursively removes that derived path. Validate the complete
name against the documented grammar before path construction, reject dot
entries, and pass `--` to filesystem tools. Keep deletion scoped to a
successfully resolved entry beneath a trusted state root.

## Critical: command injection and argv loss

`$*` merges the command vector, then `eval` parses the result as shell source.
Whitespace and glob characters change arguments; substitutions and separators
become code. Store command arguments only in positional parameters or arrays
and invoke an isolator as `"$isolator" "$rootfs" "$@"`. Never construct a
shell program from CLI data.

## High: rootfs is unsafe data and unsafe metadata

Create neither requires an absolute existing directory nor rejects `/`.
Unquoted expansions add splitting, globbing, and option parsing. A newline in
the path corrupts the line-oriented record. Validate and canonicalize the
rootfs before committing it, reject the host root and record delimiters, quote
every expansion, and use `--` where supported.

## High: create is not a transaction

The existence check is separated from `mkdir -p`, so concurrent creators can
both report success and overwrite metadata. Claim with an atomic operation
such as plain `mkdir` while holding the runtime's per-name coordination, write
metadata through a temporary file, and remove only state owned by the failing
creator.

## High: lifecycle and status are false

The candidate has no authenticated run record, no active-delete exclusion,
and no protection against concurrent runs. Its successful `echo` masks a
nonzero child status. Record PID plus process-start identity under a lock,
clean up only the matching record, and return the isolator's status after
cleanup. `ps` must verify liveness rather than trust a PID alone.

## Medium: CLI dispatch and diagnostics are ambiguous

`"$@"` treats the subcommand as an arbitrary function or executable name.
Argument counts are not checked; ordinary failures can still return zero;
diagnostics go to stdout without a stable prefix. Use an explicit `case`,
validate arity, keep ordinary output clean, and send `minictr:` errors to
stderr with nonzero status.

