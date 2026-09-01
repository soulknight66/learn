# Starter implementation

The scaffold separates shared types, lexing, compilation, and VM execution. It
should compile before the algorithms are complete, but its deliberate `TODO`
errors mean the public behavior does not yet pass.

## Build

Free Pascal 3.2.x is the target:

```bash
make
./bin/mica examples/countdown.mica
```

Equivalent direct command:

```bash
mkdir -p bin units
fpc -Mobjfpc -Sh -O1 -g -gl -Fusrc -FUunits -FEbin src/mica.pas
```

## Implementation milestones

1. `lexer.pas`: cursor tracking, comments, identifiers/keywords, checked decimal
   literals, one- and two-byte operators, and EOF.
2. `compiler.pas`: token cursor helpers, recursive-descent expression parsing,
   flat variable-slot resolution, statement compilation, and jump backpatching.
3. `vm.pas`: operand stack, slots, instruction dispatch, checked arithmetic,
   jump validation, output, and the exact step budget.
4. `mica.pas`: retain the CLI and diagnostic boundary while completing the three
   units above.

Do not use unchecked Pascal `Integer`; language values are `Int64`. Do not rely
only on compiler overflow switches, since acceptance may use different build
profiles.

## Debug listings

Token mode prints one line per token, including EOF:

```text
1:1 LET let
1:5 IDENTIFIER x
1:7 EQUAL =
1:9 INTEGER 2
1:10 SEMICOLON ;
2:1 EOF <eof>
```

Bytecode mode uses a four-digit instruction index, mnemonic, optional decimal
operand, and the source location associated with the instruction:

```text
0000 CONST 2 @1:9
0001 STORE 0 @1:5
0002 HALT @2:1
```

Instruction mnemonics are returned by `OpName` in `mica_types.pas`. Constants,
slots, and jump targets have operands; other instructions do not.
