# Alternative solution architectures

The shipped reference uses a conventional lexer/parser plus fork/exec process
groups. Several other designs can satisfy the same public behavior.

## Heap-owned AST

Replace fixed arrays with vectors of commands, arguments, and ordered
redirections. This removes pedagogical capacities and makes later compound
syntax easier. It requires a single, well-tested destructor that handles every
partially initialized state, plus checked growth arithmetic. Arena allocation
is a useful middle ground: all syntax for one input line can be freed together
after the job no longer needs it.

## Streaming parser with immediate execution

A parser could launch stages while reading tokens, reducing retained syntax.
For this language that is a poor default because a late syntax error could
occur after an early command has already run. A transactional preflight pass or
complete AST is preferable when the contract says syntax errors have no
execution side effects.

## `posix_spawn` backend

`posix_spawnp` with file actions can replace much fork-side setup and may behave
better in a large, multi-threaded parent. Process-group and terminal handoff
still require careful coordination, and platform support for spawn attributes
varies. Parent-run stateful builtins remain necessary.

## `signalfd`, kqueue, or a larger event backend

The reference combines a coalescing flag with a nonblocking self-pipe and
`pselect`. Linux `signalfd`, a kqueue process filter, or another platform event
backend could remove the signal-handler write and integrate more event types,
but would narrow portability. Every design must still drain `waitpid`; the
wakeup count is not the child-event count.

## Dedicated job-control reactor

A larger shell can centralize child state, terminal transitions, and input in
one event loop while evaluators send it launch requests. This clarifies
ownership for asynchronous UI features but introduces message ordering and
shutdown protocols that would obscure the core lesson here.

## Child-only builtin policy

One could run only state-changing builtins in the parent and run `pwd` or
`jobs` in a child. That reduces parent redirection exposure for pure builtins,
but job data then needs a consistent snapshot and output/error behavior differs
by builtin. The reference's uniform standalone-foreground rule is easier to
explain.

## Rich grammar architecture

Supporting `;`, `&&`, `||`, subshells, or expansions should introduce distinct
AST node kinds and an evaluator that returns statuses. Expansion should consume
quote-aware word parts and produce argv fields before execution. Retrofitting
these features into a flat pipeline struct would create ambiguous precedence
and ownership; a deliberate parser redesign is the safer alternative.

## Platform abstraction

A portable command runner could define backends for POSIX process groups and
for Windows processes/job objects. The parser and high-level job model can be
shared, but descriptor wiring, signal semantics, executable lookup, and console
ownership cannot. Treat those as backend interfaces rather than scattered
preprocessor branches.
