#!/usr/bin/env python3
"""Check only deterministic ELF32/i386 and Multiboot-v1 header properties."""

import pathlib
import struct
import sys


MULTIBOOT_MAGIC = 0x1BADB002
SEARCH_LIMIT = 8192


def fail(message: str) -> "NoReturn":
    print(f"kernel verification: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} KERNEL.ELF", file=sys.stderr)
        return 2

    path = pathlib.Path(sys.argv[1])
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"\x7fELF":
        fail("not an ELF file")
    if data[4] != 1:
        fail("ELF class is not 32-bit")
    if data[5] != 1:
        fail("ELF encoding is not little-endian")
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine != 3:
        fail(f"ELF machine is {machine}, expected i386 (3)")

    found_offset = None
    upper = min(len(data), SEARCH_LIMIT)
    for offset in range(0, upper - 11, 4):
        magic, flags, checksum = struct.unpack_from("<III", data, offset)
        if magic == MULTIBOOT_MAGIC and (magic + flags + checksum) & 0xFFFFFFFF == 0:
            found_offset = offset
            break
    if found_offset is None:
        fail("no aligned valid Multiboot-v1 header in first 8192 bytes")

    print(
        "kernel verification: PASS "
        f"(ELF32 i386, valid Multiboot-v1 header at file offset {found_offset})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
