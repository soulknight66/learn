"""Stage 6 helper entry point executed after ``unshare``.

This module deliberately contains no partial isolation setup.  Implement it
only after the validation, planning, state, and fake-backend stages pass.
"""


def main() -> int:
    raise NotImplementedError("stage 6: implement the isolated child helper")


if __name__ == "__main__":
    raise SystemExit(main())
