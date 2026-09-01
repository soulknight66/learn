# Working agreement

Implement only the contracts in `REQUIREMENTS.md`, preserving the public API in
`starter/include/tinykernel.h`.

- Keep subsystem behavior deterministic and allocation-free on the host.
- Do not add libc calls to `starter/src/`; those files must remain freestanding-compatible.
- Treat public tests as examples, not a complete specification.
- Keep generated objects inside a directory named `build/`.
- Do not inspect or copy material under `sealed/`; it is validator-owned solution evidence.
- Do not weaken tests, change fixed limits, or special-case known test inputs.
- Run each stage test and the ELF structural checker before declaring your work complete.

The artifact is intentionally partial as a production operating system. A passing exercise does
not imply production readiness.
