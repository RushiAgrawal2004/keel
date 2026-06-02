from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_CLIENTS = {"codex", "claude", "claude-code", "cursor", "gemini", "generic"}


def hook_config(repo_path: Path, client: str = "codex") -> dict[str, Any]:
    normalized = client.lower()
    if normalized not in SUPPORTED_CLIENTS:
        normalized = "generic"
    repo = str(repo_path.resolve())
    return {
        "client": normalized,
        "repo": repo,
        "purpose": "Lifecycle hooks for Keel blackbox recording, Graphify sync, and MCP access.",
        "hooks": {
            "session_start": {
                "description": "Start blackbox capture and sync the Graphify graph at the start of an agent session.",
                "commands": [["keel", "session-start", repo], ["keel", "sync", repo]],
            },
            "command": {
                "description": "Run shell commands through Keel so output, exit code, git state, and graph state are recorded.",
                "command_template": ["keel", "run", "{command}", "--repo", repo, "--session", "{session_id}"],
            },
            "decision": {
                "description": "Record decisions and findings into the blackbox timeline.",
                "command_template": ["keel", "blackbox-note", "{note}", "--repo", repo, "--session", "{session_id}", "--kind", "decision"],
            },
            "session_end": {
                "description": "Write a blackbox report and close the session.",
                "commands_template": [["keel", "blackbox-report", "{session_id}", repo], ["keel", "session-end", "{session_id}", repo]],
            },
        },
        "mcp": {
            "command": "keel",
            "args": ["serve", "--repo", repo],
            "tools": [
                "mcp_project_sync",
                "mcp_project_status",
                "mcp_graph_status",
                "mcp_blackbox_start",
                "mcp_blackbox_run",
                "mcp_blackbox_note",
                "mcp_blackbox_sessions",
                "mcp_blackbox_report",
                "mcp_blackbox_end",
                "mcp_check_change",
            ],
        },
    }


def write_hook_config(repo_path: Path, client: str = "codex") -> dict[str, Any]:
    config = hook_config(repo_path, client)
    out = repo_path / "keel-out" / "hooks" / f"{config['client']}-hooks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return {**config, "path": str(out)}
