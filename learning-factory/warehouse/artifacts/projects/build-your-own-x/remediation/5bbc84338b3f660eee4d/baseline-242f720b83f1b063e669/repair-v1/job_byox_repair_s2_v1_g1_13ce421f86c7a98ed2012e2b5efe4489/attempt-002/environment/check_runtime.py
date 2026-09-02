"""Fail early when the selected Python or temporary directory is unsuitable."""

import sys
import tempfile


MINIMUM = (3, 11)


def main():
    if sys.version_info < MINIMUM:
        print(
            "error: Pebble requires Python 3.11 or newer; selected "
            + sys.version.split()[0],
            file=sys.stderr,
        )
        return 2
    try:
        temporary = tempfile.TemporaryFile()
    except OSError as error:
        print("error: temporary directory is not writable: " + str(error), file=sys.stderr)
        return 2
    temporary.close()
    print(
        "runtime_ok python={} tempdir={}".format(
            sys.version.split()[0], tempfile.gettempdir()
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
