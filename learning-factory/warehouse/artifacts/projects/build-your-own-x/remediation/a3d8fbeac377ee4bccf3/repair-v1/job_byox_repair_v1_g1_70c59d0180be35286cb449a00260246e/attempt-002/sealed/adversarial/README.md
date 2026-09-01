# Sealed adversarial corpus

`cases.json` records small deterministic seeds. A validator should materialize
each `source` into a fresh regular file, invoke the candidate using an argv array,
enforce a timeout, and compare exit code plus output constraints. Random mutation
should preserve the seed identifier and random seed in its evidence.

The corpus emphasizes phase separation and termination. It is not proof against
resource exhaustion and was not executed during generation.
