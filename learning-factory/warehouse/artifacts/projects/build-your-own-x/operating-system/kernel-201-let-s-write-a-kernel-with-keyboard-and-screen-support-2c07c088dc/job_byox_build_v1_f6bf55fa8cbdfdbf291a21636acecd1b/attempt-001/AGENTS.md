# Learner/agent contract

Work from the repository root and treat `REQUIREMENTS.md` as authoritative.

- Modify only `starter/` for the core exercise unless a task explicitly asks for documentation.
- Keep public APIs in `starter/include/` compatible with the supplied tests.
- Do not add hosted-library calls to code linked into the freestanding kernel.
- Preserve `volatile` at the hardware boundary and keep port I/O behind `io.h`.
- Use `make -C starter test` for fast feedback and `make -C starter kernel` for the freestanding
  link check.
- Do not claim that an ELF file booted merely because it linked. Emulator or hardware evidence is a
  separate result.
- Do not move or copy material out of `sealed/`; it is reveal-on-demand solution material.

Never put credentials, machine-specific secrets, or copyrighted upstream text in this project.
