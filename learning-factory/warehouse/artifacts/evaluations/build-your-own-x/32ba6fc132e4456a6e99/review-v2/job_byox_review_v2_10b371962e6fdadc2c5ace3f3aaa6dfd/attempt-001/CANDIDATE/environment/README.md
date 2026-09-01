# Java environment

This challenge is self-contained and requires no network access or third-party
dependencies.

Required tools:

- a Java Development Kit with `javac` and `java`, version 17 or newer;
- a POSIX-compatible shell to run the public test script.

Confirm the Java tools with:

```sh
javac -version
java -version
```

Run the contract suite from the repository root:

```sh
sh public_tests/run.sh
```

The runner passes `--release 17` to `javac` and builds in a newly created
temporary directory. It does not write compiled classes into `starter/` or
`public_tests/`.
