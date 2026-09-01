# Starter

`include/tinyarm.h` is the fixed public ABI. `src/kernel.c` contains compiling placeholders; replace
them with your implementation while preserving the declarations and enum/layout order.

The portable core is the required milestone. `arm/` is an optional ARMv7-A bring-up scaffold whose
build needs tools not supplied by this repository. It is not exercised by the host public tests.

```sh
make -C starter clean all
```

No solution or design answer is present in this directory.
