from __future__ import annotations

from pathlib import Path
from typing import Any

from .graphify_runner import ensure_graph, graph_status
from .memory import list_events, list_memories, record_event, remember_project_context


def sync_project(repo_path: Path, *, update_graph: bool = True) -> dict[str, Any]:
    repo = repo_path.resolve()
    memory_ids = remember_project_context(repo)
    graph_path = None
    graph_error = None
    if update_graph:
        try:
            graph_path = ensure_graph(repo, update=True)
        except Exception as exc:
            graph_error = str(exc)
    payload = {
        "ok": graph_error is None,
        "repo": str(repo),
        "memory_count": len(memory_ids),
        "memory_ids": memory_ids,
        "graph_path": str(graph_path) if graph_path else None,
        "graph_error": graph_error,
        "graph": graph_status(repo),
    }
    record_event(repo, "project_synced", payload)
    return payload


def manager_status(repo_path: Path) -> dict[str, Any]:
    repo = repo_path.resolve()
    memories = list_memories(repo, limit=100000)
    events = list_events(repo, limit=10)
    latest_sync = next((event for event in events if event["type"] == "project_synced"), None)
    return {
        "repo": str(repo),
        "memory_count": len(memories),
        "recent_events": events,
        "latest_sync": latest_sync,
        "graph": graph_status(repo),
        "ready": bool(memories) and graph_status(repo)["exists"],
        "warnings": _status_warnings(memories, latest_sync, graph_status(repo)),
    }


def _status_warnings(memories: list[dict[str, Any]], latest_sync: dict[str, Any] | None, graph: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not memories:
        warnings.append("No memories stored yet. Run `keel sync .` or `keel remember --from-project --repo .`.")
    if latest_sync is None:
        warnings.append("No project sync event recorded yet. Run `keel sync .` at session start.")
    if not graph["exists"]:
        warnings.append("Graphify graph is missing. Run `keel sync .` with Graphify configured, or use `keel sync . --no-graph` for memory-only mode.")
    if graph.get("nodes", 0) == 0 and graph["exists"]:
        warnings.append("Graphify graph exists but has no nodes.")
    return warnings


def manager_instructions(repo_path: Path, client: str = "claude-code") -> str:
    repo = str(repo_path.resolve())
    return f"""# Keel Blackbox Manager

Use Keel for three things only:

1. Graphify graph access.
2. Blackbox recording of commands, failures, changes, and decisions.
3. MCP tools for agent access.

Repository:
`{repo}`

## Required Lifecycle

At session start:

```bash
keel session-start "{repo}" --label "{client}"
keel graph "{repo}"
```

During work, run shell commands through Keel so they are recorded:

```bash
keel run "<command>" --repo "{repo}" --session <SESSION_ID>
```

When making a decision or learning a project fact:

```bash
keel blackbox-note "<decision or finding>" --repo "{repo}" --session <SESSION_ID> --kind decision
```

Before finishing:

```bash
keel run "python -m pytest" --repo "{repo}" --session <SESSION_ID>
keel blackbox-report <SESSION_ID> "{repo}"
keel session-end <SESSION_ID> "{repo}"
```

## MCP Tools

Prefer MCP tools when available:

- `mcp_graph_build`
- `mcp_graph_status`
- `mcp_blackbox_start`
- `mcp_blackbox_run`
- `mcp_blackbox_note`
- `mcp_blackbox_sessions`
- `mcp_blackbox_report`
- `mcp_blackbox_end`

## Safety Rule

The blackbox is evidence. Current repo files, Graphify output, tests, and command results are source of truth. Record what happened; do not pretend Keel inferred facts it did not observe.
"""
