# Study Task: A Testable Compiler Vertical Slice

## Goal

Build a small command-line compiler for the unit-local language **MiniMain-0**. It reads one source file, validates the complete program, constructs a program representation, and emits canonical **MiniIR-0** text. These names and formats belong only to this exercise; do not claim SysY or Koopa IR conformance.

Use a language and build system you can support with repeatable commands. C, C++, or Rust matches the course catalog, but another suitable implementation language is acceptable if you document it.

## MiniMain-0 contract

The grammar is written in EBNF:

```text
program  = "int", ws1, "main", ws0, "(", ws0, ")", ws0,
           "{", ws0, "return", ws1, integer, ws0, ";", ws0, "}" ;
integer  = "0" | nonzero-digit, { digit } ;
digit    = "0" | nonzero-digit ;
nonzero-digit = "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
ws0      = { " " | "\t" | "\n" | "\r" } ;
ws1      = ( " " | "\t" | "\n" | "\r" ), ws0 ;
```

The integer's mathematical value must be in the inclusive range `0..2147483647`. Input is interpreted as bytes from the ASCII repertoire used by the grammar. The entire file must match `program`; a valid prefix followed by any other byte is invalid. Comments, signs, byte-order marks, alternate spellings, and extra declarations are outside this language.

## MiniIR-0 contract

For a valid program returning the value `N`, emit exactly this UTF-8/ASCII text, including the final newline:

```text
fun @main(): i32 {
%entry:
  ret N
}
```

Replace only `N` with the canonical decimal value from the input. Because MiniMain-0 forbids leading zeroes except for `0`, this preserves the accepted spelling.

Example:

```text
input:  int main() { return 42; }

output:
fun @main(): i32 {
%entry:
  ret 42
}
```

## Process interface

Provide a documented command with this logical interface:

```text
COMPILER INPUT --emit mini-ir -o OUTPUT
```

`COMPILER` may be an executable or a documented launcher plus arguments. The option spelling and order above are part of the task contract.

- On success, exit `0`, write the canonical output to `OUTPUT`, and write no diagnostic to standard error.
- On a source-language error, exit `2`, emit a one-line diagnostic to standard error, and do not leave a newly generated or partially overwritten `OUTPUT` file. The diagnostic must contain the zero-based byte offset and a short reason. Exact wording is your documented choice and must be deterministic.
- On a command-line, input/output, or other operational error, exit a nonzero value other than `2`, emit a one-line diagnostic to standard error, and do not emit partial compiler output.
- Do not write generated IR to standard output. Do not include timestamps, random values, absolute workspace paths, or stack traces in normal diagnostics.

If `OUTPUT` already exists, a failed compilation must preserve its previous bytes. A successful compilation may replace it. Design the write path accordingly.

## Required implementation properties

Your submission must:

1. Have identifiable boundaries for input/process handling, recognition or parsing, the program representation, and emission. These may be modules, types, or similarly clear units appropriate to your language.
2. Represent the accepted program before rendering it. Directly copying a digit substring into a fixed template during ad hoc scanning does not meet this goal.
3. Validate the complete input and the numeric range without crashing, hanging, or depending on host integer overflow.
4. Produce byte-for-byte deterministic output and stable exit-code classes.
5. Use bounded, repeatable automated tests. Tests must create their own temporary files and must not depend on network access, wall-clock time, or a particular absolute workspace path.

## Minimum test partitions

Include automated cases covering at least:

- compact input and varied legal whitespace;
- the values `0` and `2147483647`;
- a leading-zero integer such as `01`;
- the out-of-range integer `2147483648` and at least one much longer digit sequence;
- a missing keyword, delimiter, and semicolon in separate cases;
- a negative sign, a non-ASCII byte, an empty file, and trailing non-whitespace;
- success replacing an existing output;
- source failure preserving an existing output and leaving a nonexistent output absent;
- a missing input file and an unwritable or otherwise failing output destination;
- the same valid compilation run repeatedly with identical output bytes.

You may add unit tests below the process boundary. At least one test group must invoke the documented command as a subprocess and inspect exit status, standard error, and filesystem effects.

## Deliverables

Submit the following together:

- the compiler source and any build metadata;
- automated tests;
- `README.md` with prerequisites plus clean build, run, and test commands;
- `DECISIONS.md` describing the pipeline boundaries, core invariants, atomic-output strategy, diagnostic-offset convention, and how you would add parenthesized addition without implementing it now;
- `EVIDENCE.md` recording the environment/tool versions, exact commands run, exit outcomes, and a concise test summary. Keep evidence reproducible; do not merely write “all tests passed”;
- responses to every question in `COMPREHENSION.md`, in a clearly identified response document.

Do not vendor hidden tests, course answers, external repositories, or generated dependency caches into the submission.

## Suggested work loop

First freeze the CLI and byte-level examples as black-box tests. Then introduce the smallest representation that can carry the return value through parsing and emission. Add failure partitions, including output-preservation checks, before polishing documentation. Finish by running the clean build and full test sequence from the documented starting state and capturing the evidence.

Stop at the stated grammar. Expressions, optimizations, official IR syntax, and target assembly belong to later, separately sourced units.
