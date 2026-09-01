from __future__ import annotations


class SharedPageSystem:
    PAGE_SIZE = 4096

    def __init__(self) -> None:
        # Design the frame table, process tables, name registry, and lock.
        raise NotImplementedError("student implementation required")

    def create_process(self, pid: int) -> None: raise NotImplementedError
    def alloc_private(self, pid: int, vpn: int, initial: bytes = b"") -> None: raise NotImplementedError
    def create_shared(self, name: str, initial: bytes = b"") -> None: raise NotImplementedError
    def map_shared(self, pid: int, vpn: int, name: str, *, writable: bool = True) -> None: raise NotImplementedError
    def fork(self, parent_pid: int, child_pid: int) -> None: raise NotImplementedError
    def read(self, pid: int, vpn: int, length: int, *, offset: int = 0) -> bytes: raise NotImplementedError
    def write(self, pid: int, vpn: int, data: bytes, *, offset: int = 0) -> None: raise NotImplementedError
    def unmap(self, pid: int, vpn: int) -> None: raise NotImplementedError
    def exec(self, pid: int) -> None: raise NotImplementedError
    def exit(self, pid: int) -> None: raise NotImplementedError
    def unlink_shared(self, name: str) -> None: raise NotImplementedError
    def stats(self) -> dict[str, object]: raise NotImplementedError
