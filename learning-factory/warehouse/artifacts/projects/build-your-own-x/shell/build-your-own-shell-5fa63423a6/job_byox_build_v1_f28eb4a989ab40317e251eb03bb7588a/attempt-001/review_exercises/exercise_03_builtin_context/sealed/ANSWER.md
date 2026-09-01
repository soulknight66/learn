# Sample review: builtin execution context

## Critical: dispatch ignores pipeline and background context

Any builtin first stage bypasses the entire pipeline launcher. `cd /tmp | pwd`
changes the parent directory and never starts `pwd`; `cd /tmp &` changes the
parent synchronously; `exit &` terminates the shell; and `exit | cat` exits
without launching `cat`. This violates both syntax and isolation.

The dispatch policy is:

| Context | Execution location |
| --- | --- |
| one command, foreground, builtin | parent shell |
| one command, background, builtin | child in a new job process group |
| pipeline stage, builtin | that stage's child in the pipeline group |
| any external command | child in the pipeline group |

State changes by a child-context `cd` or `exit` affect only that child. `fg` and
`bg` need an explicit child-context policy; usually they report that job-control
builtins require the main shell rather than trying to manipulate a copied job
table.

## Critical: parent descriptors are never restored

After `pwd > out`, shell stdout still refers to `out`, so later command output
and possibly prompts go there. Before applying parent-builtin
redirections, duplicate each affected standard descriptor. Apply the parsed
redirections, invoke the builtin, flush output, and restore with `dup2` on one
cleanup path. Close every saved/opened descriptor and preserve the intended
builtin status across restoration.

If opening an output path fails after a valid input redirect was installed,
restoration must still occur and the builtin itself must not run. Duplicate
same-stream redirections are rejected by the parser before this function; they
must never be collapsed silently into one path.

## High: failed redirection leaks a descriptor

When `open` succeeds and `dup2` fails, the combined condition returns without
closing `opened`. Split acquisition from installation or route both through
cleanup. Also handle interrupted calls according to the project's syscall
policy.

## High: name dispatch is ambiguous

Testing only the first character makes unrelated names select builtins if this
function is called incorrectly (`catapult` becomes `cd`, for example). Dispatch
should use the builtin identity already established by an exact lookup, or
exact `strcmp` matches. `exit` must validate its optional numeric argument and
return a request/status to the main loop; a helper calling `exit(0)` cannot
restore redirections or perform shell cleanup.

## Medium: buffering crosses descriptor changes

`stdio` data buffered before redirection can be flushed to the wrong file, and
builtin output can remain buffered until after restoration. Flush relevant
streams before descriptor replacement and after builtin output, or use a
carefully checked descriptor-level output API.

Tests should assert the dispatch matrix, parent working directory, complete
pipeline output, background responsiveness, duplicate-redirection rejection,
descriptor restoration after success and failure, and validated `exit`
behavior.
