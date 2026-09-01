# Java environment

This challenge is self-contained and requires no network access or third-party
dependencies.

Required tools:

- a Java Development Kit with `javac` and `java`, version 17 or newer;
- a POSIX-compatible shell to run the public test script;
- the `dirname` and `rm` POSIX utilities;
- an implementation of `mktemp` supporting `mktemp -d TEMPLATE` with six trailing `X` characters;
- an existing writable temporary parent directory.

Confirm the Java tools with:

```sh
javac -version
java -version
```

Run the contract suite from the repository root:

```sh
sh public_tests/run.sh
```

The runner passes `--release 17 -Xlint:all -Werror` to `javac`. For temporary storage it first uses a
non-empty `$TMPDIR`, then writable `/tmp`, then the writable repository root. To select explicitly:

```sh
TMPDIR=/existing/writable/directory sh public_tests/run.sh milestone-1
```

The temporary directory is removed on normal exit and handled signals. The runner does not write
compiled classes into `starter/` or `public_tests/`.

## Learner-view transfer boundary

`student-view-files.txt` is the exact regular-file allowlist for control-plane export. It excludes
provenance operations, validation records, exercises, and every `sealed/` path. The full production
pack is not a learner view. A production-only validator at
`sealed/validation/verify_student_view.py` compares an exported directory's complete file and
directory inventory plus every file hash against this allowlist. Only the delivery harness should
create that external view; this challenge pack does not create one itself.
