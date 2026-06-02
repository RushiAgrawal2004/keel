from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .hooks import hook_config
from .manager import manager_instructions
from .onboard import mcp_config


CLIENT_ALIASES = {
    "claude-code": "claude",
    "claude": "claude",
    "codex": "codex",
    "cursor": "cursor",
    "gemini": "generic",
    "generic": "generic",
}


def agent_setup(repo_path: Path, client: str = "claude-code") -> dict[str, Any]:
    normalized = client.lower()
    mcp_client = CLIENT_ALIASES.get(normalized, "generic")
    repo = repo_path.resolve()
    mcp = mcp_config(repo, mcp_client) if mcp_client in {"codex", "claude", "cursor"} else {
        "mcpServers": {"keel": {"command": "keel", "args": ["serve", "--repo", str(repo)]}}
    }
    return {
        "client": normalized,
        "repo": str(repo),
        "mcp": mcp,
        "hooks": hook_config(repo, normalized),
        "manager_instructions": manager_instructions(repo, normalized),
        "commands": {
            "session_start": ["keel", "session-start", str(repo), "--label", normalized],
            "graph": ["keel", "graph", str(repo)],
            "run_command": ["keel", "run", "<command>", "--repo", str(repo), "--session", "<session_id>"],
            "record_decision": ["keel", "blackbox-note", "<note>", "--repo", str(repo), "--session", "<session_id>", "--kind", "decision"],
            "session_report": ["keel", "blackbox-report", "<session_id>", str(repo)],
            "session_end": ["keel", "session-end", "<session_id>", str(repo)],
        },
    }


def write_agent_setup(repo_path: Path, client: str = "claude-code") -> dict[str, Any]:
    setup = agent_setup(repo_path, client)
    out_dir = repo_path / "keel-out" / "agent-setup"
    out_dir.mkdir(parents=True, exist_ok=True)
    setup_path = out_dir / f"{setup['client']}.json"
    instructions_path = out_dir / f"{setup['client']}-KEEL.md"
    setup_path.write_text(json.dumps(setup, indent=2), encoding="utf-8")
    instructions_path.write_text(setup["manager_instructions"], encoding="utf-8")
    return {**setup, "setup_path": str(setup_path), "instructions_path": str(instructions_path)}
