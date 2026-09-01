# Build environment

The repository has no third-party dependencies. It needs a C11 compiler, `make`, and Python 3 for the
black-box test drivers. The observed host used the commands recorded in `VALIDATION.md`; compiler
versions are host facts, not pinned dependencies.

For an optional diagnostic build, override flags without editing the Makefile:

```sh
make -C starter clean all \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined'
```

Sanitizer availability varies by compiler and runtime. Restore the ordinary build with `make clean
all` afterward. No network access, package installation, environment file, or secret material is
needed.

The repository structure and metadata can be checked without third-party packages:

```sh
python3 environment/audit_repository.py
```
