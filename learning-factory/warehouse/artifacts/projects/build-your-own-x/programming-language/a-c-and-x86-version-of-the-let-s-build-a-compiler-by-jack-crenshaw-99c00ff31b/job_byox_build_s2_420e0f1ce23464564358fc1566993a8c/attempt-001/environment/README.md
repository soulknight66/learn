# Supported environment

The artifact uses only a C11-capable GCC-compatible compiler, GNU-compatible
x86-64 assembler/linker behavior exposed through `cc`, GNU Make, and Python
3.6 or newer. The generated assembly targets Linux System V AMD64 and calls
the platform C library.

Run the non-mutating probe with:

```bash
python3 environment/check_toolchain.py
```

No package download, network access, container image, upstream checkout, or
third-party Python module is required. Other architectures can build the C
interpreter but cannot directly assemble or execute this backend's output.
