# Starter implementation

This directory is the learner’s only implementation workspace. It deliberately
compiles but returns `E_NOT_IMPLEMENTED` until the pipeline is filled in.

The supplied API/data classes already enforce immutability at the boundary. The
front-end and backend files are small stage placeholders, not an architectural
requirement: you may change package-private structure while preserving the
public signatures in `REQUIREMENTS.md`.

Run from the repository root:

```bash
./environment/run-public-tests.sh
```

The script needs a Java 17+ JDK (`java` and `javac` on `PATH`) and creates only a
temporary build directory, which it removes on exit.

