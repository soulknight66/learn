# Reproducible environment

The artifact has no downloaded dependencies. It uses Java language features available in Java 21.
The factory-provided read-only JDK is:

```text
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Inspect and test it with:

```bash
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 public_tests/run.sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
```

`public_tests/run.sh` honors `JDK_ROOT` and otherwise uses that exact factory path. It never accesses
the network and builds in a newly created temporary directory.
`audit.py` checks packaging paths, regular-file types, manifest identity, provenance linkage, and a
small set of high-confidence credential signatures without traversing factory-owned hidden metadata.
