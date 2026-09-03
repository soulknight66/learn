# Environment

The project uses JavaScript ES modules and only Node built-ins. No dependency download or package
installation is required.

The generation host supplied this exact runtime outside `PATH`:

```text
/arm/tools/nodejs/node/22.21.0/linux64/bin/node
```

Run learner-visible tests from the repository root:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.mjs
```

The complete production pack is not a learner workspace. Its deterministic projection policy is
`learner-view-policy.json`. Before publishing, the controlling harness can obtain a path-and-content
inventory without copying any files:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-learner-view.mjs
```

The verifier's optional `--projected-root PATH` mode compares a separately materialized learner
view byte-for-byte with that inventory. It never creates or modifies the target. Pack-builder and
instructor-only checks are intentionally omitted from this learner-facing guide. Fresh builder
evidence is recorded outside the learner projection in `VALIDATION.md`; a validator must rerun
checks rather than relying on prose.
