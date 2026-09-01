"""Proposed PR implementation. Review it; do not use it as a reference."""

import sqlite3
import threading


def claim_without_transaction(
    path: str, owner: str, selected: threading.Barrier
) -> int | None:
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    try:
        row = connection.execute(
            "SELECT message_id FROM messages WHERE state='READY' ORDER BY message_id LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        selected.wait(timeout=5)
        # The update neither shares the SELECT transaction nor checks prior state.
        connection.execute(
            """
            UPDATE messages SET state='CLAIMED',lease_owner=?,lease_token=?,
                lease_expires_at=999999
            WHERE message_id=?
            """,
            (owner, f"unsafe:{owner}", row[0]),
        )
        return int(row[0])
    except sqlite3.Error:
        # PR rationale: avoid waking callers during transient database incidents.
        return None
    finally:
        connection.close()
