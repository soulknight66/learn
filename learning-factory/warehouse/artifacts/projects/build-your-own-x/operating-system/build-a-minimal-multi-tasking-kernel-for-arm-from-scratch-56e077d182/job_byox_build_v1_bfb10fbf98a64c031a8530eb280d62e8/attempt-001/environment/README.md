# Build environment

The portable model needs a C11 compiler, POSIX `make`, and a shell. The Makefiles use no downloaded
packages. The checked baseline is GCC with strict warnings; sanitizer support is optional.

The optional ARMv7 target expects `arm-none-eabi-gcc`, companion binutils, and
`qemu-system-arm`. Those tools are intentionally not vendored. Run `sh environment/check.sh` to
print availability without changing the machine.
