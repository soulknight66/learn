# Sprig grammar and precedence

```text
program     := statement* EOF
statement   := "let" IDENT "=" expression ";"
             | IDENT "=" expression ";"
             | "print" expression ";"
             | "if" "(" expression ")" block ("else" block)?
             | "while" "(" expression ")" block
             | block
block       := "{" statement* "}"
expression  := or
or          := and ("||" and)*
and         := equality ("&&" equality)*
equality    := comparison (("==" | "!=") comparison)*
comparison  := term (("<" | "<=" | ">" | ">=") term)*
term        := factor (("+" | "-") factor)*
factor      := unary (("*" | "/" | "%") unary)*
unary       := ("!" | "-") unary | primary
primary     := NUMBER | "true" | "false" | IDENT | "(" expression ")"
```

Binary precedence rows are left-associative. Identifiers match `[A-Za-z_][A-Za-z0-9_]*`.
Decimal integers use ASCII digits and have no sign token; unary minus supplies it. The parser
admits magnitudes through 2^63 so `-9223372036854775808` is representable, while other uses of
2^63 overflow during evaluation. `//` comments end at newline.
Diagnostics report one-based line and column at the unexpected token or character.
