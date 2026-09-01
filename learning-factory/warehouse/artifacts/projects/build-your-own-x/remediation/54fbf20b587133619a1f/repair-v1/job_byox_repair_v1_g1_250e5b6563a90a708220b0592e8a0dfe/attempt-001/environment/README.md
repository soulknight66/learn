# Environment

The challenge is dependency-free JavaScript using ECMAScript modules and the built-in `node:test`
runner.

Recommended environment:

- Node.js 20 or newer
- a POSIX-like shell for the documented command examples
- no network access and no package installation

From the repository root, run:

```bash
node --test public_tests/*.test.mjs
```

No environment variables, credentials, services, files outside this repository, or upstream
checkout are required. The generation host had Python 3.11.5 but no JavaScript runtime, so it could
only perform structural and static validation; the administrator validation record preserves that
limitation.

## Learner-view policy

`view-policy.json` is the machine-readable, default-deny reveal policy. The initial `core` view
contains only the documented learner base. Later views cumulatively add the debugging, review,
adversarial-protocol, and benchmark-protocol prompt directories; `sealed/` is denied in every view.
The administrator-side projector and transfer audit are intentionally not learner-visible.
