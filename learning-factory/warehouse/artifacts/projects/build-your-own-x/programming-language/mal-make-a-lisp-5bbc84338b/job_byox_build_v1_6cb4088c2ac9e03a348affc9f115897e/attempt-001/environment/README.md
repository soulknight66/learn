# Environment

Sprig is intentionally dependency-free. It requires:

- Python 3.6 or newer
- the Python standard library, including `unittest`
- a POSIX-like shell only for the command examples (the package itself is portable Python)

No package installation, network access, build step, environment variable, locale setting, database,
or service is required. Run commands from the repository root and select the package under test with
`PYTHONPATH=starter`.

The generation host reported `Python 3.6.8`. See `VALIDATION.md` for commands that were actually run;
that record is not a substitute for independent validation.
