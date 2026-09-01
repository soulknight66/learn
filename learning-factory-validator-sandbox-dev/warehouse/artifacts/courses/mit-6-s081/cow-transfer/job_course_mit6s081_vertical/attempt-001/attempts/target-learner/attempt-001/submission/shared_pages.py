from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class _Frame:
    data: bytearray
    mappings: set[tuple[int, int]] = field(default_factory=set)
    names: set[str] = field(default_factory=set)


@dataclass
class _Mapping:
    frame_id: int
    writable: bool
    cow: bool = False
    shared: bool = False


class SharedPageSystem:
    PAGE_SIZE = 4096

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._next_frame = 1
        self._frames: dict[int, _Frame] = {}
        self._processes: dict[int, dict[int, _Mapping]] = {}
        self._segments: dict[str, int] = {}

    def _new_frame(self, initial: bytes = b"") -> int:
        if not isinstance(initial, bytes) or len(initial) > self.PAGE_SIZE:
            raise ValueError("page contents must be bytes no larger than PAGE_SIZE")
        frame_id = self._next_frame
        self._next_frame += 1
        data = bytearray(self.PAGE_SIZE)
        data[: len(initial)] = initial
        self._frames[frame_id] = _Frame(data)
        return frame_id

    def _table(self, pid: int) -> dict[int, _Mapping]:
        try:
            return self._processes[pid]
        except KeyError as error:
            raise KeyError(f"unknown process: {pid}") from error

    def _mapping(self, pid: int, vpn: int) -> _Mapping:
        try:
            return self._table(pid)[vpn]
        except KeyError as error:
            raise KeyError(f"unmapped page: pid={pid} vpn={vpn}") from error

    def _validate_location(self, vpn: int, offset: int, length: int) -> None:
        if vpn < 0 or offset < 0 or length < 0 or offset + length > self.PAGE_SIZE:
            raise ValueError("page address is out of range")

    def create_process(self, pid: int) -> None:
        with self._lock:
            if pid in self._processes:
                raise ValueError(f"process already exists: {pid}")
            self._processes[pid] = {}

    def alloc_private(self, pid: int, vpn: int, initial: bytes = b"") -> None:
        with self._lock:
            self._validate_location(vpn, 0, len(initial))
            table = self._table(pid)
            if vpn in table:
                raise ValueError("virtual page is already mapped")
            frame_id = self._new_frame(initial)
            table[vpn] = _Mapping(frame_id, writable=True)
            self._frames[frame_id].mappings.add((pid, vpn))

    def create_shared(self, name: str, initial: bytes = b"") -> None:
        with self._lock:
            if not name or name in self._segments:
                raise ValueError("shared name must be nonempty and unique")
            frame_id = self._new_frame(initial)
            self._segments[name] = frame_id
            self._frames[frame_id].names.add(name)

    def map_shared(self, pid: int, vpn: int, name: str, *, writable: bool = True) -> None:
        with self._lock:
            self._validate_location(vpn, 0, 0)
            table = self._table(pid)
            if vpn in table:
                raise ValueError("virtual page is already mapped")
            try:
                frame_id = self._segments[name]
            except KeyError as error:
                raise KeyError(f"unknown shared page: {name}") from error
            table[vpn] = _Mapping(frame_id, writable=writable, shared=True)
            self._frames[frame_id].mappings.add((pid, vpn))

    def fork(self, parent_pid: int, child_pid: int) -> None:
        with self._lock:
            if child_pid in self._processes:
                raise ValueError("child process already exists")
            parent = self._table(parent_pid)
            child: dict[int, _Mapping] = {}
            for vpn, mapping in parent.items():
                if mapping.shared or not mapping.writable and not mapping.cow:
                    copy = _Mapping(mapping.frame_id, mapping.writable, mapping.cow, mapping.shared)
                else:
                    mapping.writable = False
                    mapping.cow = True
                    copy = _Mapping(mapping.frame_id, writable=False, cow=True)
                child[vpn] = copy
                self._frames[mapping.frame_id].mappings.add((child_pid, vpn))
            self._processes[child_pid] = child

    def read(self, pid: int, vpn: int, length: int, *, offset: int = 0) -> bytes:
        with self._lock:
            self._validate_location(vpn, offset, length)
            mapping = self._mapping(pid, vpn)
            return bytes(self._frames[mapping.frame_id].data[offset : offset + length])

    def write(self, pid: int, vpn: int, data: bytes, *, offset: int = 0) -> None:
        if not isinstance(data, bytes):
            raise TypeError("writes require bytes")
        with self._lock:
            self._validate_location(vpn, offset, len(data))
            mapping = self._mapping(pid, vpn)
            if mapping.cow:
                old = self._frames[mapping.frame_id]
                if len(old.mappings) > 1:
                    old.mappings.remove((pid, vpn))
                    frame_id = self._new_frame(bytes(old.data))
                    self._frames[frame_id].mappings.add((pid, vpn))
                    mapping.frame_id = frame_id
                mapping.cow = False
                mapping.writable = True
            if not mapping.writable:
                raise PermissionError("mapping is read-only")
            self._frames[mapping.frame_id].data[offset : offset + len(data)] = data

    def _release(self, pid: int, vpn: int) -> None:
        table = self._table(pid)
        mapping = table.pop(vpn)
        frame = self._frames[mapping.frame_id]
        frame.mappings.remove((pid, vpn))
        if not frame.mappings and not frame.names:
            del self._frames[mapping.frame_id]

    def unmap(self, pid: int, vpn: int) -> None:
        with self._lock:
            if vpn not in self._table(pid):
                raise KeyError(f"unmapped page: pid={pid} vpn={vpn}")
            self._release(pid, vpn)

    def exec(self, pid: int) -> None:
        with self._lock:
            for vpn in list(self._table(pid)):
                self._release(pid, vpn)

    def exit(self, pid: int) -> None:
        with self._lock:
            self.exec(pid)
            del self._processes[pid]

    def unlink_shared(self, name: str) -> None:
        with self._lock:
            try:
                frame_id = self._segments.pop(name)
            except KeyError as error:
                raise KeyError(f"unknown shared page: {name}") from error
            frame = self._frames[frame_id]
            frame.names.remove(name)
            if not frame.names and not frame.mappings:
                del self._frames[frame_id]

    def stats(self) -> dict[str, object]:
        with self._lock:
            return {
                "process_count": len(self._processes),
                "frame_count": len(self._frames),
                "segment_count": len(self._segments),
                "frames": {
                    frame_id: {
                        "mapping_refs": len(frame.mappings),
                        "name_refs": len(frame.names),
                    }
                    for frame_id, frame in sorted(self._frames.items())
                },
            }
