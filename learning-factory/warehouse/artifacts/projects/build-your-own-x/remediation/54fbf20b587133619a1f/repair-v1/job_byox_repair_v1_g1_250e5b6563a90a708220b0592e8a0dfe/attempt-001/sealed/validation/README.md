# Validation utilities

`check_artifact.py` audits the complete administrator pack. It does not imply that the complete tree
is safe to expose to a learner.

`view_policy.py` applies the strict policy in `environment/view-policy.json`. The policy starts from
an exact learner allowlist, denies everything else, never follows symbolic links, and reveals later
prompt directories cumulatively. `audit` constructs every projected file set in memory, checks that
sealed and unrevealed paths are absent, and binds each view to a path-and-content SHA-256 identity:

```sh
python3 sealed/validation/view_policy.py audit
python3 -m unittest discover -s sealed/validation -p 'test_*.py' -v
```

An administrator can use `list VIEW` to inspect one projection. `export VIEW OUTPUT` requires a new
output path outside the complete pack, copies only audited regular files, and verifies the resulting
identity. Never transfer the complete administrator tree as a substitute for this projection.
