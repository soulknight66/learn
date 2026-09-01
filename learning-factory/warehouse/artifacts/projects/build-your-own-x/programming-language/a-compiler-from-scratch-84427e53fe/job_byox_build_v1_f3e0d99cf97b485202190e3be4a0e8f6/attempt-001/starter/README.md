# Starter layout

`lib/pebble/` contains one file per compiler stage. Public method signatures and data containers are provided, while core methods intentionally raise `NotImplementedError`. Implement them in this suggested order:

1. `lexer.rb`
2. `parser.rb`
3. `compiler.rb`
4. `vm.rb`
5. `lib/pebble.rb` convenience methods and `bin/pebble`

Do not change the required AST or instruction interface. Small private helpers and additional tests are encouraged. No gems are needed.
