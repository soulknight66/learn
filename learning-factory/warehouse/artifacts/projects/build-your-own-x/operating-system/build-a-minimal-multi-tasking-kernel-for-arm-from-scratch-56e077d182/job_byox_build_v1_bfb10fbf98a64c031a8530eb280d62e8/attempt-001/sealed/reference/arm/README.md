# Sealed ARMv7-A cooperative demonstration

This freestanding adapter targets QEMU `virt` in AArch32 at `0x40010000`. Startup masks interrupts,
sets a stack, clears `.bss`, and enters C. Two finite tasks run on separate 1 KiB stacks. The assembly
switch preserves AAPCS callee-saved registers and `lr`; expected UART payload is an alternating
`ABABABAB` between the banner and completion line.

This demonstrates cooperative stack switching only. It does not enable the MMU, install exception
vectors, enter userspace, or provide timer preemption. The portable host implementation remains the
executable model for VM and filesystem policy.

Build with `make` only when `arm-none-eabi-gcc` and binutils are installed. Run with
`make run` only when `qemu-system-arm` is installed. Neither dependency is bundled.
