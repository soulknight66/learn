# Sealed alternatives

Several valid designs were intentionally left out of the reference path:

- Compile Sprig to Java source and invoke `javac`. This makes bytecode correct by
  delegation but adds a subprocess/toolchain trust boundary and makes diagnostics
  harder to map precisely.
- Interpret the checked AST. This is excellent for differential testing but does
  not satisfy the class-file artifact contract by itself.
- Use ASM or Byte Buddy. Either removes low-level class formatting work, but a
  dependency would obscure the learning objective and require network/cache
  provenance.
- Target a modern class version and compute `StackMapTable` frames. This is more
  representative of production bytecode generation, but substantially expands
  the verifier-specific surface.
- Lower to a small basic-block IR before emission. That improves optimization,
  dataflow, and wide-branch rewriting. The reference compiles validated ASTs
  directly because the language has one function and no optimizer.

An interpreter makes a particularly useful future sealed oracle: compare its
return/output/exception tuple with the generated class over randomly generated,
well-typed programs, while keeping the generator and oracle independent from the
compiler under test.

