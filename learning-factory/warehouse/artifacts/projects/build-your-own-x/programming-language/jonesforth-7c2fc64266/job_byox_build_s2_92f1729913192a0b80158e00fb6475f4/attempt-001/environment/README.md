# Reproducible build environment

`build.py` invokes binaries directly with argv arrays, captures diagnostics, applies a 20-second
timeout to each tool, and never uses a shell. Each child starts an isolated process group, which is
killed as a unit on timeout. Its verified defaults are `/usr/bin/as` and `/usr/bin/ld`; override them
only with regular, non-symlink files using `--assembler` and `--linker`.

The job's pinned Python entry point is:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
```

The generated executable is a freestanding ELF and has no libc dependency. The configured JDK is
not used because this project and its validators contain no Java component. Exact observed tool
versions are retained in `VALIDATION.md`.

`audit.py` checks the authoritative required and forbidden path lists, regular-file/directory types,
the exact manifest object, the provenance binding, and narrowly defined credential patterns. Run it
after creating `VALIDATION.md`; it intentionally does not treat ordinary educational uses of words
such as “token” or “secret” as a credential.
