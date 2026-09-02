# Public tests

`PublicTestMain` is a dependency-free Java program with six small contract
tests. It checks record ownership, a direct codec round trip and boundary,
durable log round trips, election voting, majority commitment, and committed
read isolation. The codec case gives milestone-2 feedback before segmented-log
work is complete. The suite is deliberately not an exhaustive specification;
read `REQUIREMENTS.md` for edge cases.

From the repository root run:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

The initial starter should compile and report incomplete milestones. A passing
public suite is useful feedback but is not proof of full correctness. The
runner accepts `--temp-root <writable-directory>` when its deterministic
repository-local and attempt-local scratch locations are unavailable.
