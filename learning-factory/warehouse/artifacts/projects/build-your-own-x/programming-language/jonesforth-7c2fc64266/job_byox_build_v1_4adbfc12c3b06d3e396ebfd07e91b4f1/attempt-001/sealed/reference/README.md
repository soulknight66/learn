# Sealed reference implementation

This directory contains an independently generated x86-64 GNU assembly implementation of the
specified language. It reads through EOF, compiles every token to bounded bytecode, then executes
the bytecode on a 256-cell stack. It uses only Linux read, write, and exit system calls.

Harness commands:

    make -C sealed/reference clean all
    STACKVM_TARGET=sealed/reference python3 -m unittest discover -s public_tests -v
    python3 -m unittest discover -s sealed/reference_tests -v

This code is evaluator-only solution material. Local results do not promote the manifest.

