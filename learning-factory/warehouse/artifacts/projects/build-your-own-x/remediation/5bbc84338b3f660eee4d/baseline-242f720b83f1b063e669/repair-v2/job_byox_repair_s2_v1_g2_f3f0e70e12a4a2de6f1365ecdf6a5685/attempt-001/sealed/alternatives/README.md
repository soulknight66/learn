# Sealed alternatives

The reference tree contains two execution designs over one value model:

1. `pebble.interpreter.Interpreter` directly walks syntax and supports the entire required language.
2. `pebble.compiler.Compiler` plus `pebble.vm.VirtualMachine` lowers a pure subset to stack bytecode and
   rejects state/closure forms.

Other viable independent designs include immutable located AST nodes, an explicit continuation machine,
or lexical-address compilation with captured cells. They were not implemented here because each would
either duplicate the teaching implementation or substantially widen the validation surface. The bytecode
path is deliberately small enough for instruction stack effects to be audited in one file.
