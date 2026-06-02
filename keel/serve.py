from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .brief import make_brief
from .check import check_repo
from .config import load_config
from .graph import load_graph
from .graphify_runner import ensure_graph
from .layers import assign_layers_and_zones
from .memory import context_pack
from .memory import recall as recall_memories
from .memory import remember as remember_memory
from .memory import remember_project_context
from .manager import sync_project
from .record import get_session, log_action, start_session
from .report import render_replay


def get_brief(repo_path: Path | None = None) -> str:
    repo = _repo(repo_path)
    config = load_config(repo)
    graph = load_graph(ensure_graph(repo))
    assign_layers_and_zones(graph, config)
    return make_brief(graph, config)


def check_change(files: list[str], repo_path: Path | None = None) -> list[str]:
    repo = _repo(repo_path)
    return [violation.message for violation in check_repo(repo, changed_files=files)]


def record_action(kind: str, payload: dict[str, Any], session_id: int | None = None, repo_path: Path | None = None) -> dict[str, Any]:
    repo = _repo(repo_path)
    sid = session_id or start_session(repo)
    event_id = log_action(repo, sid, kind, payload)
    return {"ok": True, "session_id": sid, "event_id": event_id}


def get_replay(session_id: int, repo_path: Path | None = None) -> str:
    return render_replay(get_session(_repo(repo_path), session_id))


def memory_search(query: str, limit: int = 5, repo_path: Path | None = None) -> list[dict[str, Any]]:
    return recall_memories(_repo(repo_path), query, limit=limit)


def memory_write(
    content: str,
    kind: str = "note",
    title: str | None = None,
    tags: list[str] | None = None,
    repo_path: Path | None = None,
) -> dict[str, Any]:
    memory_id = remember_memory(_repo(repo_path), content, kind=kind, title=title, tags=tags or [])
    return {"ok": True, "memory_id": memory_id}


def memory_bootstrap(repo_path: Path | None = None) -> dict[str, Any]:
    ids = remember_project_context(_repo(repo_path))
    return {"ok": True, "count": len(ids), "memory_ids": ids}


def memory_context(query: str, limit: int = 6, repo_path: Path | None = None) -> str:
    return context_pack(_repo(repo_path), query, limit=limit)


def project_sync(update_graph: bool = True, repo_path: Path | None = None) -> dict[str, Any]:
    return sync_project(_repo(repo_path), update_graph=update_graph)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Keel MCP stdio server")
    parser.add_argument("--repo", default=os.environ.get("KEEL_REPO_PATH", "."))
    args = parser.parse_args(argv)
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit("MCP SDK missing. Install with `python -m pip install mcp` or `pip install -e .[mcp]`.") from exc

    repo = Path(args.repo).resolve()
    server = FastMCP("keel")

    @server.tool()
    def mcp_get_brief() -> str:
        return get_brief(repo)

    @server.tool()
    def mcp_check_change(files: list[str]) -> list[str]:
        return check_change(files, repo)

    @server.tool()
    def mcp_record_action(kind: str, payload_json: str, session_id: int | None = None) -> str:
        payload = json.loads(payload_json)
        return json.dumps(record_action(kind, payload, session_id=session_id, repo_path=repo))

    @server.tool()
    def mcp_get_replay(session_id: int) -> str:
        return get_replay(session_id, repo)

    @server.tool()
    def mcp_memory_search(query: str, limit: int = 5) -> str:
        return json.dumps(memory_search(query, limit=limit, repo_path=repo), indent=2)

    @server.tool()
    def mcp_memory_write(content: str, kind: str = "note", title: str | None = None, tags_json: str = "[]") -> str:
        tags = json.loads(tags_json)
        return json.dumps(memory_write(content, kind=kind, title=title, tags=tags, repo_path=repo))

    @server.tool()
    def mcp_memory_bootstrap() -> str:
        return json.dumps(memory_bootstrap(repo), indent=2)

    @server.tool()
    def mcp_memory_context(query: str, limit: int = 6) -> str:
        return memory_context(query, limit=limit, repo_path=repo)

    @server.tool()
    def mcp_project_sync(update_graph: bool = True) -> str:
        return json.dumps(project_sync(update_graph=update_graph, repo_path=repo), indent=2)

    server.run()


def _repo(repo_path: Path | None) -> Path:
    return (repo_path or Path(os.environ.get("KEEL_REPO_PATH", "."))).resolve()


if __name__ == "__main__":
    main()
