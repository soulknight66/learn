# Reproducible build environment

`build.py` invokes binaries directly with argv arrays, captures diagnostics, applies a 20-second
timeout to each tool, and never uses a shell. Each child starts an isolated process group, which is
killed as a unit on timeout. Its verified defaults are `/usr/bin/as` and `/usr/bin/ld.bfd`; override
them only with regular, non-symlink files using `--assembler` and `--linker`.

The helper rejects source, assembler, and linker symlinks before resolving the supplied paths. It
assembles in a private temporary directory but gives the linker the stable input name `cinder.o`,
so a random scratch path is not retained in the ELF string table.

The job's pinned Python entry point is:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
```

The generated executable is a freestanding ELF and has no libc dependency. The configured JDK is
not used because this project and its validators contain no Java component. Exact observed tool
versions are retained in `VALIDATION.md`.

`audit.py` checks every checked-in pack file as required, the authoritative forbidden path list,
regular-file/directory types, the exact manifest object, the complete canonical provenance object,
and narrowly defined credential patterns. Its full-object provenance digest is distinct from the
source-snapshot identifier stored in the manifest. Run it after creating `VALIDATION.md`; it
intentionally does not treat ordinary educational uses of words such as “token” or “secret” as a
credential.

Run the helper regressions from the pack root with:

```text
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s environment -p 'test_*.py' -v
```
