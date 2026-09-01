# Environment

Requires Python 3.11 with SQLite enabled. No network or third-party package is used. All test,
fuzz, stress, and benchmark databases live in temporary directories. The materializer copies
an explicit allowlist to a destination outside this pack, creating a structural learner view.
