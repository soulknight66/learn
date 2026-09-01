---
course_id: course_186d33d93d0211917db009f374a278b6
unit_id: unit_01_minicool_lexer_engineering
audience: learner
provenance: manager-authored MiniCOOL-0 exercise; not an official Stanford CS143 assignment
validation_label: LEARNER_SAFE_PREPARED_UNVALIDATED
---

# Study task: engineer a MiniCOOL-0 lexer

Build a deterministic lexer in Java or C++ for the contract below. Treat the contract as the product boundary: do not add parser behavior or claim compatibility with the full COOL language.

## 1. Deliverables

Place these items in your submission repository:

1. Scanner source code with a library-level operation equivalent to `scan(source) -> ordered token records`.
2. A command-line entry point that accepts exactly one source-file path, emits token records to standard output, emits usage or file-I/O diagnostics to standard error, and returns a nonzero status for invocation or I/O failure.
3. Automated tests runnable without network access.
4. A README or DESIGN file that gives exact clean-build, run, and test commands; identifies the supported Java or C++ toolchain; sketches component boundaries; states the scanner complexity; and lists any known limitation.
5. Responses to every prompt in `COMPREHENSION.md`, with references to your code or tests where requested.

Use only the chosen language's standard library and a locally available build/test toolchain. Do not download dependencies during build or test.

## 2. Source and position model

MiniCOOL-0 source is ASCII text. A byte outside ASCII is an invalid character. Input may be empty.

- Lines and columns are one-based.
- LF (`\n`) advances to the next line and resets the column to 1.
- Space, horizontal tab, carriage return, form feed, and vertical tab each advance the column by one. They are otherwise ignored outside strings and comments.
- Every token position is the position of its first character.
- After the last input character, emit exactly one `EOF` token with an empty lexeme at the current position.

Each library token record contains `kind`, exact raw `lexeme`, `line`, and `column`. Raw lexemes preserve source spelling; for example, a string token includes both quote characters and keeps backslash escape characters un-decoded.

## 3. Tokens

Apply longest match. When matches have equal length, the earlier category in this list wins.

### Reserved words

The following exact lowercase spellings become the corresponding uppercase token kind:

`class else fi if in inherits isvoid let loop pool then while case esac new of not true false`

For example, the spelling `class` has kind `CLASS`. Keywords are case-sensitive in MiniCOOL-0; `Class` is therefore an identifier, not `CLASS`.

### Identifiers and integers

- `TYPE_ID`: `[A-Z][A-Za-z0-9_]*`
- `OBJECT_ID`: `[a-z][A-Za-z0-9_]*`, after reserved-word recognition
- `INT`: `[0-9]+`

An underscore cannot begin an identifier and is therefore invalid when encountered first.

### Operators and punctuation

The multi-character tokens are:

| Lexeme | Kind |
|---|---|
| `<-` | `ASSIGN` |
| `<=` | `LE` |
| `=>` | `DARROW` |

The single-character tokens are:

| Lexeme | Kind | Lexeme | Kind |
|---|---|---|---|
| `{` | `LBRACE` | `}` | `RBRACE` |
| `(` | `LPAREN` | `)` | `RPAREN` |
| `:` | `COLON` | `;` | `SEMI` |
| `,` | `COMMA` | `.` | `DOT` |
| `+` | `PLUS` | `-` | `MINUS` |
| `*` | `STAR` | `/` | `SLASH` |
| `~` | `TILDE` | `<` | `LT` |
| `=` | `EQ` | `@` | `AT` |

### Strings

A `STRING` begins and ends with `"` on the same line. Its raw lexeme includes the quotes. Inside a valid string, ordinary printable ASCII characters are allowed except unescaped `"` and `\`. The only valid escapes are `\\`, `\"`, `\n`, and `\t`; preserve both characters of an escape in the raw lexeme.

If an unescaped LF or end of file appears before the closing quote, emit one `ERROR_UNTERMINATED_STRING` covering from the opening quote up to but not including that LF or through end of file. Leave the LF for normal whitespace handling, then continue. If an invalid escape such as `\q` occurs, consume the backslash and following character, emit one `ERROR_INVALID_ESCAPE` for those two characters at the backslash position, and then resume the same string. The valid portions before and after that error do not form a `STRING` token; on a later closing quote, scanning resumes in the normal state after the quote.

## 4. Ignored text and comment errors

- Space and the other whitespace described above are ignored outside strings and comments.
- A line comment begins with `--` and ends immediately before LF or at end of file.
- A block comment begins with `(*`, ends at its matching `*)`, and may nest. Comment delimiters inside a block comment affect nesting even if quote characters appear there.
- If end of file arrives inside a block comment, emit one `ERROR_UNTERMINATED_COMMENT` whose lexeme runs from the unmatched outermost opening delimiter through end of file and whose position is that delimiter's position. Then emit `EOF`.

Comments emit no normal tokens. The sequence `*)` outside a block comment has no special meaning and is scanned as `STAR`, then `RPAREN`.

## 5. Other errors and recovery

Any character that begins none of the constructs above produces one `ERROR_INVALID_CHAR` token containing that single character. Consume it and continue. Lexical error tokens go to standard output in source order like other tokens; their presence alone does not make a correctly invoked CLI fail.

Your scanner must always make progress: for any finite input it terminates and emits exactly one final `EOF`.

## 6. Command-line serialization

Print one token per line in this exact tab-separated form:

```text
line:column<TAB>kind<TAB>escaped_lexeme
```

Serialize the raw lexeme by replacing, in this order, `\` with `\\`, tab with `\t`, carriage return with `\r`, LF with `\n`, and other non-printable or non-ASCII bytes with uppercase `\xHH`. An empty lexeme produces an empty third field. Do not print banners, summaries, or diagnostics to standard output.

## 7. Required verification

Include automated tests for at least these independently named behaviors:

- empty input and the final `EOF` position;
- every reserved word plus a keyword-prefix identifier such as `classroom`;
- distinction between type and object identifiers;
- all punctuation and longest-match operators next to one another;
- line comments, nested block comments, and an unterminated block comment;
- valid strings and every supported escape;
- invalid escape recovery and unterminated strings at LF and EOF;
- invalid-character recovery followed by a valid token;
- line and column tracking across more than one line;
- a generated long input that supports your linear-time argument without relying on a fragile wall-clock threshold.

At least one test should exercise the CLI as a process, not only the scanner API. Tests must use temporary files or repository fixtures and must not depend on network access, current time, random seeds, or mutable global machine state.

## 8. Work sequence

Before coding, sketch scanner states and the transitions that consume zero, one, or multiple characters. Then implement the smallest vertical slice (identifiers, whitespace, and EOF), add tests, and extend it category by category. Finish by running from a clean build, recording the commands in your README, and answering the comprehension prompts from the final implementation.

Do not submit generated build products unless your toolchain convention requires them. Do submit source, fixtures, build configuration, and reproducible evidence.
