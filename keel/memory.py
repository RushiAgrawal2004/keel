from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def remember(
    repo_path: Path,
    content: str,
    *,
    kind: str = "note",
    title: str | None = None,
    scope: str = "project",
    source: str = "manual",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    db_path = _db_path(repo_path)
    db_path.parent.mkdir(exist_ok=True)
    clean_tags = _clean_tags(tags or [])
    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            """
            insert into memories
              (created_at, updated_at, kind, title, content, scope, source, tags_json, metadata_json)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                _now(),
                kind,
                title or _title_from_content(content),
                content.strip(),
                scope,
                source,
                json.dumps(clean_tags, sort_keys=True),
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
        memory_id = int(cursor.lastrowid)
    record_event(
        repo_path,
        "memory_written",
        {"memory_id": memory_id, "kind": kind, "scope": scope, "source": source, "tags": clean_tags},
    )
    return memory_id


def remember_project_context(repo_path: Path) -> list[int]:
    ids: list[int] = []
    readme = repo_path / "README.md"
    if readme.exists():
        ids.append(
            remember(
                repo_path,
                _summarize_text(readme.read_text(encoding="utf-8"), max_chars=1200),
                kind="project",
                title="Project README Summary",
                source="README.md",
                tags=["project", "readme"],
            )
        )
    architecture = repo_path / "ARCHITECTURE.md"
    if architecture.exists():
        ids.append(
            remember(
                repo_path,
                _summarize_text(architecture.read_text(encoding="utf-8"), max_chars=1800),
                kind="architecture",
                title="Architecture Summary",
                source="ARCHITECTURE.md",
                tags=["architecture", "system"],
            )
        )
    graph_report = repo_path / "graphify-out" / "GRAPH_REPORT.md"
    if graph_report.exists():
        ids.append(
            remember(
                repo_path,
                _summarize_graph_report(graph_report.read_text(encoding="utf-8")),
                kind="graph",
                title="Graphify Graph Summary",
                source="graphify-out/GRAPH_REPORT.md",
                tags=["graphify", "graph", "architecture"],
            )
        )
    config = repo_path / ".keel.yml"
    if config.exists():
        ids.append(
            remember(
                repo_path,
                _summarize_text(config.read_text(encoding="utf-8"), max_chars=1200),
                kind="config",
                title="Keel Config Snapshot",
                source=".keel.yml",
                tags=["config", "rules"],
            )
        )
    return ids


def recall(
    repo_path: Path,
    query: str,
    *,
    limit: int = 5,
    kind: str | None = None,
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    memories = list_memories(repo_path, limit=100000, kind=kind)
    required_tags = set(_clean_tags(tags or []))
    query_terms = _terms(query)
    scored: list[tuple[float, dict[str, Any]]] = []
    for memory in memories:
        memory_tags = set(memory["tags"])
        if required_tags and not required_tags.issubset(memory_tags):
            continue
        score = _score_memory(memory, query_terms)
        if score > 0 or not query_terms:
            item = dict(memory)
            item["score"] = round(score, 3)
            scored.append((score, item))
    scored.sort(key=lambda item: (item[0], item[1]["id"]), reverse=True)
    return [item for _, item in scored[:limit]]


def list_memories(repo_path: Path, limit: int = 50, kind: str | None = None) -> list[dict[str, Any]]:
    db_path = _db_path(repo_path)
    if not db_path.exists():
        return []
    query = """
        select id, created_at, updated_at, kind, title, content, scope, source, tags_json, metadata_json
        from memories
    """
    params: list[Any] = []
    if kind:
        query += " where kind = ?"
        params.append(kind)
    query += " order by id desc limit ?"
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(query, params).fetchall()
    return [_row_to_memory(row) for row in rows]


def forget_memory(repo_path: Path, memory_id: int) -> bool:
    db_path = _db_path(repo_path)
    if not db_path.exists():
        return False
    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)
        cursor = conn.execute("delete from memories where id = ?", (memory_id,))
        deleted = cursor.rowcount > 0
    if deleted:
        record_event(repo_path, "memory_deleted", {"memory_id": memory_id})
    return deleted


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
    conn.execute(
        """
        create table if not exists memories (
            id integer primary key autoincrement,
            created_at text not null,
            updated_at text not null,
            kind text not null,
            title text not null,
            content text not null,
            scope text not null,
            source text not null,
            tags_json text not null,
            metadata_json text not null
        )
        """
    )
    conn.execute("create index if not exists idx_memories_kind on memories(kind)")
    conn.execute("create index if not exists idx_memories_source on memories(source)")


def _row_to_event(row: tuple[int, str, str, str]) -> dict[str, Any]:
    event_id, created_at, event_type, payload_json = row
    return {
        "id": event_id,
        "created_at": created_at,
        "type": event_type,
        "payload": json.loads(payload_json),
    }


def _row_to_memory(row: tuple[int, str, str, str, str, str, str, str, str, str]) -> dict[str, Any]:
    memory_id, created_at, updated_at, kind, title, content, scope, source, tags_json, metadata_json = row
    return {
        "id": memory_id,
        "created_at": created_at,
        "updated_at": updated_at,
        "kind": kind,
        "title": title,
        "content": content,
        "scope": scope,
        "source": source,
        "tags": json.loads(tags_json),
        "metadata": json.loads(metadata_json),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_tags(tags: list[str]) -> list[str]:
    return sorted({tag.strip().lower() for tag in tags if tag and tag.strip()})


def _title_from_content(content: str) -> str:
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "Untitled memory")
    return first_line[:80]


def _terms(text: str) -> list[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "what",
        "how",
        "does",
        "into",
        "your",
        "about",
        "when",
        "where",
        "why",
    }
    return [term for term in re.findall(r"[a-zA-Z0-9_./-]+", text.lower()) if len(term) > 2 and term not in stop]


def _score_memory(memory: dict[str, Any], query_terms: list[str]) -> float:
    if not query_terms:
        return 1.0
    title = memory["title"].lower()
    content = memory["content"].lower()
    source = memory["source"].lower()
    tags = " ".join(memory["tags"]).lower()
    score = 0.0
    for term in query_terms:
        if term in title:
            score += 4.0
        if term in tags:
            score += 3.0
        if term in source:
            score += 2.0
        count = content.count(term)
        if count:
            score += min(5.0, float(count))
    return score


def _summarize_text(text: str, *, max_chars: int) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    useful = [line for line in lines if line.strip()]
    summary = "\n".join(useful)
    if len(summary) <= max_chars:
        return summary
    return summary[: max_chars - 18].rstrip() + "\n... [truncated]"


def _summarize_graph_report(text: str) -> str:
    wanted = ("## Summary", "## God Nodes", "## Knowledge Gaps", "## Suggested Questions")
    lines = text.splitlines()
    selected: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("## "):
            capture = line.startswith(wanted)
        if capture:
            selected.append(line)
    return _summarize_text("\n".join(selected), max_chars=1800)
