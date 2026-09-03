# Reference review

The reference was reviewed against the explicit contract and strict compiler warnings. The strongest
properties are bounded memory access, no heap/libc dependency in the core, check-before-commit error
paths, and validation of both forward and reverse resource ownership.

Review findings addressed during construction:

1. An optimized freestanding build initially emitted SSE instructions in the zeroing loop. Multiboot
   entered with SSE unavailable, so QEMU raised invalid opcode and triple-faulted. The kernel build now
   targets baseline i386 and disables SSE/MMX code generation.
2. The supplied QEMU binary loaded an incompatible ambient GLib unless its configured GLib directory
   was placed first in `LD_LIBRARY_PATH`. The documented command pins that directory.
3. Sanitizer binaries need the configured GCC runtime directory. LeakSanitizer additionally needs
   process inspection denied by this sandbox, so only leak detection is disabled.

Remaining limitations include linear lookup, no concurrency, no fault containment around caller
pointers, no persistent media, no actual hardware page tables, no interrupt-driven context switches,
and no security boundary. Those are scope boundaries, not production-ready features. Independent
validation remains required, and the manifest intentionally stays `GENERATED` + `PARTIAL`.
