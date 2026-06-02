from __future__ import annotations

from pathlib import Path
from typing import Any

from .graphify_runner import ensure_graph
from .memory import record_event, remember_project_context


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
    }
    record_event(repo, "project_synced", payload)
    return payload


def manager_instructions(repo_path: Path, client: str = "claude-code") -> str:
    repo = str(repo_path.resolve())
    return f"""# Keel Project Manager

Use Keel as the project manager for this repository.

Repository:
`{repo}`

## Required Lifecycle

At session start:

```bash
keel sync "{repo}"
```

Before each coding task:

```bash
keel context "<task>" --repo "{repo}" --limit 8
```

After each coding task:

```bash
keel remember "<short summary of what changed, what was learned, and what to avoid next time>" --repo "{repo}" --kind session --tag agent --gate
```

Before finishing:

```bash
keel check "{repo}"
keel eval "{repo}"
```

## MCP Tools

Prefer MCP tools when available:

- `mcp_memory_bootstrap`
- `mcp_memory_context`
- `mcp_memory_search`
- `mcp_memory_write`
- `mcp_project_sync`
- `mcp_check_change`
- `mcp_record_action`
- `mcp_get_replay`

## Safety Rule

Memory guides the agent. Current repo files, tests, and Keel checks are the source of truth. If memory is missing, stale, or low confidence, inspect files directly and then store the new finding.
"""
