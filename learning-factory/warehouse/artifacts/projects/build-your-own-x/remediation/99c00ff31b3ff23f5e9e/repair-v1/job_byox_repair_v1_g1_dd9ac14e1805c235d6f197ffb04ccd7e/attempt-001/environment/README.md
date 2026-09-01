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
operational-file, content-inventory, special-file, and credential-pattern
checks with:

```bash
python3 environment/verify_artifact.py
```

The complete production pack contains `sealed/`; readable modes on that tree
are not a learner isolation mechanism. To exercise the actual allowlisted
projection in a disposable workspace-local directory, run:

```bash
python3 environment/materialize_student_view.py .student-view-check
python3 environment/verify_student_view.py .student-view-check
```

The projection contains exactly `README.md`, `AGENTS.md`, `MANIFEST.yaml`,
`REQUIREMENTS.md`, `CONCEPTS.md`, `DESIGN_QUESTIONS.md`, `starter/`,
`public_tests/`, and `environment/`. It excludes the entire `sealed/` tree plus
production provenance, license-boundary, and validation records. A controller
must project this allowlist before giving a workspace to a learner; the local
check demonstrates the transformation but does not claim harness-controlled
transfer validation.

`environment/STUDENT_VIEW_INVENTORY.json` binds every projected regular file
except the inventory itself. `sealed/ARTIFACT_INVENTORY.json` similarly records
the path, type, size, and SHA-256 digest of every other complete-pack file. Run
`python3 sealed/integrity/update_inventories.py` only after intentional pack
changes, then rerun both verifiers.

No network access, package installation, external repository, system temporary
directory, or environment secret is required. Test scratch files stay beneath
this directory and are removed by the harness.
