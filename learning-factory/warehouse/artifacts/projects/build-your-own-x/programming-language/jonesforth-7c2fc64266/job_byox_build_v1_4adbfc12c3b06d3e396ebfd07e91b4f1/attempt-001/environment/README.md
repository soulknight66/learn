# Environment

The intended host is x86-64 Linux with GNU make, GNU assembler, GNU linker, and Python 3. No package
download, libc, emulator, or network access is required.

Expected commands:

    uname -m
    as --version
    ld --version
    make --version
    python3 --version
    sh environment/check.sh

The assembly uses GNU as Intel syntax. The Makefiles invoke tools through argv supplied by make and
link directly with ld, so the resulting program has no dynamic runtime dependency.

