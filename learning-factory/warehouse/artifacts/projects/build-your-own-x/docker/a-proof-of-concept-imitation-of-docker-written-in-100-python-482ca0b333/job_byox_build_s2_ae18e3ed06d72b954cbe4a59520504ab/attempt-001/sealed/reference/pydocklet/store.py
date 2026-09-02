"""SQLite-backed image names and container lifecycle state."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Mapping, Sequence

from .errors import Conflict, InvalidName, InvalidProcess, InvalidTransition, NotFound
from .models import ContainerRecord, ContainerState, ExecutionResult, ImageRecord


_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _command_json(command: Sequence[str]) -> str:
    if isinstance(command, (str, bytes)):
        raise InvalidProcess("command must be a sequence of arguments")
    values = list(command)
    if not values or any(not isinstance(value, str) or "\0" in value for value in values):
        raise InvalidProcess("command must contain NUL-free string arguments")
    if not values[0]:
        raise InvalidProcess("executable argument must not be empty")
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def _env_json(env: Mapping[str, str]) -> str:
    if not isinstance(env, Mapping):
        raise InvalidProcess("environment must be a mapping")
    values = dict(env)
    for key, value in values.items():
        if not isinstance(key, str) or not _ENV_NAME.fullmatch(key):
            raise InvalidProcess(f"invalid environment name: {key!r}")
        if not isinstance(value, str) or "\0" in value:
            raise InvalidProcess(f"invalid environment value for {key}")
    return json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class StateStore:
    def __init__(self, root: Path) -> None:
        candidate = Path(root)
        if candidate.is_symlink():
            raise Conflict("runtime root must not be a symbolic link")
        candidate.mkdir(parents=True, exist_ok=True, mode=0o755)
        self.root = candidate.resolve(strict=True)
        self.db_path = self.root / "state.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS image_objects (
                    digest TEXT PRIMARY KEY,
                    rootfs TEXT NOT NULL,
                    layer_digests_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS image_tags (
                    name TEXT PRIMARY KEY,
                    digest TEXT NOT NULL REFERENCES image_objects(digest)
                );
                CREATE TABLE IF NOT EXISTS allowed_transitions (
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    PRIMARY KEY (from_state, to_state)
                );
                INSERT OR IGNORE INTO allowed_transitions(from_state, to_state)
                    VALUES ('CREATED', 'RUNNING'), ('RUNNING', 'EXITED');
                CREATE TABLE IF NOT EXISTS containers (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    container_id TEXT UNIQUE,
                    image_digest TEXT NOT NULL REFERENCES image_objects(digest),
                    state TEXT NOT NULL CHECK (state IN ('CREATED', 'RUNNING', 'EXITED')),
                    command_json TEXT NOT NULL,
                    env_json TEXT NOT NULL,
                    rootfs TEXT NOT NULL,
                    exit_code INTEGER,
                    stdout TEXT NOT NULL DEFAULT '',
                    stderr TEXT NOT NULL DEFAULT ''
                );
                CREATE TRIGGER IF NOT EXISTS enforce_container_initial_state
                BEFORE INSERT ON containers
                FOR EACH ROW WHEN NEW.state <> 'CREATED'
                BEGIN
                    SELECT RAISE(ABORT, 'container must begin in CREATED');
                END;
                CREATE TRIGGER IF NOT EXISTS enforce_container_transition
                BEFORE UPDATE OF state ON containers
                FOR EACH ROW
                WHEN OLD.state <> NEW.state AND NOT EXISTS (
                    SELECT 1 FROM allowed_transitions
                    WHERE from_state = OLD.state AND to_state = NEW.state
                )
                BEGIN
                    SELECT RAISE(ABORT, 'invalid container state transition');
                END;
                COMMIT;
                """
            )
        finally:
            connection.close()

    def _stored_path(self, path: Path) -> str:
        resolved = Path(path).resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise Conflict("object path must remain beneath the runtime root")
        return resolved.relative_to(self.root).as_posix()

    def _loaded_path(self, stored: str) -> Path:
        value = Path(stored)
        if value.is_absolute() or ".." in value.parts:
            raise Conflict("persisted object path is corrupt")
        resolved = (self.root / value).resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise Conflict("persisted object path escapes runtime root")
        return resolved

    @staticmethod
    def _validate_name(name: str) -> None:
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise InvalidName(f"invalid image name: {name!r}")

    @staticmethod
    def _validate_digest(digest: str) -> None:
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise Conflict("invalid content digest")

    def register_image(
        self, name: str, digest: str, rootfs: Path, layer_digests: Sequence[str]
    ) -> ImageRecord:
        self._validate_name(name)
        self._validate_digest(digest)
        layer_values = tuple(layer_digests)
        if not layer_values or any(
            not isinstance(value, str) or not _DIGEST.fullmatch(value) for value in layer_values
        ):
            raise Conflict("invalid layer digest list")
        stored_rootfs = self._stored_path(rootfs)
        stored_layers = json.dumps(layer_values, separators=(",", ":"))

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            object_row = connection.execute(
                "SELECT rootfs, layer_digests_json FROM image_objects WHERE digest = ?", (digest,)
            ).fetchone()
            if object_row is None:
                connection.execute(
                    "INSERT INTO image_objects(digest, rootfs, layer_digests_json) VALUES (?, ?, ?)",
                    (digest, stored_rootfs, stored_layers),
                )
            elif object_row["rootfs"] != stored_rootfs or object_row["layer_digests_json"] != stored_layers:
                raise Conflict("digest is already registered with different metadata")

            tag_row = connection.execute(
                "SELECT digest FROM image_tags WHERE name = ?", (name,)
            ).fetchone()
            if tag_row is not None and tag_row["digest"] != digest:
                raise Conflict(f"image tag is already bound to different content: {name}")
            if tag_row is None:
                connection.execute(
                    "INSERT INTO image_tags(name, digest) VALUES (?, ?)", (name, digest)
                )
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return ImageRecord(name, digest, Path(rootfs).resolve(strict=False), layer_values)

    def get_image(self, name: str) -> ImageRecord:
        self._validate_name(name)
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT t.name, o.digest, o.rootfs, o.layer_digests_json
                FROM image_tags AS t
                JOIN image_objects AS o ON o.digest = t.digest
                WHERE t.name = ?
                """,
                (name,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise NotFound(f"image not found: {name}")
        try:
            layers = json.loads(row["layer_digests_json"])
            if not isinstance(layers, list) or not layers or any(
                not isinstance(value, str) or not _DIGEST.fullmatch(value) for value in layers
            ):
                raise ValueError("invalid layers")
            if json.dumps(layers, separators=(",", ":")) != row["layer_digests_json"]:
                raise ValueError("non-canonical layers")
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise Conflict("persisted image metadata is corrupt") from exc
        return ImageRecord(row["name"], row["digest"], self._loaded_path(row["rootfs"]), tuple(layers))

    def create_container(
        self,
        image_digest: str,
        command: Sequence[str],
        env: Mapping[str, str],
        rootfs: Path,
    ) -> ContainerRecord:
        self._validate_digest(image_digest)
        command_data = _command_json(command)
        env_data = _env_json(env)
        stored_rootfs = self._stored_path(rootfs)

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                "SELECT 1 FROM image_objects WHERE digest = ?", (image_digest,)
            ).fetchone()
            if exists is None:
                raise NotFound(f"image digest not found: {image_digest}")
            cursor = connection.execute(
                """
                INSERT INTO containers(
                    container_id, image_digest, state, command_json, env_json, rootfs
                ) VALUES (NULL, ?, 'CREATED', ?, ?, ?)
                """,
                (image_digest, command_data, env_data, stored_rootfs),
            )
            container_id = f"c{cursor.lastrowid:06d}"
            connection.execute(
                "UPDATE containers SET container_id = ? WHERE seq = ?",
                (container_id, cursor.lastrowid),
            )
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return self.get_container(container_id)

    def _container_from_row(self, row: sqlite3.Row) -> ContainerRecord:
        try:
            command = json.loads(row["command_json"])
            env = json.loads(row["env_json"])
            state = ContainerState(row["state"])
            if not isinstance(command, list) or not command or any(
                not isinstance(value, str) for value in command
            ):
                raise ValueError("invalid command")
            if not isinstance(env, dict) or any(
                not isinstance(key, str) or not isinstance(value, str) for key, value in env.items()
            ):
                raise ValueError("invalid environment")
            exit_code = row["exit_code"]
            if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
                raise ValueError("invalid exit code")
            if _command_json(command) != row["command_json"] or _env_json(env) != row["env_json"]:
                raise ValueError("non-canonical or invalid JSON field")
        except (json.JSONDecodeError, ValueError, TypeError, InvalidProcess) as exc:
            raise Conflict("persisted container metadata is corrupt") from exc
        return ContainerRecord(
            container_id=row["container_id"],
            image_digest=row["image_digest"],
            state=state,
            command=tuple(command),
            env=dict(env),
            rootfs=self._loaded_path(row["rootfs"]),
            exit_code=exit_code,
            stdout=row["stdout"],
            stderr=row["stderr"],
        )

    def get_container(self, container_id: str) -> ContainerRecord:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM containers WHERE container_id = ?", (container_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise NotFound(f"container not found: {container_id}")
        return self._container_from_row(row)

    def list_containers(self) -> list[ContainerRecord]:
        connection = self._connect()
        try:
            rows = connection.execute("SELECT * FROM containers ORDER BY seq").fetchall()
        finally:
            connection.close()
        return [self._container_from_row(row) for row in rows]

    def claim_start(self, container_id: str) -> ContainerRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM containers WHERE container_id = ?", (container_id,)
            ).fetchone()
            if row is None:
                raise NotFound(f"container not found: {container_id}")
            if row["state"] != ContainerState.CREATED.value:
                raise InvalidTransition(
                    f"cannot start {container_id} from state {row['state']}"
                )
            cursor = connection.execute(
                "UPDATE containers SET state = 'RUNNING' WHERE container_id = ? AND state = 'CREATED'",
                (container_id,),
            )
            if cursor.rowcount != 1:
                raise InvalidTransition(f"container start was claimed concurrently: {container_id}")
            connection.commit()
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.rollback()
            raise InvalidTransition(str(exc)) from exc
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return self.get_container(container_id)

    def finish(self, container_id: str, result: ExecutionResult) -> ContainerRecord:
        if not isinstance(result.exit_code, int) or isinstance(result.exit_code, bool):
            raise InvalidProcess("exit code must be an integer")
        if not isinstance(result.stdout, str) or not isinstance(result.stderr, str):
            raise InvalidProcess("captured output must be text")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM containers WHERE container_id = ?", (container_id,)
            ).fetchone()
            if row is None:
                raise NotFound(f"container not found: {container_id}")
            if row["state"] != ContainerState.RUNNING.value:
                raise InvalidTransition(
                    f"cannot finish {container_id} from state {row['state']}"
                )
            connection.execute(
                """
                UPDATE containers
                SET state = 'EXITED', exit_code = ?, stdout = ?, stderr = ?
                WHERE container_id = ? AND state = 'RUNNING'
                """,
                (result.exit_code, result.stdout, result.stderr, container_id),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.rollback()
            raise InvalidTransition(str(exc)) from exc
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return self.get_container(container_id)
