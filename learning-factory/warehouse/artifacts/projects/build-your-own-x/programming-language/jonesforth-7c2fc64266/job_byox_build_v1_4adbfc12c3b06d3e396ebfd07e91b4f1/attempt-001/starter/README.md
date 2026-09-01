# Starter

stackvm.S is a buildable syscall-only scaffold. It deliberately implements only process startup,
bounded input collection, empty-program success, and the required compile-error response for any
non-separator token.

Replace the marked compile_stub path with your tokenizer, compiler, and VM. You may split the source
into additional assembly files if Makefile continues to produce an executable named stackvm.

Useful loops while working:

    make -C starter clean all
    printf '' | starter/stackvm
    printf '2 3 + .\n' | starter/stackvm
    python3 -m unittest discover -s public_tests -v

Build products stackvm and stackvm.o are scratch artifacts and should not be submitted as source.

