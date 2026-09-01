# Alternative designs

These alternatives were considered but are not implemented in the reference.

1. **Pratt parser.** A binding-power table compresses expression parsing and is
   easier to extend with new operators. Recursive-descent levels were chosen
   because their functions visibly correspond to the published grammar.
2. **Bytecode virtual machine.** Lowering the AST to stack bytecode would give
   the interpreter and x86 backend a smaller shared semantic core. It adds an IR
   format, validation rules, and another resource budget.
3. **Direct assembly during parsing.** This reduces retained memory for simple
   expressions. It makes semantic rejection after emission, branch declarations,
   and clean failure output substantially harder.
4. **Register-based IR.** Three-address instructions followed by liveness and
   register allocation would produce better native code. That is a natural
   follow-on challenge rather than a necessary part of Mica's language-design
   objective.
5. **Lexical block scopes.** Scope stacks are more familiar and prevent skipped
   declarations from being visible later. Mica deliberately uses one source
   namespace so the first symbol pass stays inspectable; adding scopes should be
   specified as a language revision, not a silent implementation choice.
