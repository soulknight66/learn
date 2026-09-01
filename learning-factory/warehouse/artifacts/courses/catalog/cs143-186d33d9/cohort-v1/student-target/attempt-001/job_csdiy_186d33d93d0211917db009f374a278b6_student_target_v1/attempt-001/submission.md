---
unit_id: unit_01_minicool_lexer_engineering
provenance: learner-authored responses backed by the implementation and local test output
validation_label: LEARNER_ATTEMPT_UNVALIDATED
---

# MiniCOOL-0 bounded-unit submission

This submission covers only the manager-authored MiniCOOL-0 lexer kickoff. It
does not claim full COOL compatibility, completion of Stanford CS143, or
independent validation.

The library scanner is in `include/minicool/lexer.hpp` and `src/lexer.cpp`; the
CLI is `src/main.cpp`. Reproducible commands and component boundaries are in
`DESIGN.md`, while `tests/test_lexer.cpp` and `tests/test_cli.sh` contain the
automated evidence.

## Comprehension responses

### 1. Pipeline boundary

In a complete compiler, source bytes flow through the lexer before a parser:

`source bytes -> lexer -> token records -> parser -> syntax tree -> later passes`

The lexer removes ignored whitespace and comments. It preserves significant
source spelling, order, and the starting line/column of each token or lexical
error. It adds a token kind and a deterministic EOF record so a future parser
does not have to rediscover lexical boundaries. Type checking and target-code
generation are two later responsibilities deliberately outside this unit (as
are parsing, optimization, runtime layout, and register allocation).

### 2. Longest match

For input `<=`, `<` is already a valid `LT`, but consuming it immediately would
leave `=` and miss the required `LE`. In `Scanner::run` (`src/lexer.cpp`), the
non-consuming `starts_with` checks feed `scan_multi_character_token` before
`scan_single_character_token`; the former consumes both bytes as `LE`. The test
`all_punctuation_and_longest_match_operators_are_adjacent` places `<-`, `<=`,
and `=>` directly beside single-character operators and would fail if `<` or
`=` were chosen early. Maximal identifier scanning followed by keyword lookup
similarly keeps `classroom` as one object identifier in
`every_reserved_word_and_keyword_prefix_identifier`.

### 3. Main-loop invariant and termination

At the top of every `Scanner::run` iteration:

- `offset_` identifies the first unprocessed byte;
- `line_` and `column_` identify that byte's one-based position (or the EOF
  position when `offset_ == source_.size()`); and
- emitted records describe completed constructs from the consumed prefix in
  scanner order, with no EOF record yet.

Only `Scanner::advance` mutates the cursor, applying the LF rule in one place.
Each token captures a `Mark` before consuming its first byte, so the invariant
gives its correct starting position. Every normal-loop branch consumes at least
one byte; delegated comment/string loops either consume a byte/pair or return;
and one-byte invalid-character recovery also advances. Thus `offset_` strictly
increases while input remains, even for malformed input. The loop terminates
after at most a constant number of checks per consumed byte, and `run` appends
exactly one EOF afterward. Tests
`invalid_character_recovers_to_following_valid_token`,
`unterminated_string_at_lf_recovers_on_next_line`, and
`empty_input_and_final_eof_position` exercise those claims.

### 4. Nested block comments

`Scanner::scan_block_comment` stores the outer opening `Mark` and a depth
counter initialized to one. Each nested `(*` increments it, each `*)`
decrements it, and every other byte advances once; quote bytes receive no
special treatment. Depth zero returns to normal scanning. EOF at positive
depth uses the saved outer mark for one `ERROR_UNTERMINATED_COMMENT`.

For a comment/input span of length `n`, time is tightly `Theta(n)`: every byte
is advanced exactly once and each position gets only constant two-byte
lookahead. Auxiliary comment-state space is `Theta(1)` machine words, or
`Theta(log d)` bits to represent maximum nesting depth `d`; no `Theta(d)` stack
is needed because inner positions are never reported. Returned error lexeme
storage can be `Theta(n)`. Tests `nested_block_comments_are_ignored` (including
delimiters around quote bytes) and
`unterminated_block_comment_reports_outer_span` cover both exits.

### 5. Invalid-escape recovery

In `Scanner::scan_string`, an invalid escape has the two-byte boundary required
by the contract. The scanner records the backslash position, consumes exactly
the backslash and following byte, buffers an `ERROR_INVALID_ESCAPE`, marks the
string tainted, and remains in string state. It consumes a later closing quote
but emits no `STRING` for the surrounding valid fragments. Normal scanning then
begins at the first byte after that quote.

This cannot duplicate the bad pair because the cursor has advanced twice; it
cannot skip the unrelated following token because the closing quote, rather
than an arbitrary later token, is the recovery boundary.
`invalid_escape_recovers_at_closing_quote` proves that `after` remains a token
while `a`/`z` do not leak out.
`multiple_invalid_escapes_do_not_expose_string_fragments` proves two focused
errors are kept and an intervening `+` stays inside the malformed string; it
also verifies that the later `if` keyword is not skipped.

### 6. Parser-facing interface

No CLI parsing is needed now: a parser can call `Lexer::scan(std::string_view)`
from `include/minicool/lexer.hpp` and consume `std::vector<Token>`, whose records
already contain a typed kind, exact raw lexeme, and numeric position. Lexical
diagnostics are structured error token kinds, not stderr strings. The CLI in
`src/main.cpp` is only an adapter over that API.

If the parser later requires decoded string/integer values or diagnostics
separate from the token stream, the smallest extension would add an optional
typed value to `Token` and/or return a `ScanResult {tokens, diagnostics}` while
retaining the current raw fields. API tests such as
`valid_strings_include_every_supported_escape` and
`invalid_character_recovers_to_following_valid_token` test records directly,
whereas `serialization_escapes_bytes_in_the_required_form` and
`cli_process_serialization_and_lexical_error_status` isolate formatting. That
boundary limits the change and provides regression evidence on both sides.

### 7. Reproduction and remaining uncertainty

Exact clean-build and test commands:

```sh
make clean
make all
make test
```

The final clean run is recorded in `debugging-log.md`. It compiled under G++
8.5.0 with C++17 warnings treated as errors, then reported 18 API tests and
three CLI process tests passing. This is local evidence for this bounded unit,
not an independent validation or wider-course completion claim.

One uncertain design choice remains: the contract separately requires focused
invalid-escape errors and an outer unterminated-string error but gives no
combined example. When both occur in one string, this implementation orders the
outer span before buffered inner errors by source position. `notes.md` and
`DESIGN.md` state that choice explicitly rather than asserting an unspecified
full-COOL behavior.
