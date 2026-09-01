# Debugging exercises

These exercises focus on evidence, not guesswork. For each scenario, identify the violated invariant,
the smallest reproducible test, the correction, and a regression test. Do not edit a record by hand
and call that a fix.

## State corruption

After the controller is forcibly stopped during a lifecycle update, reading one container produces a
JSON parse error. Another run attempting the same identifier must not overwrite useful failure
evidence. Explain how to determine whether the visible record was written partially, replaced with
invalid content, or modified concurrently. Specify the ordering and failure behavior of a durable
update, including what happens to revisions and terminal states.

## Namespace order

A privileged integration run sees the host hostname unchanged, but the target's `/proc` view reports
unexpected host processes and cleanup occasionally leaves a proc mount behind. The unit test using a
fake backend still passes. Draw the launcher/`unshare`/helper/target process sequence and locate the
operations that must occur after namespace creation and before target execution. Include an
integration assertion that proves kernel state rather than merely checking a planned flag list.

Instructor analyses are stored only in `sealed/debugging/`.

