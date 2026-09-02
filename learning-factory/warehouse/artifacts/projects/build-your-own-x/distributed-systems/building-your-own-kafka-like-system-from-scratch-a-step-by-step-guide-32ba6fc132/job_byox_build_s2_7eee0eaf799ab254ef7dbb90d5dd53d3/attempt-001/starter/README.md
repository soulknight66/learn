# Starter workspace

Implement the Java files under `src/main/java`. Keep package names and public
method signatures stable because evaluator tests compile directly against
them. The starter has no external dependencies and targets Java 21.

Recommended order:

1. `LogRecord` and `RecordCodec`
2. `SegmentedLog`
3. `ElectionState`
4. `ReplicationTracker`
5. `PartitionLeader`

Run the public suite from the repository root:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

The runner compiles into a temporary directory and leaves this tree clean.
Initial failures marked `TODO` are expected. Do not read or depend on `sealed/`;
independent evaluation uses it only as an artifact reference.
