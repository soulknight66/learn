# Environment

The project uses JavaScript ES modules and only Node built-ins. No dependency download or package
installation is required.

The generation host supplied this exact runtime outside `PATH`:

```text
/arm/tools/nodejs/node/22.21.0/linux64/bin/node
```

Run public tests, sealed instructor tests, and the pack audit from the repository root:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.mjs
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/*.test.mjs
/arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-pack.mjs
```

The observed version and results from the generation run are recorded in `VALIDATION.md`. A future
validator must run commands independently rather than relying on that prose.
