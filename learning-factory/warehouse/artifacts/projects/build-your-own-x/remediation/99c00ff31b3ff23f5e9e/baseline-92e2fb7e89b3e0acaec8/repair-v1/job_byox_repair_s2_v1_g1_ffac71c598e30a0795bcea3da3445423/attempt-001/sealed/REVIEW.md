# Sealed implementation review

## Reviewed properties

- Lexer offsets never advance beyond the loaded byte count, and invalid bytes
  are reported by unsigned hexadecimal value.
- Literal accumulation checks range before multiplication/addition.
- Parser recursion and resolved AST depth are bounded independently.
- Declarations reject duplicate names first, then resolve initializers before
  installing their own symbol, which makes precedence deterministic and
  rejects accidental self-reference.
- Interpreter operations avoid signed-overflow undefined behavior.
- The backend balances temporary pushes and restores ABI call alignment.
- Both backends apply the same statement/loop fuel model and runtime messages.
- Both backends check each standard-output call and flush, report failures as
  status 66, and share an exact stable diagnostic.
- Assembly publication uses a temporary sibling and removes it after failure.
- Test subprocesses use argv arrays, bounded capture, temporary directories,
  fresh sessions, whole-group timeout cleanup, and no network.

## Residual findings

- Out-of-memory handling terminates the process immediately, so it cannot
  release already-owned allocations or distinguish phase-specific status.
- Diagnostic writes to standard error remain unchecked; if that stream itself
  fails, no secondary channel exists for reporting the failure.
- `fsync` covers the assembly file but not the containing directory after
  rename; crash durability is therefore incomplete.
- Generated executables are native code linked outside any sandbox.
- GCC/Clang overflow builtins and GNU assembler syntax narrow portability.
- No sanitizer, fuzzer, valgrind, profiler, cross-architecture, or independent
  validation evidence is claimed by this artifact.

These findings are consistent with `productionized: false` and the `PARTIAL`
label. They are not silently promoted into production claims.
