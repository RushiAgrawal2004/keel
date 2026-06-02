from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MEMORY_KINDS = {
    "project",
    "architecture",
    "decision",
    "preference",
    "correction",
    "bug",
    "test",
    "dependency",
    "session",
    "graph",
    "config",
    "note",
}

KIND_HINTS = {
    "architecture": {"architecture", "layer", "boundary", "database", "service", "ui", "graph", "contract", "rule"},
    "decision": {"decided", "because", "why", "reason", "chosen", "package", "name"},
    "preference": {"prefer", "always", "never", "user", "style", "tone"},
    "correction": {"wrong", "fix", "correction", "mistake", "do not", "don't"},
    "bug": {"bug", "failed", "failure", "error", "regression", "broken"},
    "test": {"test", "pytest", "verify", "suite", "pass", "fail"},
    "dependency": {"dependency", "package", "install", "pip", "npm", "version"},
    "session": {"session", "changed", "built", "implemented", "pushed", "commit"},
    "project": {"project", "repo", "command", "readme", "cli"},
}


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
    gate: bool = False,
) -> int:
    encoded = encode_memory(content, kind=kind, title=title, source=source, tags=tags or [])
    if gate and not encoded["should_store"]:
        record_event(repo_path, "memory_rejected", {"reason": encoded["reason"], "source": source})
        return 0
    kind = encoded["kind"]
    title = encoded["title"]
    tags = encoded["tags"]
    metadata = {**(metadata or {}), "encoding": encoded}
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
        _upsert_fts(conn, memory_id, title or _title_from_content(content), content.strip(), clean_tags)
    record_event(
        repo_path,
        "memory_written",
        {"memory_id": memory_id, "kind": kind, "scope": scope, "source": source, "tags": clean_tags},
    )
    return memory_id


def encode_memory(
    content: str,
    *,
    kind: str = "note",
    title: str | None = None,
    source: str = "manual",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    stripped = content.strip()
    terms = _terms(stripped)
    inferred_kind = kind if kind in MEMORY_KINDS and kind != "note" else _infer_kind(stripped, tags or [])
    inferred_tags = sorted(set(_clean_tags(tags or []) + [inferred_kind]))
    title_text = title or _title_from_content(stripped)
    has_signal = len(terms) >= 3 or inferred_kind in {"preference", "decision", "correction"}
    too_short = len(stripped) < 12
    duplicate_noise = stripped.lower() in {"ok", "okay", "thanks", "thank you", "yes", "no"}
    should_store = bool(stripped) and has_signal and not too_short and not duplicate_noise
    confidence = 0.85 if should_store and inferred_kind != "note" else 0.55 if should_store else 0.1
    reason = "stored: useful typed memory" if should_store else "rejected: low long-term signal"
    return {
        "should_store": should_store,
        "kind": inferred_kind,
        "title": title_text,
        "tags": inferred_tags,
        "confidence": confidence,
        "reason": reason,
        "source": source,
    }


def recall_plan(query: str) -> dict[str, Any]:
    terms = _terms(query)
    raw = query.lower()
    kind_scores: dict[str, int] = {}
    term_set = set(terms)
    for kind, hints in KIND_HINTS.items():
        overlap = len(term_set.intersection(hints))
        if overlap:
            kind_scores[kind] = overlap
    if "why" in raw or "reason" in raw or "because" in raw:
        kind_scores["decision"] = kind_scores.get("decision", 0) + 2
    if "test" in raw or "pytest" in raw:
        kind_scores["test"] = kind_scores.get("test", 0) + 2
    if "rule" in raw or "layer" in raw or "database" in raw or "architecture" in raw:
        kind_scores["architecture"] = kind_scores.get("architecture", 0) + 2
    if not kind_scores:
        kind_scores["project"] = 1
        kind_scores["note"] = 1
    ranked = sorted(kind_scores, key=kind_scores.get, reverse=True)
    return {
        "query": query,
        "terms": terms,
        "target_kinds": ranked[:3],
        "channels": ["fts", "keyword", "type", "recency", "verification"],
    }


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
    memory_architecture = repo_path / "MEMORY_ARCHITECTURE.md"
    if memory_architecture.exists():
        ids.append(
            remember(
                repo_path,
                _summarize_text(memory_architecture.read_text(encoding="utf-8"), max_chars=1800),
                kind="architecture",
                title="Memory Architecture Summary",
                source="MEMORY_ARCHITECTURE.md",
                tags=["memory", "architecture", "agent"],
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
    verify: bool = False,
) -> list[dict[str, Any]]:
    plan = recall_plan(query)
    memories = list_memories(repo_path, limit=100000, kind=kind)
    required_tags = set(_clean_tags(tags or []))
    query_terms = _terms(query)
    fts_scores = _fts_scores(repo_path, query_terms)
    scored: list[tuple[float, dict[str, Any]]] = []
    for memory in memories:
        memory_tags = set(memory["tags"])
        if required_tags and not required_tags.issubset(memory_tags):
            continue
        score, channels = _score_memory(memory, query_terms, plan, fts_scores.get(memory["id"], 0.0))
        if score > 0 or not query_terms:
            item = dict(memory)
            item["score"] = round(score, 3)
            item["channels"] = channels
            if verify:
                item["verification"] = verify_memory(repo_path, item)
            scored.append((score, item))
    scored.sort(key=lambda item: (item[0], item[1]["id"]), reverse=True)
    return [item for _, item in scored[:limit]]


def context_pack(repo_path: Path, query: str, *, limit: int = 6) -> str:
    matches = recall(repo_path, query, limit=limit, verify=True)
    if not matches:
        return "\n".join(
            [
                "# Keel Memory Context",
                "",
                f"Query: {query}",
                "",
                "Coverage: LOW",
                "",
                "No verified memories matched this query.",
                "",
                "Agent safety instructions:",
                "- Do not assume Keel has context for this task.",
                "- Inspect repo files directly.",
                "- Run targeted search with `rg`.",
                "- Check tests and project config.",
                "- Store the discovered result with `keel remember ... --kind session --gate`.",
            ]
        )
    best_score = max(float(item.get("score", 0)) for item in matches)
    stale_count = sum(1 for item in matches if item.get("verification", {}).get("status") == "stale")
    coverage = "HIGH" if best_score >= 8 and stale_count == 0 else "MEDIUM" if best_score >= 3 else "LOW"
    lines = [
        "# Keel Memory Context",
        "",
        f"Query: {query}",
        f"Coverage: {coverage}",
        "",
        "Agent safety instructions:",
        "- Treat current repo files, tests, and Keel checks as source of truth.",
        "- Verify stale or unverified memories before editing.",
        "- If important context is missing, inspect files directly and store what you learn after the task.",
        "",
    ]
    if stale_count:
        lines.extend([f"Warning: {stale_count} stale memory item(s) were retrieved.", ""])
    for item in matches:
        verification = item.get("verification", {})
        lines.extend(
            [
                f"## #{item['id']} {item['kind']} - {item['title']}",
                f"score: {item['score']} | source: {item['source']} | status: {verification.get('status', 'unknown')}",
                item["content"],
                "",
            ]
        )
    return "\n".join(lines).rstrip()


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
            _delete_fts(conn, memory_id)
    if deleted:
        record_event(repo_path, "memory_deleted", {"memory_id": memory_id})
    return deleted


def verify_memory(repo_path: Path, memory: dict[str, Any]) -> dict[str, Any]:
    source = str(memory.get("source") or "")
    content = str(memory.get("content") or "")
    evidence: list[str] = []
    stale: list[str] = []
    if source and source not in {"manual", "mcp", "agent"} and not source.startswith("http"):
        source_path = repo_path / source
        if source_path.exists():
            evidence.append(f"source exists: {source}")
        else:
            stale.append(f"source missing: {source}")
    for token in _path_mentions(content):
        candidate = repo_path / token
        if candidate.exists():
            evidence.append(f"path exists: {token}")
        elif "/" in token or "\\" in token:
            stale.append(f"path missing: {token}")
    if stale:
        status = "stale"
    elif evidence:
        status = "verified"
    else:
        status = "unverified"
    return {"status": status, "evidence": evidence, "stale": stale}


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
    try:
        conn.execute(
            """
            create virtual table if not exists memories_fts
            using fts5(title, content, tags, content='memories', content_rowid='id')
            """
        )
    except sqlite3.OperationalError:
        # Some Python builds omit FTS5; keyword/type scoring remains available.
        pass


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


def _infer_kind(content: str, tags: list[str]) -> str:
    haystack = " ".join([content.lower(), " ".join(tags).lower()])
    best = ("note", 0)
    for kind, hints in KIND_HINTS.items():
        score = sum(1 for hint in hints if hint in haystack)
        if score > best[1]:
            best = (kind, score)
    return best[0]


def _score_memory(
    memory: dict[str, Any],
    query_terms: list[str],
    plan: dict[str, Any],
    fts_score: float,
) -> tuple[float, list[str]]:
    if not query_terms:
        return 1.0, ["recency"]
    title = memory["title"].lower()
    content = memory["content"].lower()
    source = memory["source"].lower()
    tags = " ".join(memory["tags"]).lower()
    score = 0.0
    channels: list[str] = []
    if fts_score:
        score += fts_score
        channels.append("fts")
    for term in query_terms:
        if term in title:
            score += 4.0
            channels.append("keyword:title")
        if term in tags:
            score += 3.0
            channels.append("keyword:tag")
        if term in source:
            score += 2.0
            channels.append("keyword:source")
        count = content.count(term)
        if count:
            score += min(5.0, float(count))
            channels.append("keyword:content")
    if memory["kind"] in plan.get("target_kinds", []):
        score += 2.0
        channels.append("type")
    metadata = memory.get("metadata") or {}
    confidence = float((metadata.get("encoding") or {}).get("confidence") or 0.5)
    score += confidence
    channels.append("confidence")
    return score, sorted(set(channels))


def _fts_scores(repo_path: Path, query_terms: list[str]) -> dict[int, float]:
    if not query_terms:
        return {}
    db_path = _db_path(repo_path)
    if not db_path.exists():
        return {}
    match = " OR ".join(term.replace('"', "") for term in query_terms[:8])
    if not match:
        return {}
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_schema(conn)
            rows = conn.execute(
                "select rowid, rank from memories_fts where memories_fts match ? order by rank limit 50",
                (match,),
            ).fetchall()
    except sqlite3.OperationalError:
        return {}
    scores: dict[int, float] = {}
    for rowid, rank in rows:
        scores[int(rowid)] = max(0.1, min(8.0, abs(float(rank)) * 100.0))
    return scores


def _upsert_fts(conn: sqlite3.Connection, memory_id: int, title: str, content: str, tags: list[str]) -> None:
    try:
        conn.execute("delete from memories_fts where rowid = ?", (memory_id,))
        conn.execute(
            "insert into memories_fts(rowid, title, content, tags) values (?, ?, ?, ?)",
            (memory_id, title, content, " ".join(tags)),
        )
    except sqlite3.OperationalError:
        pass


def _delete_fts(conn: sqlite3.Connection, memory_id: int) -> None:
    try:
        conn.execute("delete from memories_fts where rowid = ?", (memory_id,))
    except sqlite3.OperationalError:
        pass


def _path_mentions(text: str) -> list[str]:
    return re.findall(r"[\w.-]+(?:/|\\)[\w./\\-]+", text)


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
