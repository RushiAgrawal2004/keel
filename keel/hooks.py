from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_CLIENTS = {"codex", "claude", "cursor", "gemini", "generic"}


def hook_config(repo_path: Path, client: str = "codex") -> dict[str, Any]:
    normalized = client.lower()
    if normalized not in SUPPORTED_CLIENTS:
        normalized = "generic"
    repo = str(repo_path.resolve())
    return {
        "client": normalized,
        "repo": repo,
        "purpose": "Lifecycle hooks for automatic Keel memory capture and recall.",
        "hooks": {
            "session_start": {
                "description": "Bootstrap project memory at the start of an agent session.",
                "command": ["keel", "remember", "--from-project", "--repo", repo],
            },
            "before_task": {
                "description": "Fetch a memory context pack before coding.",
                "command_template": ["keel", "context", "{task}", "--repo", repo, "--limit", "8"],
            },
            "after_task": {
                "description": "Store a concise task summary after coding.",
                "command_template": [
                    "keel",
                    "remember",
                    "{summary}",
                    "--repo",
                    repo,
                    "--kind",
                    "session",
                    "--tag",
                    "agent",
                    "--gate",
                ],
            },
        },
        "mcp": {
            "command": "keel",
            "args": ["serve", "--repo", repo],
            "tools": ["mcp_memory_search", "mcp_memory_write", "mcp_memory_bootstrap", "mcp_check_change"],
        },
    }


def write_hook_config(repo_path: Path, client: str = "codex") -> dict[str, Any]:
    config = hook_config(repo_path, client)
    out = repo_path / "keel-out" / "hooks" / f"{config['client']}-hooks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return {**config, "path": str(out)}
