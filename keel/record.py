from __future__ import annotations

import json
import subprocess
import sqlite3
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from .graphify_runner import graph_status


MAX_CAPTURE_CHARS = 12000


def start_session(repo_path: Path, label: str | None = None) -> int:
    db = _db_path(repo_path)
    db.parent.mkdir(exist_ok=True)
    with sqlite3.connect(db) as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            "insert into sessions (started_at, label, status, repo) values (?, ?, ?, ?)",
            (_now(), label, "running", str(repo_path.resolve())),
        )
        return int(cursor.lastrowid)


def end_session(repo_path: Path, session_id: int, status: str = "completed") -> dict[str, Any]:
    db = _db_path(repo_path)
    db.parent.mkdir(exist_ok=True)
    ended_at = _now()
    with sqlite3.connect(db) as conn:
        _ensure_schema(conn)
        conn.execute(
            "update sessions set ended_at = ?, status = ? where id = ?",
            (ended_at, status, session_id),
        )
    return {"session_id": session_id, "ended_at": ended_at, "status": status}


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


def list_sessions(repo_path: Path, limit: int = 20) -> list[dict[str, Any]]:
    db = _db_path(repo_path)
    if not db.exists():
        return []
    with sqlite3.connect(db) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            select s.id, s.started_at, s.ended_at, s.label, s.status, count(e.id)
            from sessions s
            left join events e on e.session_id = s.id
            group by s.id
            order by s.id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": row[0],
            "started_at": row[1],
            "ended_at": row[2],
            "label": row[3],
            "status": row[4],
            "event_count": row[5],
        }
        for row in rows
    ]


def run_command(
    repo_path: Path,
    command: str,
    *,
    session_id: int | None = None,
    timeout: int = 600,
    update_graph: bool = False,
) -> dict[str, Any]:
    repo = repo_path.resolve()
    sid = session_id or start_session(repo, label="keel run")
    before = capture_snapshot(repo)
    log_action(repo, sid, "command_started", {"command": command, "timeout": timeout, "before": before})
    started = datetime.now(timezone.utc)
    timed_out = False
    try:
        result = subprocess.run(
            command,
            cwd=repo,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        returncode = result.returncode
        stdout = result.stdout or ""
        stderr = result.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = _bytes_or_text(exc.stdout)
        stderr = _bytes_or_text(exc.stderr) + f"\nTimed out after {timeout}s."
    duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    after = capture_snapshot(repo, update_graph=update_graph)
    payload = {
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "stdout": _capture_text(stdout),
        "stderr": _capture_text(stderr),
        "before": before,
        "after": after,
    }
    event_id = log_action(repo, sid, "command_finished", payload)
    return {
        "ok": returncode == 0,
        "session_id": sid,
        "event_id": event_id,
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "changed_files": after.get("changed_files", []),
        "graph": after.get("graph", {}),
        "stdout_tail": payload["stdout"]["tail"],
        "stderr_tail": payload["stderr"]["tail"],
    }


def record_note(repo_path: Path, note: str, *, session_id: int | None = None, kind: str = "note") -> dict[str, Any]:
    repo = repo_path.resolve()
    sid = session_id or start_session(repo, label="keel note")
    event_id = log_action(repo, sid, kind, {"note": note, "snapshot": capture_snapshot(repo)})
    return {"ok": True, "session_id": sid, "event_id": event_id}


def capture_snapshot(repo_path: Path, *, update_graph: bool = False) -> dict[str, Any]:
    repo = repo_path.resolve()
    if update_graph:
        try:
            from .graphify_runner import ensure_graph

            ensure_graph(repo, update=True)
        except Exception as exc:
            graph = graph_status(repo)
            graph["update_error"] = str(exc)
        else:
            graph = graph_status(repo)
    else:
        graph = graph_status(repo)
    status = _git(repo, ["status", "--short"])
    return {
        "repo": str(repo),
        "time": _now(),
        "git_head": _git(repo, ["rev-parse", "--short", "HEAD"]).strip() or None,
        "git_branch": _git(repo, ["branch", "--show-current"]).strip() or None,
        "git_status": status,
        "changed_files": _changed_files(status),
        "diff_stat": _git(repo, ["diff", "--stat", "--", "."]),
        "graph": graph,
    }


def blackbox_report(repo_path: Path, session_id: int) -> str:
    events = get_session(repo_path, session_id)
    lines = [f"# Keel Blackbox Session {session_id}", ""]
    if not events:
        lines.append("No events recorded.")
        return "\n".join(lines)
    commands = [event for event in events if event["kind"] == "command_finished"]
    failures = [event for event in commands if event["payload"].get("returncode") != 0]
    lines.extend(
        [
            f"- Events: {len(events)}",
            f"- Commands: {len(commands)}",
            f"- Failed commands: {len(failures)}",
            "",
            "## Timeline",
            "",
        ]
    )
    for event in events:
        payload = event["payload"]
        if event["kind"] == "command_finished":
            lines.append(
                f"- {event['ts']} command `{payload.get('command')}` -> exit {payload.get('returncode')} "
                f"({payload.get('duration_ms')}ms)"
            )
            changed = payload.get("after", {}).get("changed_files", [])
            if changed:
                lines.append(f"  changed: {', '.join(changed[:8])}")
            stderr_tail = payload.get("stderr", {}).get("tail", "").strip()
            if stderr_tail:
                lines.append(f"  stderr: {stderr_tail[:500]}")
        elif event["kind"] == "command_started":
            lines.append(f"- {event['ts']} started `{payload.get('command')}`")
        else:
            note = payload.get("note") or json.dumps(payload, sort_keys=True)
            lines.append(f"- {event['ts']} {event['kind']}: {note}")
    return "\n".join(lines)


def _db_path(repo_path: Path) -> Path:
    return repo_path / "keel-out" / "keel.db"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        create table if not exists sessions (
            id integer primary key autoincrement,
            started_at text not null,
            ended_at text,
            label text,
            status text default 'running',
            repo text
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
    _ensure_columns(
        conn,
        "sessions",
        {
            "ended_at": "text",
            "label": "text",
            "status": "text default 'running'",
            "repo": "text",
        },
    )


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"pragma table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"alter table {table} add column {name} {definition}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(repo_path: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=repo_path, text=True, capture_output=True, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or result.stderr or "").strip()


def _changed_files(status: str) -> list[str]:
    files: list[str] = []
    for line in status.splitlines():
        item = line[3:].strip() if len(line) > 3 else line.strip()
        if " -> " in item:
            item = item.rsplit(" -> ", 1)[-1]
        if item:
            files.append(item)
    return files


def _capture_text(text: str) -> dict[str, Any]:
    return {
        "length": len(text),
        "sha256": sha256(text.encode("utf-8", errors="replace")).hexdigest(),
        "truncated": len(text) > MAX_CAPTURE_CHARS,
        "tail": text[-MAX_CAPTURE_CHARS:],
    }


def _bytes_or_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
