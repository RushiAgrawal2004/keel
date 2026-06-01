from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def start_session(repo_path: Path) -> int:
    db = _db_path(repo_path)
    db.parent.mkdir(exist_ok=True)
    with sqlite3.connect(db) as conn:
        _ensure_schema(conn)
        cursor = conn.execute("insert into sessions (started_at) values (?)", (_now(),))
        return int(cursor.lastrowid)


def log_action(repo_path: Path, session_id: int, kind: str, payload: dict[str, Any]) -> int:
    db = _db_path(repo_path)
    db.parent.mkdir(exist_ok=True)
    with sqlite3.connect(db) as conn:
        _ensure_schema(conn)
        conn.execute("insert or ignore into sessions (id, started_at) values (?, ?)", (session_id, _now()))
        cursor = conn.execute(
            "insert into events (session_id, ts, kind, payload_json) values (?, ?, ?, ?)",
            (session_id, _now(), kind, json.dumps(payload, sort_keys=True)),
        )
        return int(cursor.lastrowid)


def get_session(repo_path: Path, session_id: int) -> list[dict[str, Any]]:
    db = _db_path(repo_path)
    if not db.exists():
        return []
    with sqlite3.connect(db) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "select id, ts, kind, payload_json from events where session_id = ? order by id",
            (session_id,),
        ).fetchall()
    return [
        {"id": row[0], "ts": row[1], "kind": row[2], "payload": json.loads(row[3])}
        for row in rows
    ]


def _db_path(repo_path: Path) -> Path:
    return repo_path / "keel-out" / "keel.db"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        create table if not exists sessions (
            id integer primary key autoincrement,
            started_at text not null
        )
        """
    )
    conn.execute(
        """
        create table if not exists events (
            id integer primary key autoincrement,
            session_id integer not null,
            ts text not null,
            kind text not null,
            payload_json text not null
        )
        """
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

