# Study Task: Lexical Analysis as a Tested Software Contract

Course ID: `course_23fa038d619a5b3482e8c8eadb3e2d78`  
Unit ID: `kickoff_01_lexical_contracts`  
Validation label: `LEARNER_SAFE_TASK_SPECIFICATION_PENDING_HARNESS_VALIDATION`  
Provenance: manager-authored from the compiler-topic scope of the supplied CSDIY catalog snapshot; the task is not official USTC material and requires no fetched resource.

## Mission

Build `minilex`, a dependency-free C++17 lexer library plus a thin command-line adapter. Treat the specification below as a public API contract: behavior must be deterministic, errors must be visible, and a clean checkout must build and test without network access.

Target 8 hours. Stop at 10 hours, preserve a working bounded submission, and list unfinished or desirable extensions in `DESIGN.md`.

## MiniLex lexical contract

Input is a sequence of bytes. The language's valid tokens and layout are ASCII; a byte outside ASCII is an unexpected character. Retain the exact source spelling as each token's lexeme. Do not convert integer values.

### Tokens

Recognize these keywords, with the exact token kinds shown:

- `int` → `KW_INT`
- `return` → `KW_RETURN`
- `if` → `KW_IF`
- `else` → `KW_ELSE`
- `while` → `KW_WHILE`
- `void` → `KW_VOID`

Recognize identifiers as `[A-Za-z_][A-Za-z0-9_]*` with kind `IDENTIFIER`, and decimal integer lexemes as `[0-9]+` with kind `INTEGER`. A keyword is recognized only when the complete identifier lexeme exactly equals that keyword.

Recognize the following fixed tokens:

| Spelling | Kind | Spelling | Kind |
| --- | --- | --- | --- |
| `==` | `EQ_EQ` | `!=` | `BANG_EQ` |
| `<=` | `LESS_EQ` | `>=` | `GREATER_EQ` |
| `=` | `ASSIGN` | `<` | `LESS` |
| `>` | `GREATER` | `+` | `PLUS` |
| `-` | `MINUS` | `*` | `STAR` |
| `/` | `SLASH` | `;` | `SEMICOLON` |
| `,` | `COMMA` | `(` | `LPAREN` |
| `)` | `RPAREN` | `{` | `LBRACE` |
| `}` | `RBRACE` | end of input | `EOF` |

Use maximal munch: at a position, consume the longest valid token. Resolve identifier/keyword ties by first scanning the entire identifier and then checking for an exact keyword match.

### Layout and comments

Skip spaces, horizontal tabs, and logical newlines. `LF`, `CRLF`, and a lone `CR` each represent one logical newline; `CRLF` must count as one newline, not two. A horizontal tab counts as one input column for this deliberately byte-oriented contract.

Skip `//` comments from the two slashes through the byte immediately before a logical newline or end of input. Skip non-nesting `/* ... */` comments, including any logical newlines inside them. The first `*/` closes a block comment. Comment markers inside a comment have no separate token meaning.

Comment recognition takes precedence over the one-character `SLASH` token. A slash that is not followed by `/` or `*` is a `SLASH` token.

### Positions and errors

Every token contains its kind, lexeme, and 1-based starting line and column. The first byte is at `1:1`. Columns count input bytes within a logical line, with the newline rules above. The `EOF` position is the position where the next byte would have started after all input and skipped layout.

Stop at the first lexical error. Support these stable diagnostic codes:

- `UNEXPECTED_CHARACTER` for a byte that cannot begin a valid token, including a lone `!`;
- `UNTERMINATED_BLOCK_COMMENT` when end of input occurs before a closing `*/`.

The error position is the unexpected byte for `UNEXPECTED_CHARACTER` and the opening slash for `UNTERMINATED_BLOCK_COMMENT`. Never silently drop bad input.

### Library and CLI boundary

Expose lexer behavior through a reusable library API. The library must not read process arguments, print output, or terminate the process. Its result must distinguish a complete token sequence from a structured lexical error.

The `minilex` executable accepts either no positional argument, meaning read standard input, or one file path. More arguments are a usage error. It scans the complete input before writing token output, so lexical failure produces no partial token stream.

On success, write every token, including `EOF`, to standard output as:

```text
LINE:COLUMN<TAB>KIND<TAB>LEXEME
```

Here `<TAB>` means one literal tab byte. MiniLex token lexemes cannot contain a tab or newline, and the `EOF` lexeme is empty. Send diagnostics and usage or I/O errors to standard error. Return `0` on successful tokenization and a nonzero status on any error. A lexical diagnostic must include its `LINE:COLUMN` and stable diagnostic code; human-readable detail may follow.

## Engineering work

1. Write down the central scanner states and invariants in `DESIGN.md` before or alongside implementation. Explain how the design prevents consuming the first byte of the next token and how it updates positions across all newline forms.
2. Implement the library and CLI in C++17. Keep token data, lexical errors, scanning logic, and process I/O separable enough to test the scanner without launching a process.
3. Use CMake without network downloads. These commands must work from a clean submission:

   ```bash
   cmake -S . -B build
   cmake --build build
   ctest --test-dir build --output-on-failure
   ```

4. Add deterministic automated tests. Include at least 12 focused library cases and at least 2 CLI-level cases. Cover all of these risk classes:

   - empty input and layout-only input;
   - every keyword and punctuation/operator kind;
   - keyword-prefix and identifier-boundary cases;
   - overlaps among one- and two-character operators;
   - a slash versus both comment forms;
   - adjacent tokens without spaces;
   - position tracking across `LF`, `CRLF`, lone `CR`, a tab, and a multiline block comment;
   - an arbitrarily long integer lexeme without numeric conversion;
   - each lexical error, including its position and atomic no-token-output CLI behavior; and
   - end of input immediately after a line comment and at several block-comment boundaries.

5. Include at least one compact test whose purpose is to kill a plausible mutation—for example, shortest-operator-first scanning, prefix-based keyword recognition, or counting `CRLF` twice. Name the mutation in the test or design notes.
6. Run the required clean-build sequence and save the full command transcript in `evidence/test-output.txt`. Record compiler and CMake versions in `README.md`. Do not hand-edit a failing transcript into a passing one.
7. Answer every question in `COMPREHENSION.md` in `responses/COMPREHENSION_RESPONSES.md`. Refer to your own code or test names where requested.

## Submission shape

Keep generated build products out of the submitted source tree except for the requested plain-text evidence. Submit at least:

```text
CMakeLists.txt
README.md
DESIGN.md
src/                 # library and CLI source
tests/               # deterministic tests
evidence/test-output.txt
responses/COMPREHENSION_RESPONSES.md
```

Your `README.md` must give the clean build/test commands, CLI examples, toolchain versions used, and any known limitation. Your `DESIGN.md` must identify ownership/lifetime choices, scanner states or equivalent control structure, position invariants, error strategy, and one consciously deferred extension.

## End condition

Stop when the bounded artifacts above are present and the clean-build sequence has been captured. Do not start a parser or retrofit the work into the unavailable official framework. Submission is evidence for independent review; it is not, by itself, proof that this unit or the course is complete.
