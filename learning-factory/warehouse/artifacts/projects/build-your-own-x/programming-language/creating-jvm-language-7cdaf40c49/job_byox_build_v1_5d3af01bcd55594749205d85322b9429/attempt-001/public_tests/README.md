# Public smoke tests

`PublicTestMain.java` is a dependency-free executable test harness. It checks a
small cross-section of the public contract: a loadable class, evaluation,
printing, precedence, control flow, diagnostics, determinism, and defensive
copies. It intentionally does not reveal the independent validation cases.

Run it through `./environment/run-public-tests.sh`. A nonzero exit means at
least one check failed. Passing this suite is necessary but not sufficient.

