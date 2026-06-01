from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def record_event(repo_path: Path, event_type: str, payload: dict[str, Any]) -> int:
    db_path = _db_path(repo_path)
    db_path.parent.mkdir(exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            "insert into events (created_at, type, payload_json) values (?, ?, ?)",
            (_now(), event_type, json.dumps(payload, sort_keys=True)),
        )
        return int(cursor.lastrowid)


def list_events(repo_path: Path, limit: int = 50) -> list[dict[str, Any]]:
    db_path = _db_path(repo_path)
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "select id, created_at, type, payload_json from events order by id desc limit ?",
            (limit,),
        ).fetchall()
    return [_row_to_event(row) for row in rows]


def export_events_jsonl(repo_path: Path, output_path: Path | None = None) -> Path:
    out = output_path or (repo_path / "keel-out" / "events.jsonl")
    out.parent.mkdir(exist_ok=True)
    events = list(reversed(list_events(repo_path, limit=100000)))
    out.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    return out


def _db_path(repo_path: Path) -> Path:
    return repo_path / "keel-out" / "keel.sqlite3"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        create table if not exists events (
            id integer primary key autoincrement,
            created_at text not null,
            type text not null,
            payload_json text not null
        )
        """
    )
    conn.execute("create index if not exists idx_events_type on events(type)")


def _row_to_event(row: tuple[int, str, str, str]) -> dict[str, Any]:
    event_id, created_at, event_type, payload_json = row
    return {
        "id": event_id,
        "created_at": created_at,
        "type": event_type,
        "payload": json.loads(payload_json),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

