# Callable contract

`PAGE_SIZE` is 4096. All methods are thread-safe.

- `create_process(pid: int) -> None`
- `alloc_private(pid: int, vpn: int, initial: bytes = b"") -> None`
- `create_shared(name: str, initial: bytes = b"") -> None`
- `map_shared(pid: int, vpn: int, name: str, *, writable: bool = True) -> None`
- `fork(parent_pid: int, child_pid: int) -> None`
- `read(pid: int, vpn: int, length: int, *, offset: int = 0) -> bytes`
- `write(pid: int, vpn: int, data: bytes, *, offset: int = 0) -> None`
- `unmap(pid: int, vpn: int) -> None`
- `exec(pid: int) -> None`
- `exit(pid: int) -> None`
- `unlink_shared(name: str) -> None`
- `stats() -> dict[str, object]`

`stats()` returns integer keys `process_count`, `frame_count`, and `segment_count`, plus `frames`.
`frames` maps stable integer frame IDs to dictionaries containing integer `mapping_refs` and
`name_refs`.

Raise `ValueError` for a duplicate process, duplicate name, duplicate `(pid, vpn)` mapping,
oversized initial content, invalid length/offset, or a write through a read-only mapping. Raise
`KeyError` for an unknown process, name, or virtual page. Reads beyond the page and writes whose
`offset + len(data)` exceeds `PAGE_SIZE` raise `ValueError`.
