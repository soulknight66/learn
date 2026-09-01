# Environment

The implementation uses only C11 and the C standard library. Building the tool
requires `cc` and `make`; running the test harness requires Python 3.6 or newer.
Native-output tests additionally require an x86-64 System V environment, GNU
assembler syntax accepted by `cc`, and support for `cc -no-pie`.

Check command availability with:

```bash
python3 environment/check_environment.py
```

After creating or changing artifact files, reproduce the structural, metadata,
special-file, isolation, and credential-pattern checks with:

```bash
python3 environment/verify_artifact.py
```

No network access, package installation, external repository, system temporary
directory, or environment secret is required. Test scratch files stay beneath
this directory and are removed by the harness.
