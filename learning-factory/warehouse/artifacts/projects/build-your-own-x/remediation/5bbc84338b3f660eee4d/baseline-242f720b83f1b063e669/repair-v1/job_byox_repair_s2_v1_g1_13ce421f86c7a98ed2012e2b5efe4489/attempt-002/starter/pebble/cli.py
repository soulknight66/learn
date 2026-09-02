"""Command-line boundary scaffold for ``python -m pebble.cli``."""

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Implement expression, UTF-8 file, and interactive modes."""

    raise NotImplementedError("TODO: implement the command-line contract")


if __name__ == "__main__":
    raise SystemExit(main())
