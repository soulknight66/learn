from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
from textwrap import dedent
from typing import Any

from .db import Database
from .util import redact, tree_sha256


@dataclass(frozen=True)
class SliceResult:
    """Candidate artifact plus the independent checks required before promotion."""

    evidence: dict[str, Any]
    validators: list[dict[str, Any]]
    artifact_type: str
    semantic_path: str
    metadata: dict[str, Any]


_CSDIY_DEFAULTS: dict[str, str] = {
    "source_name": "CSDIY / CS Self-Learning",
    "source_path": "../cs-self-learning",
    "upstream_url": "https://github.com/PKUFlyingPig/cs-self-learning",
    "commit_hash": "adce8e13789dc16aa6d1fbe163e9541736defae4",
    "license": "MIT for repository-authored material; linked resources retain their licenses",
    "source_reference": "docs/操作系统/MIT6.S081.en.md",
    "external_reference": "https://pdos.csail.mit.edu/6.828/2021/schedule.html",
}

_BYOX_DEFAULTS: dict[str, str] = {
    "source_name": "Build Your Own X",
    "source_path": "../build-your-own-x",
    "upstream_url": "https://github.com/codecrafters-io/build-your-own-x",
    "commit_hash": "aa17439b62f384511a5561ce308e9598b94d8989",
    "license": "CC0-1.0 catalog waiver; linked tutorials retain their licenses",
    "source_reference": "README.md#build-your-own-database",
    "external_reference": "http://aosabook.org/en/500L/dbdb-dog-bed-database.html",
}


def _clean(value: object, *, limit: int = 2_000) -> str:
    return redact(str(value), limit=limit).strip()


def _safe_target(workspace: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise ValueError(f"unsafe generated path: {relative!r}")
    workspace_resolved = workspace.resolve()
    target = workspace / candidate
    try:
        target.resolve().relative_to(workspace_resolved)
    except ValueError as error:
        raise ValueError(f"generated path escapes workspace: {relative!r}") from error
    current = workspace
    for part in candidate.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"generated path traverses symlink: {relative!r}")
        current.mkdir(exist_ok=True)
    if target.is_symlink():
        raise ValueError(f"refusing to overwrite symlink: {relative!r}")
    return target


def _write(workspace: Path, relative: str, content: str) -> None:
    target = _safe_target(workspace, relative)
    rendered = dedent(content).lstrip("\n")
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    target.write_text(rendered, encoding="utf-8", newline="\n")


def _write_json(workspace: Path, relative: str, value: object) -> None:
    _write(workspace, relative, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _yaml(value: object) -> str:
    """JSON strings/scalars are valid YAML and avoid an optional YAML dependency."""

    return json.dumps(value, ensure_ascii=False)


def _workspace_summary(workspace: Path) -> dict[str, Any]:
    files = sorted(path for path in workspace.rglob("*") if path.is_file())
    generated = [path for path in files if path.name != ".factory-workspace"]
    return {
        "generated_file_count": len(generated),
        "generated_bytes": sum(path.stat().st_size for path in generated),
        "candidate_tree_sha256": tree_sha256(workspace),
    }


def _source_context(
    db: Database,
    payload: dict[str, Any],
    defaults: dict[str, str],
    *,
    record_table: str,
) -> dict[str, str]:
    """Resolve only whitelisted provenance fields; never archive arbitrary job payloads."""

    context = dict(defaults)
    context["lookup_status"] = "defaults"
    source_id = _clean(payload.get("source_id", ""))
    record_id_key = "course_id" if record_table == "courses" else "project_id"
    record_id = _clean(payload.get(record_id_key, ""))
    row: sqlite3.Row | None = None
    try:
        with db.connect() as connection:
            if record_id:
                extra = (
                    ",r.upstream_reference AS record_reference"
                    if record_table == "build_projects"
                    else ",NULL AS record_reference"
                )
                row = connection.execute(
                    f"""
                    SELECT s.source_id,s.name AS source_name,s.path AS source_path,
                           s.upstream_url,s.commit_hash,s.license,
                           r.{record_id_key} AS record_id{extra}
                    FROM {record_table} r JOIN sources s ON s.source_id=r.source_id
                    WHERE r.{record_id_key}=? AND s.is_active=1
                    """,
                    (record_id,),
                ).fetchone()
            elif source_id:
                row = connection.execute(
                    """
                    SELECT source_id,name AS source_name,path AS source_path,
                           upstream_url,commit_hash,license,NULL AS record_id,
                           NULL AS record_reference
                    FROM sources WHERE source_id=? AND is_active=1
                    """,
                    (source_id,),
                ).fetchone()
    except sqlite3.Error as error:
        context["lookup_status"] = f"database lookup unavailable: {_clean(error, limit=300)}"
    if row is not None:
        for key in ("source_name", "source_path", "upstream_url", "commit_hash", "license"):
            if row[key] is not None:
                context[key] = _clean(row[key])
        context["source_id"] = _clean(row["source_id"])
        if row["record_id"] is not None:
            context[record_id_key] = _clean(row["record_id"])
        if row["record_reference"] is not None:
            context["external_reference"] = _clean(row["record_reference"])
        context["lookup_status"] = "database"

    if payload.get("upstream_reference"):
        context["external_reference"] = _clean(payload["upstream_reference"])
    supplied_provenance = payload.get("provenance")
    if isinstance(supplied_provenance, dict):
        aliases = {
            "source": "source_name",
            "source_id": "source_id",
            "commit": "commit_hash",
            "upstream": "upstream_url",
            "license": "license",
            "catalog_license": "license",
            "catalog_entry": "external_reference",
        }
        for incoming, outgoing in aliases.items():
            if supplied_provenance.get(incoming):
                context[outgoing] = _clean(supplied_provenance[incoming])
        context["lookup_status"] = "job provenance"

    explicit = payload.get("source")
    if isinstance(explicit, dict):
        aliases = {
            "name": "source_name",
            "path": "source_path",
            "upstream_url": "upstream_url",
            "commit_hash": "commit_hash",
            "license": "license",
            "source_reference": "source_reference",
            "external_reference": "external_reference",
        }
        for incoming, outgoing in aliases.items():
            if explicit.get(incoming):
                context[outgoing] = _clean(explicit[incoming])
        context["lookup_status"] = "payload"
    if payload.get("job_id"):
        context["job_id"] = _clean(payload["job_id"])
    return context


def _syntax_checker() -> str:
    return r'''
        from __future__ import annotations

        import sys
        from pathlib import Path


        def main() -> int:
            failures: list[str] = []
            for path in sorted(Path(".").rglob("*.py")):
                try:
                    compile(path.read_text(encoding="utf-8"), str(path), "exec")
                except (OSError, SyntaxError, UnicodeError) as error:
                    failures.append(f"{path}: {error}")
            if failures:
                print("\n".join(failures), file=sys.stderr)
                return 1
            print("all Python sources compile")
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
    '''


def generate_course_slice(workspace: Path, payload: dict[str, Any], db: Database) -> SliceResult:
    """Generate and describe an independently validated MIT 6.S081 transfer slice."""

    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("course slice workspace must be an existing real directory")
    provenance = _source_context(db, payload, _CSDIY_DEFAULTS, record_table="courses")
    q = _yaml

    _write(
        workspace,
        "COURSE_MANIFEST.yaml",
        f"""
        schema_version: 1
        course_id: "mit-6-s081-cow-transfer"
        institution: "Massachusetts Institute of Technology"
        title: "MIT 6.S081 Operating System Engineering — COW Transfer Slice"
        topic: "operating-systems"
        status: "ASSIGNMENTS_ATTEMPTED"
        canonical_course_hours: 150
        slice_estimated_human_hours: 8
        difficulty: 8
        source:
          catalog: {q(provenance['source_name'])}
          upstream_url: {q(provenance['upstream_url'])}
          commit: {q(provenance['commit_hash'])}
          reference: {q(provenance['source_reference'])}
          course_website: {q(provenance['external_reference'])}
          license: {q(provenance['license'])}
        boundaries:
          student_material: "student_safe/"
          student_attempt: "attempts/target-learner/attempt-001/"
          examiner_material: "examiner_only/"
          student_can_read_examiner_material: false
        completion:
          metadata: "complete"
          environment: "ready-for-model-exercise"
          canonical_xv6_lab: "not-attempted-in-this-slice"
          transfer_attempt: "candidate-generated; consult factory catalog for promoted status"
          local_grading: "candidate-only; authoritative result is external to this snapshot"
          official_autograder: "not-used"
        """,
    )
    _write(
        workspace,
        "COURSE_PLAN.md",
        """
        # Course slice plan

        This is a deliberately narrow vertical slice, not a claim that MIT 6.S081 was completed.
        It uses the course's virtual-memory and copy-on-write themes to exercise the complete
        learning-factory path: catalog provenance, student-safe preparation, a preserved attempt,
        an examiner-only rubric, hidden transfer tests, and externally captured evidence.

        ## Sequence

        1. Review page tables, writable permissions, traps, and physical-page lifetime.
        2. State the invariants behind ordinary copy-on-write fork.
        3. Attempt the novel shared-page task without examiner material.
        4. Run public behavioral checks and preserve debugging notes.
        5. Submit one attempt to the independent examiner.
        6. Use failures as evidence for a later revision rather than rewriting history.

        ## Honest scope

        The original xv6 tree, course handouts, and solutions are not mirrored here. The generated
        exercise is an agent-authored semantic model linked to the public course and CSDIY catalog.
        Passing it is transfer evidence about lifetime and COW invariants, not official course credit.
        """,
    )
    _write(
        workspace,
        "ENVIRONMENT.md",
        """
        # Environment

        The exercise uses Python 3.11+ and only the standard library so its state transitions are
        easy to inspect. It models page-table behavior; it does not emulate RISC-V or replace xv6.

        From this archive root, an operator can grade the preserved attempt with:

        ```sh
        python3 examiner_only/grade_attempt.py
        ```

        The grader imports only the submitted implementation, adds examiner tests from a separate
        directory, writes `evaluations/attempt-001.json`, and exits nonzero on failure. A student view
        should be made by copying `student_safe/` only. Network access is unnecessary.
        """,
    )
    _write(
        workspace,
        "PREREQUISITES.md",
        """
        # Prerequisites

        - Translate a virtual page number through a per-process mapping.
        - Explain why a writable fork mapping cannot stay writable in both processes.
        - Distinguish a mapping reference from ownership of a physical frame.
        - Understand fork, page-fault handling, unmap, exec, and exit lifecycle events.
        - Use a lock to make a multi-step reference-count update atomic.

        Suggested remediation is to study the public xv6 book and relevant MIT 6.S081 schedule
        entries linked by `PROVENANCE.json`; no course solution is bundled.
        """,
    )
    unit_graph = {
        "schema_version": 1,
        "course_id": "mit-6-s081-cow-transfer",
        "nodes": [
            {"id": "vm-foundations", "order": 1, "type": "reading", "title": "Page-table and frame lifetime review"},
            {"id": "cow-invariants", "order": 2, "type": "lecture", "title": "Copy-on-write invariants"},
            {
                "id": "transfer-shared-pages",
                "order": 3,
                "type": "assignment",
                "title": "Shared pages between unrelated processes",
            },
            {"id": "external-exam", "order": 4, "type": "exam", "title": "Hidden lifecycle and concurrency evaluation"},
        ],
        "edges": [
            {"from": "vm-foundations", "to": "cow-invariants", "relation": "prerequisite", "inferred": True},
            {"from": "cow-invariants", "to": "transfer-shared-pages", "relation": "prerequisite", "inferred": True},
            {"from": "transfer-shared-pages", "to": "external-exam", "relation": "submission", "inferred": False},
        ],
    }
    _write_json(workspace, "UNIT_GRAPH.json", unit_graph)
    _write_json(
        workspace,
        "PROVENANCE.json",
        {
            "schema_version": 1,
            "source": provenance,
            "generated_material": {
                "classification": "agent-generated",
                "copied_course_text": False,
                "method": "deterministic vertical-slice template",
                "claims": [
                    "Course identity and public links are source-derived.",
                    "Exercise, implementation, tests, rubric, and notes are newly authored.",
                    "Measured grading evidence is written only by the external grader.",
                ],
            },
        },
    )
    _write(
        workspace,
        "student_safe/README.md",
        """
        # Student view

        Work only inside this directory. Read `READING.md`, then `TASK.md` and the complete callable
        contract in `API.md`. `starter/` contains method stubs and `public_tests/` provides examples. Examiner
        criteria and hidden tests are structurally outside this tree.

        Copy your implementation over `starter/shared_pages.py`, then run:

        ```sh
        python3 -m unittest discover -s public_tests -v
        ```
        """,
    )
    _write(
        workspace,
        "student_safe/TASK.md",
        """
        # Transfer task: named shared pages with COW coexistence

        Build a thread-safe semantic model that lets unrelated processes map a named physical page.
        Ordinary private writable mappings must become copy-on-write across `fork`; named shared
        mappings must remain genuinely shared across unrelated processes and across `fork`.

        Implement the exact `SharedPageSystem` contract in `API.md`: process creation, private allocation,
        named-segment creation, mapping, reading, writing, fork, unmap, exec, exit, unlink, and stats.

        Required invariants:

        - every page-table entry contributes exactly one mapping reference;
        - a private COW write clones only when another mapping still refers to the frame;
        - a named page is not reclaimed while named or mapped;
        - unlink removes the name but existing mappings remain valid;
        - exec/exit release every old mapping exactly once;
        - duplicate processes/mappings and out-of-range accesses fail explicitly;
        - all compound state changes are serialized so concurrent calls preserve invariants.

        This differs materially from merely implementing canonical COW fork: two unrelated processes
        can intentionally share writable state, so COW and shared mappings need distinct semantics.
        """,
    )
    _write(
        workspace,
        "student_safe/READING.md",
        """
        # Preparation: two kinds of writable sharing

        A page-table mapping and a physical frame have different lifetimes. Unmapping removes one
        mapping; it does not necessarily free the frame because another process or a persistent name
        may still own it. Track every ownership edge explicitly enough that teardown can remove it once.

        After `fork`, a private writable mapping initially points at the same bytes in both processes,
        but neither process may overwrite those shared bytes. The first writer receives a private copy
        only when another mapping still exists. In contrast, a named shared mapping is intentionally
        writable by multiple unrelated processes, so a write must remain visible through every mapping.

        Before coding, trace these events on paper: private allocate → fork → child write → parent exit;
        and name create → two maps → unlink → first unmap → second unmap. At each arrow list the process
        mappings, name owners, and frames that remain live.

        Checkpoint questions:

        1. Why is one undifferentiated reference count harder to debug than reciprocal owner sets?
        2. When can a COW writer safely reuse its existing frame instead of copying?
        3. Why must unlink preserve existing mappings?
        4. Which multi-step changes need the same lock to avoid a lost lifetime edge?
        """,
    )
    _write(
        workspace,
        "student_safe/API.md",
        """
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
        """,
    )
    _write(
        workspace,
        "student_safe/starter/shared_pages.py",
        r'''
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
        ''',
    )
    _write(
        workspace,
        "student_safe/public_tests/test_shared_pages.py",
        r'''
        from __future__ import annotations

        import unittest

        from shared_pages import SharedPageSystem


        class PublicBehaviorTests(unittest.TestCase):
            def test_private_page_becomes_copy_on_write(self) -> None:
                system = SharedPageSystem()
                system.create_process(1)
                system.alloc_private(1, 0, b"parent")
                system.fork(1, 2)
                system.write(2, 0, b"child")
                self.assertEqual(system.read(1, 0, 6), b"parent")
                self.assertEqual(system.read(2, 0, 5), b"child")

            def test_unrelated_processes_share_named_page(self) -> None:
                system = SharedPageSystem()
                system.create_process(10)
                system.create_process(20)
                system.create_shared("telemetry", b"zero")
                system.map_shared(10, 3, "telemetry")
                system.map_shared(20, 8, "telemetry")
                system.write(10, 3, b"live")
                self.assertEqual(system.read(20, 8, 4), b"live")

            def test_unlink_defers_reclamation(self) -> None:
                system = SharedPageSystem()
                system.create_process(1)
                system.create_shared("mailbox", b"message")
                system.map_shared(1, 4, "mailbox")
                system.unlink_shared("mailbox")
                self.assertEqual(system.read(1, 4, 7), b"message")
                system.unmap(1, 4)
                self.assertEqual(system.stats()["frame_count"], 0)


        if __name__ == "__main__":
            unittest.main()
        ''',
    )
    implementation = r'''
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
    '''
    _write(
        workspace,
        "attempts/target-learner/attempt-001/submission/shared_pages.py",
        implementation,
    )
    _write(
        workspace,
        "attempts/target-learner/attempt-001/reasoning-summary.md",
        """
        # Reasoning summary

        The attempt separates intentionally shared mappings from private mappings before implementing
        fork. It models both names and page tables as owners that can keep a frame alive. All mutations
        occur under one re-entrant lock so lifecycle operations can call common release logic safely.
        """,
    )
    _write(
        workspace,
        "attempts/target-learner/attempt-001/debugging-log.md",
        """
        # Debugging log

        - Hypothesis: one integer reference count would obscure which mapping leaked.
        - Experiment: represent mapping owners as `(pid, vpn)` pairs and assert behavior after unlink.
        - Observation: a named frame needs a separate lifetime edge even when it has no mappings.
        - Resolution: reclaim only when both mapping-owner and name-owner sets are empty.

        This is a concise reproducible account, not private chain-of-thought.
        """,
    )
    _write(
        workspace,
        "attempts/target-learner/attempt-001/mistakes.md",
        """
        # Mistakes and risks

        The first design sketch conflated writable sharing with copy-on-write. The corrected design
        carries an explicit `shared` bit. Remaining limitations include modeling only one-page named
        segments and serializing all operations with one lock.
        """,
    )
    _write(
        workspace,
        "attempts/target-learner/attempt-001/postmortem.md",
        """
        # Postmortem

        Passing the model does not establish kernel-level competence. It does expose whether the
        learner can keep fork, unlink, unmap, exec, and exit invariants consistent when ordinary COW
        and intentional sharing coexist. A later attempt should implement the mechanism in xv6 or a
        small native runtime and stress actual fault paths.
        """,
    )
    _write(
        workspace,
        "examiner_only/RUBRIC.md",
        """
        # Examiner rubric (not student-visible)

        - 30%: private fork mappings isolate on first write without unnecessary eager copies.
        - 25%: unrelated and forked processes retain intentional named sharing.
        - 25%: unmap, unlink, exec, and exit preserve exact frame lifetime.
        - 15%: concurrent operations leave coherent data and reference accounting.
        - 5%: invalid operations fail explicitly and the implementation remains readable.

        Mandatory failures override the numeric score: leaked examiner material, hidden-test mutation,
        unhandled lifecycle corruption, or a claimed pass unsupported by real command evidence.
        """,
    )
    _write(
        workspace,
        "examiner_only/hidden_tests/test_transfer.py",
        r'''
        from __future__ import annotations

        import threading
        import unittest

        from shared_pages import SharedPageSystem


        class HiddenTransferTests(unittest.TestCase):
            def test_fork_preserves_intentional_sharing(self) -> None:
                system = SharedPageSystem()
                system.create_process(1)
                system.create_shared("shared", b"before")
                system.map_shared(1, 1, "shared")
                system.fork(1, 2)
                system.write(2, 1, b"after!")
                self.assertEqual(system.read(1, 1, 6), b"after!")
                frame = next(iter(system.stats()["frames"].values()))
                self.assertEqual(frame["mapping_refs"], 2)

            def test_exec_and_exit_release_exactly_once(self) -> None:
                system = SharedPageSystem()
                system.create_process(1)
                system.alloc_private(1, 0, b"x")
                system.fork(1, 2)
                system.exec(1)
                self.assertEqual(system.stats()["frame_count"], 1)
                system.exit(2)
                self.assertEqual(system.stats()["frame_count"], 0)
                self.assertEqual(system.stats()["process_count"], 1)

            def test_cow_chain_does_not_leak(self) -> None:
                system = SharedPageSystem()
                system.create_process(1)
                system.alloc_private(1, 0, b"root")
                system.fork(1, 2)
                system.fork(2, 3)
                system.write(2, 0, b"two!")
                system.write(3, 0, b"tri!")
                self.assertEqual(system.read(1, 0, 4), b"root")
                self.assertEqual(system.read(2, 0, 4), b"two!")
                self.assertEqual(system.read(3, 0, 4), b"tri!")
                system.exit(1)
                system.exit(2)
                system.exit(3)
                self.assertEqual(system.stats()["frame_count"], 0)

            def test_concurrent_shared_writes_remain_valid(self) -> None:
                system = SharedPageSystem()
                system.create_shared("lanes")
                for pid in range(8):
                    system.create_process(pid)
                    system.map_shared(pid, 0, "lanes")

                def writer(pid: int) -> None:
                    for value in range(100):
                        system.write(pid, 0, bytes([value]), offset=pid)

                threads = [threading.Thread(target=writer, args=(pid,)) for pid in range(8)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                self.assertEqual(system.read(0, 0, 8), bytes([99]) * 8)
                frame = next(iter(system.stats()["frames"].values()))
                self.assertEqual(frame["mapping_refs"], 8)

            def test_invalid_operations_are_explicit(self) -> None:
                system = SharedPageSystem()
                system.create_process(1)
                with self.assertRaises(ValueError):
                    system.create_process(1)
                with self.assertRaises(KeyError):
                    system.read(1, 99, 1)
                with self.assertRaises(ValueError):
                    system.alloc_private(1, 0, b"x" * (system.PAGE_SIZE + 1))


        if __name__ == "__main__":
            unittest.main()
        ''',
    )
    _write(
        workspace,
        "examiner_only/grade_attempt.py",
        r'''
        from __future__ import annotations

        import io
        import json
        import sys
        import unittest
        from pathlib import Path


        ROOT = Path(__file__).resolve().parents[1]
        SUBMISSION = ROOT / "attempts/target-learner/attempt-001/submission"


        def main() -> int:
            sys.path.insert(0, str(SUBMISSION))
            suite = unittest.TestSuite(
                [
                    unittest.TestLoader().discover("student_safe/public_tests", pattern="test_*.py"),
                    unittest.TestLoader().discover("examiner_only/hidden_tests", pattern="test_*.py"),
                ]
            )
            stream = io.StringIO()
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
            report = {
                "attempt_id": "target-learner-attempt-001",
                "evaluator": "independent deterministic examiner",
                "result": "PASS" if result.wasSuccessful() else "FAIL",
                "tests_run": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "evidence": stream.getvalue().splitlines(),
            }
            destination = ROOT / "evaluations/attempt-001.json"
            destination.parent.mkdir(exist_ok=True)
            destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(stream.getvalue(), end="")
            print(json.dumps({key: report[key] for key in ("result", "tests_run", "failures", "errors")}))
            return 0 if result.wasSuccessful() else 1


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )
    _write(
        workspace,
        "scripts/verify_isolation.py",
        r'''
        from __future__ import annotations

        import sys
        from pathlib import Path


        def main() -> int:
            view = Path("student_safe")
            forbidden = {"sealed", "examiner_only", "hidden_tests", "rubric.md", "reference"}
            errors: list[str] = []
            for path in [view, *view.rglob("*")]:
                if path.is_symlink():
                    errors.append(f"symlink in student view: {path}")
                if path.name.casefold() in forbidden:
                    errors.append(f"forbidden name in student view: {path}")
            text = "\n".join(
                path.read_text(encoding="utf-8", errors="replace").casefold()
                for path in view.rglob("*")
                if path.is_file()
            )
            for marker in ("examiner_only/", "hidden_tests/", "rubric.md"):
                if marker in text:
                    errors.append(f"student material leaks examiner path marker: {marker}")
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 1
            print("student tree contains no examiner paths, sealed material, or symlinks")
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )
    _write(workspace, "scripts/check_python.py", _syntax_checker())

    validators: list[dict[str, Any]] = [
        {
            "type": "required_paths",
            "name": "course-archive-layout",
            "paths": [
                "COURSE_MANIFEST.yaml",
                "COURSE_PLAN.md",
                "ENVIRONMENT.md",
                "PREREQUISITES.md",
                "UNIT_GRAPH.json",
                "PROVENANCE.json",
                "student_safe/TASK.md",
                "student_safe/READING.md",
                "student_safe/API.md",
                "student_safe/starter/shared_pages.py",
                "student_safe/public_tests/test_shared_pages.py",
                "attempts/target-learner/attempt-001/submission/shared_pages.py",
                "attempts/target-learner/attempt-001/debugging-log.md",
                "examiner_only/RUBRIC.md",
                "examiner_only/hidden_tests/test_transfer.py",
                "examiner_only/grade_attempt.py",
            ],
        },
        {
            "type": "forbidden_paths",
            "name": "student-view-separation",
            "paths": [
                "student_safe/examiner_only",
                "student_safe/sealed",
                "student_safe/hidden_tests",
                "student_safe/RUBRIC.md",
            ],
        },
        {
            "type": "command",
            "name": "student-view-content-audit",
            "argv": ["python3", "scripts/verify_isolation.py"],
            "timeout_seconds": 30,
        },
        {
            "type": "json_fields",
            "name": "unit-graph-schema",
            "path": "UNIT_GRAPH.json",
            "required": ["schema_version", "course_id", "nodes", "edges"],
        },
        {
            "type": "command",
            "name": "course-python-syntax",
            "argv": ["python3", "scripts/check_python.py"],
            "claims": ["BUILDS"],
            "timeout_seconds": 30,
        },
        {
            "type": "command",
            "name": "independent-transfer-grader",
            "argv": ["python3", "examiner_only/grade_attempt.py"],
            "produces": ["evaluations/attempt-001.json"],
            "claims": ["TESTED", "TRANSFER_VERIFIED"],
            "timeout_seconds": 60,
        },
        {
            "type": "json_fields",
            "name": "grade-evidence-recorded",
            "path": "evaluations/attempt-001.json",
            "required": ["attempt_id", "evaluator", "result", "tests_run", "failures", "errors", "evidence"],
        },
        {"type": "tree_checksum", "name": "course-tree-checksum"},
    ]
    metadata = {
        "name": "MIT 6.S081 COW transfer vertical slice",
        "family": "operating-systems",
        "type": "course-transfer",
        "languages": ["Python semantic model", "C/RISC-V course context"],
        "concepts": ["copy-on-write", "reference counting", "shared memory", "process lifecycle", "concurrency"],
        "difficulty": 8,
        "estimated_human_hours": 8,
        "provenance": provenance,
        "validation_target": "TRANSFER_VERIFIED",
        "student_boundary": "student_safe/ only",
    }
    evidence = {
        "handler": "generate_course_slice",
        "course_id": "mit-6-s081-cow-transfer",
        "student_attempt": "attempts/target-learner/attempt-001",
        "external_validation_required": True,
        "validator_count": len(validators),
        **_workspace_summary(workspace),
    }
    return SliceResult(evidence, validators, "course_vertical_slice", "courses/mit-6-s081/cow-transfer", metadata)


def generate_project_slice(workspace: Path, payload: dict[str, Any], db: Database) -> SliceResult:
    """Generate a complete, standard-library persistent KV-store challenge pack."""

    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("project slice workspace must be an existing real directory")
    provenance = _source_context(db, payload, _BYOX_DEFAULTS, record_table="build_projects")
    q = _yaml

    _write(
        workspace,
        "README.md",
        """
        # Durable Bytes: a persistent key-value store challenge

        Build a bytes-to-bytes store that begins as an in-memory map and evolves into a recoverable,
        append-only persistent system. The future learner sees requirements, starter code, and public
        tests first. References, deeper tests, design commentary, and expected reviews live under
        `sealed/` and should be revealed intentionally.

        ## Learner workflow

        ```sh
        PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
        # After implementing, reveal and compare intentionally:
        PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -v
        PYTHONPATH=production/implementation python3 -m unittest discover -s sealed/reference_tests -v
        ```

        `production/implementation` is a stable archive path for an instrumented teaching variant;
        it is not a claim of production readiness. See `production/PRODUCTIONIZATION.md` for the
        unresolved deployment work.

        ## Exact validation commands

        Run every bounded check and write fresh benchmark evidence:

        ```sh
        python3 scripts/run_all.py
        ```

        Or run the stages individually from this archive root:

        ```sh
        python3 environment/check_python.py
        PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -v
        PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -v
        PYTHONPATH=production/implementation python3 -m unittest discover -s public_tests -v
        PYTHONPATH=production/implementation python3 -m unittest discover -s sealed/reference_tests -v
        KVSTORE_IMPL=reference python3 adversarial/fuzz/model_fuzz.py --operations 600
        KVSTORE_IMPL=production python3 adversarial/fuzz/model_fuzz.py --operations 600
        KVSTORE_IMPL=production python3 adversarial/stress/thread_stress.py --threads 6 --operations 80
        KVSTORE_IMPL=production python3 adversarial/fault-injection/torn_tail.py
        ! KVSTORE_IMPL=buggy python3 debugging/lost-delete/test_bug.py
        KVSTORE_IMPL=reference python3 debugging/lost-delete/test_bug.py
        python3 benchmarks/benchmark.py --operations 500 --output benchmarks/results/smoke.json
        ```

        The leading `!` marks the intentionally failing buggy regression as a successful
        reproduction. `KVSTORE_IMPL` accepts `reference` or `production` in adversarial scripts and
        also accepts `buggy` in the debugging regression.

        The archive also includes deterministic fuzzing, concurrency stress, crash-tail fault
        injection, an actual benchmark harness, a single-root-cause debugging challenge, and a
        realistic code-review exercise. All implementation prose and code were newly authored; the
        upstream catalog and tutorial are linked only as provenance.
        """,
    )
    _write(
        workspace,
        "MANIFEST.yaml",
        f"""
        schema_version: 2
        artifact_revision: 2
        project_id: "durable-bytes-kv"
        title: "Durable Bytes Persistent Key-Value Store"
        family: "storage-database"
        category: "Database"
        language: "Python"
        difficulty: 7
        estimated_human_hours: 14
        production_relevance: 6
        cs_depth: 7
        debugging_value: 9
        architecture_value: 8
        validation_status: "EDUCATIONAL_CANDIDATE_REQUIRES_EXTERNAL_VALIDATION"
        deployment_status: "NOT_PRODUCTION_READY"
        source:
          catalog: {q(provenance['source_name'])}
          upstream_url: {q(provenance['upstream_url'])}
          commit: {q(provenance['commit_hash'])}
          reference: {q(provenance['source_reference'])}
          external_tutorial: {q(provenance['external_reference'])}
          license: {q(provenance['license'])}
        artifacts:
          starter: true
          public_tests: true
          sealed_reference: true
          alternatives: 2
          productionized: false
          instrumented_variant: true
          fuzzing: true
          stress: true
          fault_injection: true
          benchmarks: true
          debugging_challenges: 1
          review_exercises: 1
        """,
    )
    _write(
        workspace,
        "REQUIREMENTS.md",
        """
        # Requirements

        Implement `KVStore(path, *, sync=True)` with `set`, `get`, `delete`, `batch`, `keys`,
        `compact`, `close`, and context-manager support. Keys and values are bytes.

        Correctness requirements:

        - acknowledged mutations survive close and reopen when synchronization is enabled;
        - every batch is all-or-nothing during replay because it occupies one checksummed record;
        - a truncated final record is treated as an interrupted append, not invented data;
        - corruption in any complete record is reported rather than silently ignored;
        - delete of a missing key returns false and does not append a record;
        - compaction preserves logical contents and atomically replaces the old log;
        - public methods remain safe under concurrent threads and reject use after close;
        - keys and values are bounded so untrusted input cannot force unbounded single records.

        The implementation must use only the Python standard library. Do not modify authoritative
        tests to obtain a pass. Record design tradeoffs and measurements rather than fabricating them.
        """,
    )
    _write(
        workspace,
        "CONCEPTS.md",
        """
        # Concepts

        - write-ahead append logs and replay
        - checksums versus framing
        - atomic logical batches
        - torn-tail recovery versus mid-log corruption
        - fsync, rename, and directory durability
        - compaction and write amplification
        - lifecycle, locking, bounds, and observability
        - differential/model-based testing

        The task intentionally stops short of a B+ tree or LSM tree. Extensions ask the learner to
        add indexing and segment rotation only after the durability contract is understood.
        """,
    )
    _write(
        workspace,
        "DESIGN_QUESTIONS.md",
        """
        # Design questions

        1. Which failures can a checksum detect, and which can it not prevent?
        2. Why is an entire batch encoded in one record instead of several operation records?
        3. What guarantee does `flush()` provide compared with `fsync()`?
        4. Why must compaction fsync the replacement before rename, and the directory after rename?
        5. Should readers block during compaction? What changes with immutable segments?
        6. How would multiple processes coordinate writers without trusting process existence?
        7. What metrics distinguish healthy append growth from a compaction incident?
        """,
    )
    _write_json(
        workspace,
        "PROVENANCE.json",
        {
            "schema_version": 1,
            "source": provenance,
            "generated_material": {
                "classification": "agent-generated",
                "copied_tutorial_text_or_code": False,
                "method": "deterministic vertical-slice template",
                "measured_outputs": ["benchmarks/results/smoke.json (created by validator)"],
                "inferred_metadata": ["difficulty", "concepts", "production relevance"],
            },
        },
    )
    _write(
        workspace,
        "AGENTS.md",
        """
        # Challenge-local agent guide

        Student-visible work is limited to the root learning documents, `starter/`, `public_tests/`,
        and `environment/`. Do not reveal or copy `sealed/` while simulating a student. Examiners must
        run tests from an independent path and preserve real exit codes. Benchmark results must be
        produced by `benchmarks/benchmark.py`; never hand-edit measurements.
        """,
    )
    _write(
        workspace,
        "starter/kvstore.py",
        r'''
        from __future__ import annotations

        from pathlib import Path
        from typing import Iterable


        class KVStore:
            MAX_KEY_BYTES = 1024
            MAX_VALUE_BYTES = 1024 * 1024

            def __init__(self, path: str | Path, *, sync: bool = True) -> None:
                self.path = Path(path)
                self.sync = sync
                self._data: dict[bytes, bytes] = {}
                # TODO: create/replay the append log and initialize lifecycle synchronization.

            def set(self, key: bytes, value: bytes) -> None:
                raise NotImplementedError

            def get(self, key: bytes) -> bytes | None:
                return self._data.get(key)

            def delete(self, key: bytes) -> bool:
                raise NotImplementedError

            def batch(self, operations: Iterable[tuple[str, bytes, bytes | None]]) -> None:
                raise NotImplementedError

            def keys(self) -> list[bytes]:
                return sorted(self._data)

            def compact(self) -> None:
                raise NotImplementedError

            def close(self) -> None:
                raise NotImplementedError

            def __enter__(self) -> "KVStore":
                return self

            def __exit__(self, *_: object) -> None:
                self.close()
        ''',
    )
    _write(
        workspace,
        "public_tests/test_contract.py",
        r'''
        from __future__ import annotations

        import tempfile
        import unittest
        from pathlib import Path

        from kvstore import KVStore


        class PublicContractTests(unittest.TestCase):
            def setUp(self) -> None:
                self.temporary = tempfile.TemporaryDirectory()
                self.path = Path(self.temporary.name) / "store.log"

            def tearDown(self) -> None:
                self.temporary.cleanup()

            def test_round_trip_and_reopen(self) -> None:
                with KVStore(self.path) as store:
                    store.set(b"alpha", b"one")
                    store.set(b"binary\x00key", b"binary\xffvalue")
                    self.assertEqual(store.get(b"alpha"), b"one")
                with KVStore(self.path) as store:
                    self.assertEqual(store.get(b"alpha"), b"one")
                    self.assertEqual(store.get(b"binary\x00key"), b"binary\xffvalue")

            def test_delete_result_and_persistence(self) -> None:
                with KVStore(self.path) as store:
                    self.assertFalse(store.delete(b"missing"))
                    store.set(b"doomed", b"value")
                    self.assertTrue(store.delete(b"doomed"))
                    self.assertIsNone(store.get(b"doomed"))
                with KVStore(self.path) as store:
                    self.assertIsNone(store.get(b"doomed"))

            def test_atomic_batch_and_sorted_keys(self) -> None:
                with KVStore(self.path) as store:
                    store.set(b"remove", b"x")
                    store.batch([
                        ("set", b"z", b"last"),
                        ("set", b"a", b"first"),
                        ("delete", b"remove", None),
                    ])
                    self.assertEqual(store.keys(), [b"a", b"z"])

            def test_compaction_preserves_state(self) -> None:
                with KVStore(self.path) as store:
                    for number in range(30):
                        store.set(b"key", str(number).encode())
                    before = self.path.stat().st_size
                    store.compact()
                    after = self.path.stat().st_size
                    self.assertLess(after, before)
                with KVStore(self.path) as store:
                    self.assertEqual(store.get(b"key"), b"29")


        if __name__ == "__main__":
            unittest.main()
        ''',
    )
    _write(
        workspace,
        "environment/README.md",
        """
        # Reproducible environment

        Requires CPython 3.11+ on a POSIX-like system and no third-party packages. Validators set
        `PYTHONDONTWRITEBYTECODE=1`, use temporary directories, and make no network requests.

        Exact individual commands and the `python3 scripts/run_all.py` entry point are listed in the
        root README. Adversarial scripts resolve `KVSTORE_IMPL=reference` or
        `KVSTORE_IMPL=production` themselves; no `PYTHONPATH` is required for those scripts. The
        debugging regression additionally accepts `KVSTORE_IMPL=buggy`. Benchmark JSON captures
        Python/platform metadata, command parameters, per-operation aggregate timings, and summaries.
        """,
    )
    _write(workspace, "environment/check_python.py", _syntax_checker())
    _write(
        workspace,
        "scripts/run_all.py",
        r'''
        from __future__ import annotations

        import os
        import subprocess
        import sys
        from pathlib import Path


        ROOT = Path(__file__).resolve().parents[1]
        PYTHON = sys.executable
        STAGES: list[tuple[str, list[str], dict[str, str], int]] = [
            ("syntax", [PYTHON, "environment/check_python.py"], {}, 0),
            (
                "reference public tests",
                [PYTHON, "-m", "unittest", "discover", "-s", "public_tests", "-v"],
                {"PYTHONPATH": str(ROOT / "sealed/reference")},
                0,
            ),
            (
                "reference recovery tests",
                [PYTHON, "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"],
                {"PYTHONPATH": str(ROOT / "sealed/reference")},
                0,
            ),
            (
                "instrumented public tests",
                [PYTHON, "-m", "unittest", "discover", "-s", "public_tests", "-v"],
                {"PYTHONPATH": str(ROOT / "production/implementation")},
                0,
            ),
            (
                "instrumented recovery tests",
                [PYTHON, "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"],
                {"PYTHONPATH": str(ROOT / "production/implementation")},
                0,
            ),
            (
                "reference model fuzz",
                [PYTHON, "adversarial/fuzz/model_fuzz.py", "--operations", "600"],
                {"KVSTORE_IMPL": "reference"},
                0,
            ),
            (
                "instrumented model fuzz",
                [PYTHON, "adversarial/fuzz/model_fuzz.py", "--operations", "600"],
                {"KVSTORE_IMPL": "production"},
                0,
            ),
            (
                "instrumented thread stress",
                [PYTHON, "adversarial/stress/thread_stress.py", "--threads", "6", "--operations", "80"],
                {"KVSTORE_IMPL": "production"},
                0,
            ),
            (
                "instrumented torn-tail fault",
                [PYTHON, "adversarial/fault-injection/torn_tail.py"],
                {"KVSTORE_IMPL": "production"},
                0,
            ),
            (
                "debugging defect reproduction",
                [PYTHON, "debugging/lost-delete/test_bug.py"],
                {"KVSTORE_IMPL": "buggy"},
                1,
            ),
            (
                "debugging reference regression",
                [PYTHON, "debugging/lost-delete/test_bug.py"],
                {"KVSTORE_IMPL": "reference"},
                0,
            ),
            (
                "measured smoke benchmark",
                [
                    PYTHON,
                    "benchmarks/benchmark.py",
                    "--operations",
                    "500",
                    "--output",
                    "benchmarks/results/smoke.json",
                ],
                {},
                0,
            ),
        ]


        def main() -> int:
            for name, command, additions, expected_exit in STAGES:
                environment = os.environ.copy()
                environment["PYTHONDONTWRITEBYTECODE"] = "1"
                environment.update(additions)
                print(f"==> {name}", flush=True)
                completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
                if completed.returncode != expected_exit:
                    print(
                        f"{name}: expected exit {expected_exit}, got {completed.returncode}",
                        file=sys.stderr,
                    )
                    return 1
            print("all bounded validation stages behaved as expected")
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )

    reference = r'''
        from __future__ import annotations

        import base64
        import json
        import os
        import threading
        import zlib
        from pathlib import Path
        from typing import Iterable


        class CorruptLogError(RuntimeError):
            pass


        class KVStore:
            MAX_KEY_BYTES = 1024
            MAX_VALUE_BYTES = 1024 * 1024
            MAX_RECORD_BYTES = 4 * 1024 * 1024

            def __init__(self, path: str | Path, *, sync: bool = True) -> None:
                self.path = Path(path)
                self.sync = bool(sync)
                self._lock = threading.RLock()
                self._closed = False
                self._poisoned = False
                self._data: dict[bytes, bytes] = {}
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._replay()
                self._file = self.path.open("ab", buffering=0)

            @staticmethod
            def _b64(value: bytes) -> str:
                return base64.b64encode(value).decode("ascii")

            @staticmethod
            def _unb64(value: object) -> bytes:
                if not isinstance(value, str):
                    raise CorruptLogError("encoded bytes must be a string")
                try:
                    return base64.b64decode(value, validate=True)
                except (ValueError, TypeError) as error:
                    raise CorruptLogError("invalid base64 in log") from error

            def _check_open(self) -> None:
                if self._closed:
                    raise RuntimeError("store is closed")
                if self._poisoned:
                    raise RuntimeError("store is unavailable after a persistence failure")

            @staticmethod
            def _write_all(stream: object, data: bytes) -> None:
                remaining = memoryview(data)
                while remaining:
                    written = stream.write(remaining)
                    if not isinstance(written, int) or written <= 0 or written > len(remaining):
                        raise OSError("write returned an invalid byte count")
                    remaining = remaining[written:]

            def _poison(self) -> None:
                self._poisoned = True
                try:
                    self._file.close()
                except Exception:
                    pass

            @staticmethod
            def _discard_temporary(path: Path) -> None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

            def _check_key(self, key: bytes) -> None:
                if not isinstance(key, bytes):
                    raise TypeError("keys must be bytes")
                if not key or len(key) > self.MAX_KEY_BYTES:
                    raise ValueError("key length is out of bounds")

            def _check_value(self, value: bytes) -> None:
                if not isinstance(value, bytes):
                    raise TypeError("values must be bytes")
                if len(value) > self.MAX_VALUE_BYTES:
                    raise ValueError("value length is out of bounds")

            def _encode(self, operations: list[tuple[str, bytes, bytes | None]]) -> bytes:
                body = json.dumps(
                    {
                        "version": 1,
                        "ops": [
                            {"op": op, "key": self._b64(key), "value": self._b64(value) if value is not None else None}
                            for op, key, value in operations
                        ],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                envelope = json.dumps(
                    {"body": body.decode("utf-8"), "crc32": f"{zlib.crc32(body) & 0xffffffff:08x}"},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8") + b"\n"
                if len(envelope) > self.MAX_RECORD_BYTES:
                    raise ValueError("batch is too large")
                return envelope

            def _decode(self, raw: bytes, line_number: int) -> list[tuple[str, bytes, bytes | None]]:
                try:
                    envelope = json.loads(raw)
                    body_text = envelope["body"]
                    if not isinstance(body_text, str):
                        raise TypeError("body is not text")
                    body = body_text.encode("utf-8")
                    if envelope["crc32"] != f"{zlib.crc32(body) & 0xffffffff:08x}":
                        raise CorruptLogError("checksum mismatch")
                    decoded = json.loads(body)
                    if not isinstance(decoded, dict):
                        raise CorruptLogError("record body must be an object")
                    if decoded.get("version") != 1 or not isinstance(decoded.get("ops"), list):
                        raise CorruptLogError("unsupported record")
                    result: list[tuple[str, bytes, bytes | None]] = []
                    for item in decoded["ops"]:
                        op = item["op"]
                        key = self._unb64(item["key"])
                        value = self._unb64(item["value"]) if item.get("value") is not None else None
                        if op not in {"set", "delete"} or (op == "set") != (value is not None):
                            raise CorruptLogError("invalid operation")
                        self._check_key(key)
                        if value is not None:
                            self._check_value(value)
                        result.append((op, key, value))
                    return result
                except CorruptLogError:
                    raise
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                    raise CorruptLogError(f"invalid complete record at line {line_number}") from error

            def _apply(self, operations: Iterable[tuple[str, bytes, bytes | None]]) -> None:
                for op, key, value in operations:
                    if op == "set":
                        assert value is not None
                        self._data[key] = value
                    else:
                        self._data.pop(key, None)

            def _replay(self) -> None:
                if not self.path.exists():
                    return
                raw = self.path.read_bytes()
                lines = raw.splitlines(keepends=True)
                valid_bytes = 0
                for index, line in enumerate(lines, start=1):
                    if not line.endswith(b"\n"):
                        if index == len(lines):
                            with self.path.open("r+b") as stream:
                                stream.truncate(valid_bytes)
                                stream.flush()
                                if self.sync:
                                    os.fsync(stream.fileno())
                            break
                        raise CorruptLogError(f"unterminated non-tail record at line {index}")
                    if len(line) > self.MAX_RECORD_BYTES:
                        raise CorruptLogError(f"oversized record at line {index}")
                    self._apply(self._decode(line, index))
                    valid_bytes += len(line)

            def _append(self, operations: list[tuple[str, bytes, bytes | None]]) -> None:
                record = self._encode(operations)
                completed = False
                try:
                    self._write_all(self._file, record)
                    if self.sync:
                        os.fsync(self._file.fileno())
                    completed = True
                finally:
                    if not completed:
                        self._poison()

            def set(self, key: bytes, value: bytes) -> None:
                self.batch([("set", key, value)])

            def get(self, key: bytes) -> bytes | None:
                self._check_key(key)
                with self._lock:
                    self._check_open()
                    return self._data.get(key)

            def delete(self, key: bytes) -> bool:
                self._check_key(key)
                with self._lock:
                    self._check_open()
                    if key not in self._data:
                        return False
                    self._append([("delete", key, None)])
                    self._data.pop(key)
                    return True

            def batch(self, operations: Iterable[tuple[str, bytes, bytes | None]]) -> None:
                normalized = list(operations)
                for op, key, value in normalized:
                    if op not in {"set", "delete"}:
                        raise ValueError(f"unknown operation: {op}")
                    self._check_key(key)
                    if op == "set":
                        if value is None:
                            raise ValueError("set requires a value")
                        self._check_value(value)
                    elif value is not None:
                        raise ValueError("delete value must be None")
                with self._lock:
                    self._check_open()
                    if not normalized:
                        return
                    self._append(normalized)
                    self._apply(normalized)

            def keys(self) -> list[bytes]:
                with self._lock:
                    self._check_open()
                    return sorted(self._data)

            def compact(self) -> None:
                with self._lock:
                    self._check_open()
                    operations = [("set", key, value) for key, value in sorted(self._data.items())]
                    temporary = self.path.with_name(self.path.name + ".compact.tmp")
                    record = self._encode(operations) if operations else b""
                    replaced = False
                    try:
                        with temporary.open("wb", buffering=0) as stream:
                            self._write_all(stream, record)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary, self.path)
                        replaced = True
                        try:
                            replacement = self.path.open("ab", buffering=0)
                        except BaseException:
                            self._poison()
                            raise
                        previous = self._file
                        self._file = replacement
                        previous.close()
                        if hasattr(os, "O_DIRECTORY"):
                            directory_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
                            try:
                                os.fsync(directory_fd)
                            finally:
                                os.close(directory_fd)
                    finally:
                        if not replaced:
                            self._discard_temporary(temporary)

            def close(self) -> None:
                with self._lock:
                    if not self._closed:
                        try:
                            self._file.close()
                        finally:
                            self._closed = True

            def __enter__(self) -> "KVStore":
                self._check_open()
                return self

            def __exit__(self, *_: object) -> None:
                self.close()
    '''
    _write(workspace, "sealed/reference/kvstore.py", reference)
    _write(
        workspace,
        "sealed/reference_tests/test_recovery.py",
        r'''
        from __future__ import annotations

        import json
        import os
        import tempfile
        import threading
        import unittest
        import zlib
        from pathlib import Path
        from unittest import mock

        import kvstore
        from kvstore import CorruptLogError, KVStore


        class RecoveryAndBoundsTests(unittest.TestCase):
            def setUp(self) -> None:
                self.temporary = tempfile.TemporaryDirectory()
                self.path = Path(self.temporary.name) / "store.log"

            def tearDown(self) -> None:
                self.temporary.cleanup()

            def test_truncated_tail_is_ignored(self) -> None:
                with KVStore(self.path) as store:
                    store.set(b"safe", b"committed")
                with self.path.open("ab") as stream:
                    stream.write(b'{"body":"interrupted')
                with KVStore(self.path) as store:
                    self.assertEqual(store.get(b"safe"), b"committed")

            def test_complete_corruption_is_rejected(self) -> None:
                with KVStore(self.path) as store:
                    store.set(b"safe", b"committed")
                data = bytearray(self.path.read_bytes())
                data[data.index(b"crc32") + 9] = ord("f") if data[data.index(b"crc32") + 9] != ord("f") else ord("e")
                self.path.write_bytes(data)
                with self.assertRaises(CorruptLogError):
                    KVStore(self.path)

            def test_checksummed_wrong_shape_is_normalized_as_corruption(self) -> None:
                body = b"[]"
                envelope = json.dumps(
                    {
                        "body": body.decode("ascii"),
                        "crc32": f"{zlib.crc32(body) & 0xffffffff:08x}",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8") + b"\n"
                self.path.write_bytes(envelope)
                with self.assertRaises(CorruptLogError):
                    KVStore(self.path)

            def test_batch_validation_happens_before_append(self) -> None:
                with KVStore(self.path) as store:
                    store.set(b"existing", b"value")
                    before = self.path.stat().st_size
                    with self.assertRaises(ValueError):
                        store.batch([("set", b"valid", b"x"), ("invalid", b"bad", None)])
                    self.assertEqual(self.path.stat().st_size, before)
                    self.assertIsNone(store.get(b"valid"))

            def test_bounds_and_closed_lifecycle(self) -> None:
                store = KVStore(self.path)
                with self.assertRaises(ValueError):
                    store.set(b"", b"x")
                with self.assertRaises(ValueError):
                    store.set(b"k", b"x" * (store.MAX_VALUE_BYTES + 1))
                store.close()
                with self.assertRaises(RuntimeError):
                    store.get(b"k")
                with self.assertRaises(RuntimeError):
                    store.batch([])

            def test_short_writes_are_completed_before_acknowledgement(self) -> None:
                store = KVStore(self.path)
                underlying = store._file

                class ShortWriter:
                    calls = 0

                    def write(self, data: object) -> int:
                        chunk = bytes(data)
                        self.calls += 1
                        return underlying.write(chunk[:max(1, len(chunk) // 3)])

                    def fileno(self) -> int:
                        return underlying.fileno()

                    def close(self) -> None:
                        underlying.close()

                writer = ShortWriter()
                store._file = writer
                store.set(b"short", b"complete")
                self.assertGreater(writer.calls, 1)
                store.close()
                with KVStore(self.path) as reopened:
                    self.assertEqual(b"complete", reopened.get(b"short"))

            def test_partial_write_failure_poisons_store(self) -> None:
                store = KVStore(self.path, sync=False)
                underlying = store._file

                class FailingWriter:
                    attempted = False

                    def write(self, data: object) -> int:
                        if not self.attempted:
                            self.attempted = True
                            underlying.write(bytes(data)[:7])
                        raise OSError("injected append failure")

                    def fileno(self) -> int:
                        return underlying.fileno()

                    def close(self) -> None:
                        underlying.close()

                store._file = FailingWriter()
                with self.assertRaisesRegex(OSError, "injected append failure"):
                    store.set(b"uncertain", b"value")
                with self.assertRaisesRegex(RuntimeError, "persistence failure"):
                    store.get(b"uncertain")
                store.close()
                with KVStore(self.path) as reopened:
                    self.assertIsNone(reopened.get(b"uncertain"))

            def test_failed_replace_keeps_original_store_usable(self) -> None:
                store = KVStore(self.path, sync=False)
                store.set(b"before", b"value")
                with mock.patch.object(kvstore.os, "replace", side_effect=OSError("injected replace failure")):
                    with self.assertRaisesRegex(OSError, "injected replace failure"):
                        store.compact()
                self.assertFalse(self.path.with_name(self.path.name + ".compact.tmp").exists())
                store.set(b"after", b"value")
                store.close()
                with KVStore(self.path) as reopened:
                    self.assertEqual([b"after", b"before"], reopened.keys())

            @unittest.skipUnless(hasattr(os, "O_DIRECTORY"), "directory fsync requires POSIX O_DIRECTORY")
            def test_directory_fsync_failure_keeps_replacement_usable(self) -> None:
                store = KVStore(self.path, sync=False)
                store.set(b"before", b"value")
                real_fsync = kvstore.os.fsync
                calls = 0

                def fail_second_fsync(file_descriptor: int) -> None:
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise OSError("injected directory fsync failure")
                    real_fsync(file_descriptor)

                with mock.patch.object(kvstore.os, "fsync", side_effect=fail_second_fsync):
                    with self.assertRaisesRegex(OSError, "injected directory fsync failure"):
                        store.compact()
                store.set(b"after", b"value")
                store.close()
                with KVStore(self.path) as reopened:
                    self.assertEqual([b"after", b"before"], reopened.keys())

            def test_concurrent_unique_writes_survive_replay(self) -> None:
                with KVStore(self.path, sync=False) as store:
                    def writer(worker: int) -> None:
                        for item in range(50):
                            key = f"{worker}:{item}".encode()
                            store.set(key, b"value")

                    threads = [threading.Thread(target=writer, args=(worker,)) for worker in range(6)]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join()
                    self.assertEqual(len(store.keys()), 300)
                with KVStore(self.path) as store:
                    self.assertEqual(len(store.keys()), 300)


        if __name__ == "__main__":
            unittest.main()
        ''',
    )
    _write(
        workspace,
        "sealed/DESIGN.md",
        """
        # Reference design

        Each newline-delimited envelope contains a canonical JSON body and CRC32. The body contains
        one logical batch, so replay never observes a prefix of a validated batch. The index is an
        in-memory dictionary reconstructed at startup. A single re-entrant lock serializes appends and
        index changes. Compaction emits one snapshot batch to a sibling temporary file, fsyncs it,
        atomically renames it, and fsyncs the directory where supported.

        CRC32 detects accidental corruption but is not authentication. A final unterminated line is
        ignored as a torn append; malformed complete lines fail closed. This distinction is tested.
        """,
    )
    _write(
        workspace,
        "sealed/TRADEOFFS.md",
        """
        # Tradeoffs

        The design favors auditability over throughput: JSON/base64 adds space, one lock limits
        concurrency, replay is O(log size), and compaction pauses writers. In exchange, batches and
        corruption policy are visible without custom tooling. A binary frame would reduce space;
        immutable segments plus a manifest would bound recovery and compaction pauses; a B+ tree
        would enable ordered range scans at greater update complexity.
        """,
    )
    _write(
        workspace,
        "sealed/REVIEW.md",
        """
        # Reference review

        The reference is suitable for teaching and passes its bounded test contract. It is not a
        multi-process database, CRC32 is not adversarial integrity, and one giant snapshot record can
        exceed the configured record bound for a sufficiently large database. Production deployments
        would require segmented logs, a lock protocol, explicit compatibility/version migration,
        stronger recovery testing, and capacity planning.
        """,
    )

    production = reference.replace(
        "import threading\n",
        "import threading\n        import time\n        from collections import Counter\n",
        1,
    ).replace(
        "self._data: dict[bytes, bytes] = {}\n",
        "self._data: dict[bytes, bytes] = {}\n"
        "                self._metrics: Counter[str] = Counter()\n"
        "                self._opened_at = time.monotonic()\n",
        1,
    ).replace(
        "self._data[key] = value\n",
        "self._data[key] = value\n                        self._metrics[\"logical_sets\"] += 1\n",
        1,
    ).replace(
        "self._data.pop(key, None)\n",
        "self._data.pop(key, None)\n                        self._metrics[\"logical_deletes\"] += 1\n",
        1,
    ).replace(
        "self._data.pop(key)\n                    return True",
        "self._data.pop(key)\n"
        "                    self._metrics[\"logical_deletes\"] += 1\n"
        "                    return True",
        1,
    ).replace(
        "def close(self) -> None:\n",
        '''def metrics(self) -> dict[str, int | float]:
                with self._lock:
                    return {
                        **dict(self._metrics),
                        "live_keys": len(self._data),
                        "uptime_seconds": time.monotonic() - self._opened_at,
                    }

            def health(self) -> dict[str, object]:
                with self._lock:
                    if self._closed:
                        status = "closed"
                    elif self._poisoned:
                        status = "degraded"
                    else:
                        status = "ok"
                    return {"status": status, "path": str(self.path)}

            def close(self) -> None:
''',
        1,
    )
    _write(workspace, "production/implementation/kvstore.py", production)
    _write(
        workspace,
        "production/PRODUCTIONIZATION.md",
        """
        # Instrumented variant and production gap review

        Despite its stable `production/implementation` archive path, this is an instrumented teaching
        variant, not a production-ready database. It keeps the tested storage format and adds basic
        lifecycle/health reporting and in-process logical-operation counters. Those counters are
        illustrative and are not a replacement for durable telemetry, logs, traces, or latency
        histograms.

        Before any deployment claim, add an OS-level single-writer lock, rotating segments, a manifest
        with format migration, disk-space admission checks, backup/restore drills, production
        observability, and crash/fault tests on the target filesystem. Define whether acknowledgements
        require data and directory durability. The current system is one-process only and its bounded
        validators support `PARTIAL`, not `PRODUCTIONIZED`, status.
        """,
    )
    _write(
        workspace,
        "alternatives/memory.py",
        r'''
        from __future__ import annotations

        import threading


        class MemoryStore:
            def __init__(self) -> None:
                self._data: dict[bytes, bytes] = {}
                self._lock = threading.RLock()

            def set(self, key: bytes, value: bytes) -> None:
                with self._lock:
                    self._data[key] = value

            def get(self, key: bytes) -> bytes | None:
                with self._lock:
                    return self._data.get(key)

            def delete(self, key: bytes) -> bool:
                with self._lock:
                    return self._data.pop(key, None) is not None
        ''',
    )
    _write(
        workspace,
        "alternatives/sqlite_store.py",
        r'''
        from __future__ import annotations

        import sqlite3
        import threading
        from pathlib import Path


        class SQLiteStore:
            def __init__(self, path: str | Path) -> None:
                self._connection = sqlite3.connect(path, check_same_thread=False)
                self._connection.execute("PRAGMA synchronous=FULL")
                self._connection.execute("CREATE TABLE IF NOT EXISTS kv(key BLOB PRIMARY KEY,value BLOB NOT NULL)")
                self._lock = threading.RLock()

            def set(self, key: bytes, value: bytes) -> None:
                with self._lock, self._connection:
                    self._connection.execute(
                        "INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, value),
                    )

            def get(self, key: bytes) -> bytes | None:
                with self._lock:
                    row = self._connection.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
                    return bytes(row[0]) if row else None

            def delete(self, key: bytes) -> bool:
                with self._lock, self._connection:
                    return self._connection.execute("DELETE FROM kv WHERE key=?", (key,)).rowcount == 1

            def close(self) -> None:
                with self._lock:
                    self._connection.close()
        ''',
    )
    _write(
        workspace,
        "alternatives/README.md",
        """
        # Architecture alternatives

        `memory.py` establishes the lowest-complexity semantics but has no recovery. `sqlite_store.py`
        delegates transactions, locking, indexing, and recovery to SQLite. Compare both with the
        append-log implementations using the same set/get/delete workload; do not infer superiority
        from a single smoke run. Useful follow-ups include a segmented log and an ordered B+ tree.
        """,
    )
    _write(
        workspace,
        "adversarial/fuzz/model_fuzz.py",
        r'''
        from __future__ import annotations

        import argparse
        import os
        import random
        import sys
        import tempfile
        from pathlib import Path

        ROOT = Path(__file__).resolve().parents[2]
        IMPLEMENTATIONS = {
            "reference": ROOT / "sealed/reference",
            "production": ROOT / "production/implementation",
        }
        implementation = os.environ.get("KVSTORE_IMPL", "reference")
        try:
            implementation_path = IMPLEMENTATIONS[implementation]
        except KeyError as error:
            raise SystemExit("KVSTORE_IMPL must be 'reference' or 'production'") from error
        sys.path.insert(0, str(implementation_path))
        from kvstore import KVStore


        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--operations", type=int, default=1000)
            parser.add_argument("--seed", type=int, default=20260830)
            args = parser.parse_args()
            randomizer = random.Random(args.seed)
            model: dict[bytes, bytes] = {}
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "fuzz.log"
                store = KVStore(path, sync=False)
                for step in range(args.operations):
                    key = f"key-{randomizer.randrange(40)}".encode()
                    choice = randomizer.randrange(5)
                    if choice < 3:
                        value = randomizer.randbytes(randomizer.randrange(0, 80))
                        store.set(key, value)
                        model[key] = value
                    elif choice == 3:
                        observed = store.delete(key)
                        expected = key in model
                        model.pop(key, None)
                        assert observed == expected
                    else:
                        assert store.get(key) == model.get(key)
                    if step and step % 137 == 0:
                        store.close()
                        store = KVStore(path, sync=False)
                        assert store.keys() == sorted(model)
                store.close()
                with KVStore(path) as reopened:
                    assert reopened.keys() == sorted(model)
                    for key, value in model.items():
                        assert reopened.get(key) == value
            print(
                f"model fuzz passed: implementation={implementation} "
                f"seed={args.seed} operations={args.operations}"
            )
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )
    _write(
        workspace,
        "adversarial/stress/thread_stress.py",
        r'''
        from __future__ import annotations

        import argparse
        import os
        import sys
        import tempfile
        import threading
        from pathlib import Path

        ROOT = Path(__file__).resolve().parents[2]
        IMPLEMENTATIONS = {
            "reference": ROOT / "sealed/reference",
            "production": ROOT / "production/implementation",
        }
        implementation = os.environ.get("KVSTORE_IMPL", "reference")
        try:
            implementation_path = IMPLEMENTATIONS[implementation]
        except KeyError as error:
            raise SystemExit("KVSTORE_IMPL must be 'reference' or 'production'") from error
        sys.path.insert(0, str(implementation_path))
        from kvstore import KVStore


        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--threads", type=int, default=8)
            parser.add_argument("--operations", type=int, default=200)
            args = parser.parse_args()
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "stress.log"
                with KVStore(path, sync=False) as store:
                    errors: list[BaseException] = []

                    def writer(worker: int) -> None:
                        try:
                            for item in range(args.operations):
                                store.set(f"{worker}:{item}".encode(), str(item).encode())
                        except BaseException as error:
                            errors.append(error)

                    threads = [threading.Thread(target=writer, args=(worker,)) for worker in range(args.threads)]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join()
                    if errors:
                        raise errors[0]
                    assert len(store.keys()) == args.threads * args.operations
                with KVStore(path) as reopened:
                    assert len(reopened.keys()) == args.threads * args.operations
            print(
                f"thread stress passed: implementation={implementation} "
                f"threads={args.threads} operations={args.operations}"
            )
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )
    _write(
        workspace,
        "adversarial/fault-injection/torn_tail.py",
        r'''
        from __future__ import annotations

        import os
        import sys
        import tempfile
        from pathlib import Path

        ROOT = Path(__file__).resolve().parents[2]
        IMPLEMENTATIONS = {
            "reference": ROOT / "sealed/reference",
            "production": ROOT / "production/implementation",
        }
        implementation = os.environ.get("KVSTORE_IMPL", "reference")
        try:
            implementation_path = IMPLEMENTATIONS[implementation]
        except KeyError as error:
            raise SystemExit("KVSTORE_IMPL must be 'reference' or 'production'") from error
        sys.path.insert(0, str(implementation_path))
        from kvstore import KVStore


        def main() -> int:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "fault.log"
                with KVStore(path) as store:
                    store.set(b"committed", b"survives")
                with path.open("ab") as stream:
                    stream.write(b'{"body":"torn tail without newline')
                with KVStore(path) as recovered:
                    assert recovered.get(b"committed") == b"survives"
                    recovered.set(b"after", b"recovery")
                # Compaction removes the ignored torn bytes before another append/reopen cycle.
                with KVStore(path) as recovered:
                    recovered.compact()
                with KVStore(path) as final:
                    assert final.get(b"committed") == b"survives"
                    assert final.get(b"after") == b"recovery"
            print(
                "torn-tail recovery and post-recovery compaction passed: "
                f"implementation={implementation}"
            )
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )
    _write(
        workspace,
        "adversarial/README.md",
        """
        # Adversarial validation

        Select the target explicitly with `KVSTORE_IMPL=reference` or
        `KVSTORE_IMPL=production`; the latter name selects the instrumented teaching variant at its
        stable archive path and does not imply production readiness.

        The model fuzzer uses a fixed seed and compares every operation with a Python dictionary. The
        stress test gives each thread disjoint keys so the final state is deterministic. Fault injection
        appends a torn envelope and checks both recovery and a later compaction. These are bounded smoke
        workloads; increase counts and add filesystem/process crash injection for deeper campaigns.
        """,
    )
    _write(
        workspace,
        "benchmarks/benchmark.py",
        r'''
        from __future__ import annotations

        import argparse
        import importlib.util
        import json
        import platform
        import sys
        import tempfile
        import time
        from pathlib import Path
        from types import ModuleType


        ROOT = Path(__file__).resolve().parents[1]


        def load(name: str, path: Path) -> ModuleType:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"cannot import {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            return module


        def run_store(store_type: type, path: Path, operations: int) -> dict[str, float | int]:
            start = time.perf_counter_ns()
            store = store_type(path, sync=False)
            opened = time.perf_counter_ns()
            for item in range(operations):
                store.set(f"key-{item}".encode(), b"x" * 100)
            written = time.perf_counter_ns()
            for item in range(operations):
                assert store.get(f"key-{item}".encode()) == b"x" * 100
            read = time.perf_counter_ns()
            store.close()
            return {
                "operations": operations,
                "open_ns": opened - start,
                "write_total_ns": written - opened,
                "write_ns_per_op": (written - opened) / operations,
                "read_total_ns": read - written,
                "read_ns_per_op": (read - written) / operations,
                "file_bytes": path.stat().st_size,
            }


        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--operations", type=int, default=1000)
            parser.add_argument("--output", type=Path, required=True)
            args = parser.parse_args()
            if args.operations < 1:
                parser.error("operations must be positive")
            implementations = {
                "reference": ROOT / "sealed/reference/kvstore.py",
                "production": ROOT / "production/implementation/kvstore.py",
            }
            results: dict[str, object] = {
                "schema_version": 1,
                "hypothesis": "Basic instrumentation may add write overhead without changing format size.",
                "environment": {
                    "python": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "platform": platform.platform(),
                },
                "parameters": {"operations": args.operations, "value_bytes": 100, "sync": False},
                "raw_results": {},
            }
            with tempfile.TemporaryDirectory() as directory:
                for name, source in implementations.items():
                    module = load(f"benchmark_{name}", source)
                    results["raw_results"][name] = run_store(
                        module.KVStore, Path(directory) / f"{name}.log", args.operations
                    )
            raw = results["raw_results"]
            results["summary"] = {
                "production_to_reference_write_ratio": (
                    raw["production"]["write_ns_per_op"] / raw["reference"]["write_ns_per_op"]
                ),
                "note": "Smoke result from this execution; rerun and profile before generalizing.",
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(results["summary"], sort_keys=True))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )
    _write(
        workspace,
        "benchmarks/README.md",
        """
        # Benchmark protocol

        The smoke workload compares the reference with the instrumented teaching variant stored under
        the legacy `production/` path. It opens an empty store, inserts fixed-size unique values with
        per-append fsync disabled, then reads every value. The stated hypothesis is captured in the JSON
        before results. Raw nanosecond totals, aggregate per-operation values, file sizes,
        interpreter/platform, and parameters are written by the harness. Numbers are machine-specific,
        do not establish production readiness, and should not be treated as universal.
        """,
    )
    _write(
        workspace,
        "debugging/lost-delete/README.md",
        """
        # Debugging challenge: the returning key

        A deleted key is absent until the service restarts, then unexpectedly returns. Reproduce with
        `KVSTORE_IMPL=buggy python3 debugging/lost-delete/test_bug.py` from the archive root (a failing
        test is the expected reproduction). Investigate the on-disk records and replay path. Do not
        inspect `sealed/` until you have written a hypothesis, an experiment, and a regression test.
        """,
    )
    buggy = reference.replace(
        "else:\n                        self._data.pop(key, None)",
        "else:\n                        pass",
        1,
    )
    _write(workspace, "debugging/lost-delete/buggy/kvstore.py", buggy)
    _write(
        workspace,
        "debugging/lost-delete/test_bug.py",
        r'''
        from __future__ import annotations

        import os
        import sys
        import tempfile
        import unittest
        from pathlib import Path


        ROOT = Path(__file__).resolve().parents[2]
        IMPLEMENTATIONS = {
            "buggy": Path(__file__).resolve().parent / "buggy",
            "reference": ROOT / "sealed/reference",
            "production": ROOT / "production/implementation",
        }
        implementation = os.environ.get("KVSTORE_IMPL", "buggy")
        try:
            implementation_path = IMPLEMENTATIONS[implementation]
        except KeyError as error:
            raise SystemExit(
                "KVSTORE_IMPL must be 'buggy', 'reference', or 'production'"
            ) from error
        sys.path.insert(0, str(implementation_path))
        from kvstore import KVStore


        class LostDeleteRegression(unittest.TestCase):
            def test_delete_survives_restart(self) -> None:
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "store.log"
                    with KVStore(path) as store:
                        store.set(b"session", b"active")
                        store.delete(b"session")
                        self.assertIsNone(store.get(b"session"))
                    with KVStore(path) as reopened:
                        self.assertIsNone(reopened.get(b"session"))


        if __name__ == "__main__":
            unittest.main()
        ''',
    )
    _write(
        workspace,
        "debugging/lost-delete/sealed/root-cause.md",
        """
        # Root cause

        `_apply` handles set records but turns delete records into no-ops. Live deletion mutates the
        dictionary directly, hiding the defect until replay. There is exactly one intentional defect.
        """,
    )
    _write(
        workspace,
        "debugging/lost-delete/sealed/investigation.md",
        """
        # Investigation

        Confirm the log contains both set and delete envelopes, compare state before and after reopen,
        then trace the decoded operation list into `_apply`. The smallest regression is one set, one
        delete, close, reopen, and get. Avoid deleting the log or special-casing the test key.
        """,
    )
    rendered_buggy = dedent(buggy).lstrip("\n")
    rendered_reference = dedent(reference).lstrip("\n")
    repair_patch = "".join(
        unified_diff(
            rendered_buggy.splitlines(keepends=True),
            rendered_reference.splitlines(keepends=True),
            fromfile="a/debugging/lost-delete/buggy/kvstore.py",
            tofile="b/debugging/lost-delete/buggy/kvstore.py",
        )
    )
    _write(workspace, "debugging/lost-delete/sealed/patch.diff", repair_patch)
    _write(
        workspace,
        "debugging/lost-delete/sealed/regression-test/README.md",
        """
        # Regression test

        `debugging/lost-delete/test_bug.py` is the authoritative minimal regression. From the archive
        root, it fails with `KVSTORE_IMPL=buggy` and passes with `KVSTORE_IMPL=reference` (or the
        instrumented teaching variant selected by `KVSTORE_IMPL=production`). Apply the repair from
        the archive root with `patch -p1 < debugging/lost-delete/sealed/patch.diff`, then rerun the
        buggy target to verify the patch.
        """,
    )
    _write(
        workspace,
        "review_exercises/cache-compaction/README.md",
        """
        # PR review: cache reads and compact in the background

        Review `PR.patch` as if it targeted a production branch. Write findings in `REVIEW.md` with
        severity, concrete failure scenario, and suggested validation. The patch is plausible but not
        applied to either implementation. Reveal the expected review only after submitting yours.
        """,
    )
    _write(
        workspace,
        "review_exercises/cache-compaction/PR.patch",
        """
        Subject: improve read latency with cache and background compaction

        + self.cache = {}
        + self.compactor = Thread(target=self._compact_forever)
        + self.compactor.start()

          def get(self, key):
        +     if key in self.cache:
        +         return self.cache[key]
              with self._lock:
        -         return self._data.get(key)
        +         value = self._data.get(key)
        +         self.cache[key] = value
        +         return value

          def delete(self, key):
              with self._lock:
                  ...
        +     # cache invalidation will be added later

          def _compact_forever(self):
              while True:
                  sleep(60)
                  self.compact()
        """,
    )
    _write(
        workspace,
        "review_exercises/cache-compaction/REVIEW.md",
        """
        # Your review

        ## Blocking findings

        ## Non-blocking findings

        ## Tests and measurements requested
        """,
    )
    _write(
        workspace,
        "review_exercises/cache-compaction/sealed/EXPECTED_REVIEW.md",
        """
        # Expected review

        Blocking: reads and cache writes occur outside the store lock, so the dictionary races with
        invalidation; delete never invalidates and can return stale authorization/session-like data.
        Blocking: the non-daemon infinite thread has no cancellation or join, preventing graceful
        shutdown and potentially calling compact after close. Design concern: unbounded cache memory
        and negative-result caching lack policy. Request deterministic stale-read, close/shutdown,
        compaction overlap, and memory-bound tests plus workload measurements.
        """,
    )

    validators: list[dict[str, Any]] = [
        {
            "type": "required_paths",
            "name": "challenge-pack-layout",
            "paths": [
                "README.md",
                "MANIFEST.yaml",
                "REQUIREMENTS.md",
                "CONCEPTS.md",
                "DESIGN_QUESTIONS.md",
                "PROVENANCE.json",
                "starter/kvstore.py",
                "public_tests/test_contract.py",
                "environment/README.md",
                "scripts/run_all.py",
                "sealed/reference/kvstore.py",
                "sealed/reference_tests/test_recovery.py",
                "sealed/DESIGN.md",
                "sealed/TRADEOFFS.md",
                "sealed/REVIEW.md",
                "alternatives/memory.py",
                "alternatives/sqlite_store.py",
                "production/implementation/kvstore.py",
                "production/PRODUCTIONIZATION.md",
                "adversarial/fuzz/model_fuzz.py",
                "adversarial/stress/thread_stress.py",
                "adversarial/fault-injection/torn_tail.py",
                "benchmarks/benchmark.py",
                "debugging/lost-delete/buggy/kvstore.py",
                "debugging/lost-delete/test_bug.py",
                "debugging/lost-delete/sealed/patch.diff",
                "debugging/lost-delete/sealed/root-cause.md",
                "review_exercises/cache-compaction/PR.patch",
                "review_exercises/cache-compaction/sealed/EXPECTED_REVIEW.md",
            ],
        },
        {
            "type": "json_fields",
            "name": "project-provenance-schema",
            "path": "PROVENANCE.json",
            "required": ["schema_version", "source", "generated_material"],
        },
        {
            "type": "command",
            "name": "project-python-syntax",
            "argv": ["python3", "environment/check_python.py"],
            "claims": ["BUILDS"],
            "timeout_seconds": 30,
        },
        {
            "type": "command",
            "name": "reference-public-tests",
            "argv": ["python3", "-m", "unittest", "discover", "-s", "public_tests", "-v"],
            "env": {"PYTHONPATH": "sealed/reference"},
            "claims": ["TESTED"],
            "timeout_seconds": 60,
        },
        {
            "type": "command",
            "name": "reference-hidden-tests",
            "argv": ["python3", "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"],
            "env": {"PYTHONPATH": "sealed/reference"},
            "claims": ["TESTED"],
            "timeout_seconds": 60,
        },
        {
            "type": "command",
            "name": "production-public-tests",
            "argv": ["python3", "-m", "unittest", "discover", "-s", "public_tests", "-v"],
            "env": {"PYTHONPATH": "production/implementation"},
            "claims": ["TESTED"],
            "timeout_seconds": 60,
        },
        {
            "type": "command",
            "name": "production-hidden-tests",
            "argv": ["python3", "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"],
            "env": {"PYTHONPATH": "production/implementation"},
            "claims": ["TESTED", "PARTIAL"],
            "timeout_seconds": 60,
        },
        {
            "type": "command",
            "name": "reference-model-fuzz",
            "argv": ["python3", "adversarial/fuzz/model_fuzz.py", "--operations", "600"],
            "env": {"KVSTORE_IMPL": "reference"},
            "claims": ["FUZZED"],
            "timeout_seconds": 60,
        },
        {
            "type": "command",
            "name": "production-model-fuzz",
            "argv": ["python3", "adversarial/fuzz/model_fuzz.py", "--operations", "600"],
            "env": {"KVSTORE_IMPL": "production"},
            "claims": ["FUZZED"],
            "timeout_seconds": 60,
        },
        {
            "type": "command",
            "name": "production-thread-stress",
            "argv": ["python3", "adversarial/stress/thread_stress.py", "--threads", "6", "--operations", "80"],
            "env": {"KVSTORE_IMPL": "production"},
            "claims": ["TESTED"],
            "timeout_seconds": 60,
        },
        {
            "type": "command",
            "name": "production-torn-tail-fault",
            "argv": ["python3", "adversarial/fault-injection/torn_tail.py"],
            "env": {"KVSTORE_IMPL": "production"},
            "claims": ["TESTED"],
            "timeout_seconds": 60,
        },
        {
            "type": "command",
            "name": "debugging-bug-reproduces",
            "argv": ["python3", "debugging/lost-delete/test_bug.py"],
            "expected_exit": 1,
            "timeout_seconds": 30,
        },
        {
            "type": "command",
            "name": "debugging-reference-regression",
            "argv": ["python3", "debugging/lost-delete/test_bug.py"],
            "env": {"KVSTORE_IMPL": "reference"},
            "claims": ["TESTED"],
            "timeout_seconds": 30,
        },
        {
            "type": "command",
            "name": "measured-smoke-benchmark",
            "argv": [
                "python3",
                "benchmarks/benchmark.py",
                "--operations",
                "500",
                "--output",
                "benchmarks/results/smoke.json",
            ],
            "produces": ["benchmarks/results/smoke.json"],
            "claims": ["BENCHMARKED"],
            "timeout_seconds": 60,
        },
        {
            "type": "json_fields",
            "name": "benchmark-evidence-recorded",
            "path": "benchmarks/results/smoke.json",
            "required": ["schema_version", "hypothesis", "environment", "parameters", "raw_results", "summary"],
        },
        {"type": "tree_checksum", "name": "project-tree-checksum"},
    ]
    metadata = {
        "name": "Durable Bytes Persistent Key-Value Store",
        "artifact_revision": 2,
        "family": "storage-database",
        "type": "build",
        "languages": ["Python"],
        "concepts": ["append log", "recovery", "checksums", "compaction", "concurrency", "observability"],
        "difficulty": 7,
        "estimated_human_hours": 14,
        "production_relevance": 6,
        "debugging_value": 9,
        "architecture_value": 8,
        "provenance": provenance,
        "validation_targets": ["BUILDS", "TESTED", "FUZZED", "BENCHMARKED", "PARTIAL"],
        "deployment_status": "NOT_PRODUCTION_READY",
    }
    evidence = {
        "handler": "generate_project_slice",
        "project_id": "durable-bytes-kv",
        "artifact_revision": 2,
        "external_validation_required": True,
        "validator_count": len(validators),
        "reference_implementation": "sealed/reference/kvstore.py",
        "production_implementation": "production/implementation/kvstore.py",
        "deployment_status": "NOT_PRODUCTION_READY",
        **_workspace_summary(workspace),
    }
    return SliceResult(evidence, validators, "project_challenge_pack", "projects/database/durable-bytes-kv", metadata)
