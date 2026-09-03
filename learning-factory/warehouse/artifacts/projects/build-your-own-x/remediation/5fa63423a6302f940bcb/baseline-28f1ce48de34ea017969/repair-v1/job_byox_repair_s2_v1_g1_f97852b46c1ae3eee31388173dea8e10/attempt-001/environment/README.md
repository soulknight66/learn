# Build environment

The artifact targets a POSIX-like host with C17 compilation and the process-control interfaces named in `REQUIREMENTS.md`.

Configured read-only tools used by the generated validation are:

- `/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc` — observed `gcc (GCC) 15.2.0`
- `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3` — observed `Python 3.11.5`
- `/usr/bin/make` — observed `GNU Make 4.2.1` (host utility, not one of the configured roots)

The Makefiles honor `CC`, so validation can select the configured compiler explicitly:

```sh
make -C starter CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

No network access or third-party library is required. Interactive terminal behavior needs a controlling TTY and is therefore only partially exercised by the noninteractive tests supplied here.
