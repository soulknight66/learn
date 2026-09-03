# Reproducible environment

The artifact has no network or package-manager dependency. `toolchain.mk`
records the provisioned binaries by absolute path:

- host compiler: `/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc`
- host assembler: `/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/as`
- host linker: `/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld`
- AArch64 compiler: `/arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-gcc`
- emulator: `/arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64`
- emulator GLib runtime: `/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64`
- validation Python: `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`

Hosted compiler commands receive GCC's `-B` prefix for the recorded Binutils
directory. This selects those exact assembler and linker binaries instead of
searching `PATH` for host defaults.

On this host QEMU must be invoked with
`LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64`; otherwise the
system GLib is selected and the executable cannot resolve
`g_date_time_format_iso8601`. The sealed build file applies that environment
only to the emulator process.

Learner-facing tests use only the configured host GCC and Binutils. Run the
deterministic pack check with:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/validate_structure.py
```

Versions and observed exits from the actual validation run are recorded in
`VALIDATION.md`; this environment note is configuration, not evidence.
