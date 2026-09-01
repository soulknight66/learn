---
unit_id: unit_01_minicool_lexer_engineering
provenance: learner-authored from the three learner-safe course files and local experiments
validation_label: LEARNER_ATTEMPT_UNVALIDATED
---

# MiniCOOL-0 kickoff notes

Scope: only `unit_01_minicool_lexer_engineering`. This is a manager-authored
MiniCOOL-0 exercise, not a claim of COOL compatibility or completion of a
compiler course.

## Contract inventory

- Input is a byte sequence. Bytes `0x00`–`0x7f` use the specified ASCII rules;
  higher bytes become one `ERROR_INVALID_CHAR` each.
- A cursor owns `offset`, one-based `line`, and one-based `column`. Exactly one
  helper advances it: LF increments the line and resets the column to 1; every
  other byte increments the column.
- The scanner is a library component returning ordered records. Formatting,
  file access, argument checking, and exit status belong to the CLI component.
- Recognition priority is whitespace/comments, strings, maximal identifiers
  and integers, multi-byte operators, single-byte punctuation, then one-byte
  invalid-character recovery. Context makes comment openers take priority over
  their component punctuation.

## State sketch made before coding

The main state is `NORMAL`. Each iteration either delegates to one of the
bounded states below or consumes at least one byte.

| State | Entry | Transitions and consumption | Exit/evidence |
|---|---|---|---|
| `NORMAL` | start or after a complete construct | whitespace consumes one; identifier/integer consumes a maximal nonempty run; operators consume one or two; an invalid byte consumes one | repeats until offset equals input length, then emits one EOF |
| `LINE_COMMENT` | `--` | opener consumes two, body consumes until LF without consuming LF | returns to `NORMAL`; LF is handled there |
| `BLOCK_COMMENT(depth)` | `(*` | opener consumes two; nested `(*` increments depth; `*)` decrements it; otherwise one byte is consumed | returns at depth zero, or emits one outermost unterminated-comment error at EOF |
| `STRING(clean)` | `"` | valid ordinary bytes consume one; valid escapes consume two; closing quote consumes one | emits the complete raw `STRING` only when still clean |
| `STRING(tainted)` | first invalid escape/control byte | each bad unit emits/buffers a focused error and consumes one or two; valid content is consumed but never becomes a partial string | closing quote is consumed and returns to `NORMAL`; LF is left for `NORMAL` |

Lookahead never advances the cursor. No transition consumes zero bytes and
returns to the same nonterminal state. EOF is emitted outside the loop, so it
cannot be duplicated.

## Initial hypotheses to verify

1. Checking a fixed two-byte candidate before its one-byte prefix is sufficient
   for longest match (`<=` before `<`, `<-` before `<`, and `--` before `-`).
2. A single nesting-depth counter is enough for block comments because only the
   outermost opening position is needed for an error. It should use constant
   auxiliary records rather than a delimiter stack.
3. Centralizing byte advancement should make all token starts correct without
   category-specific line/column repair.
4. For an invalid escape, retaining string context until quote/LF/EOF prevents
   the suffix from being mis-tokenized as identifiers or punctuation.
5. A generated input with many fixed-size identifiers can verify output shape
   and exact byte consumption without treating wall-clock timing as evidence.

## Explicit edge decision

The packet specifies invalid-escape recovery and unterminated-string recovery
independently but does not give a combined example. If both occur in one
string, the implementation will preserve source-position ordering: it will
report the outer unterminated span first, then buffered focused errors within
that span. This overlapping diagnostic representation is an explicit design
choice, not a claim about full COOL behavior.

## Lessons after the vertical slice

- Longest match is easier to audit when lookahead and consumption are separate:
  `starts_with` never moves the cursor, while only `advance` changes position.
- A depth counter is strictly smaller than a delimiter stack for this contract;
  inner opening positions never appear in a successful token or the required
  unterminated-comment error.
- Recovery boundaries are part of the token contract. Consuming the closing
  quote after an invalid escape prevents valid-looking characters inside that
  malformed string from becoming unrelated tokens.
- Test infrastructure carries isolation assumptions too. The first CLI harness
  assumed `/tmp`; the workspace disproved that assumption, so temporary files
  now live under the repository's disposable build directory.
- Wall-clock speed is noisy evidence. The long-input test instead checks 20,000
  maximal identifiers, sampled boundaries, token count, and exact EOF position;
  the linear argument comes from monotonic cursor operations in the source.
