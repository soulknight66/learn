# Environment

The project uses only a Java 17+ JDK and POSIX shell. No network, Maven, Gradle,
parser generator, or bytecode library is required. This keeps validation
reproducible and makes every class-file byte attributable to learner code.

From the repository root, run:

```bash
./environment/run-public-tests.sh
```

The script checks tool availability, compiles starter sources and public tests
with `javac --release 17 -Xlint:all -Werror`, runs assertions with `java -ea`,
uses a temporary directory, and cleans it on exit.

The current generation host lacks both `java` and `javac`; this is recorded in
`VALIDATION.md`. Run the command unchanged on a JDK-equipped validator.

