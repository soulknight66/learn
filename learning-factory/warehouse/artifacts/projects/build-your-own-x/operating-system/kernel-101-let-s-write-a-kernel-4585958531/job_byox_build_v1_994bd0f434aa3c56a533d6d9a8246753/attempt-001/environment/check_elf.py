#!/usr/bin/env python3
"""Check only the structural properties promised by this challenge."""

from __future__ import print_function

import struct
import sys


def fail(message):
    print("ELF check: FAIL: " + message)
    return 1


def main(argv):
    if len(argv) != 2:
        print("usage: check_elf.py KERNEL.ELF", file=sys.stderr)
        return 2
    try:
        with open(argv[1], "rb") as stream:
            data = stream.read()
    except OSError as error:
        return fail(str(error))

    if len(data) < 52:
        return fail("file is too short for an ELF32 header")
    if data[:4] != b"\x7fELF":
        return fail("ELF magic is absent")
    if data[4] != 1 or data[5] != 1:
        return fail("expected little-endian ELF32")
    header = struct.unpack("<16sHHIIIIIHHHHHH", data[:52])
    machine = header[2]
    entry = header[4]
    if machine != 3:
        return fail("expected EM_386, got {0}".format(machine))
    if entry == 0:
        return fail("entry point is zero")
    if b"\x02\xb0\xad\x1b" not in data[:8192]:
        return fail("Multiboot v1 magic is absent from first 8192 bytes")
    print("ELF check: PASS (ELF32, EM_386, entry=0x{0:08x}, Multiboot v1)".format(entry))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
