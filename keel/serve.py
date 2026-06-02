from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .graphify_runner import build_graph, graph_status
from .record import blackbox_report, end_session, list_sessions, record_note, run_command, start_session


def graph_build(update: bool = True, cluster: bool = True, repo_path: Path | None = None) -> dict[str, Any]:
    return build_graph(_repo(repo_path), update=update, cluster=cluster)


def graph_state(repo_path: Path | None = None) -> dict[str, Any]:
    return graph_status(_repo(repo_path))


def blackbox_start(label: str | None = None, repo_path: Path | None = None) -> dict[str, Any]:
    repo = _repo(repo_path)
    session_id = start_session(repo, label=label)
    return {"ok": True, "session_id": session_id, "repo": str(repo), "label": label}


def blackbox_end(session_id: int, status: str = "completed", repo_path: Path | None = None) -> dict[str, Any]:
    return {"ok": True, **end_session(_repo(repo_path), session_id, status=status)}


def blackbox_run(
    command: str,
    session_id: int | None = None,
    timeout: int = 600,
    update_graph: bool = False,
    repo_path: Path | None = None,
) -> dict[str, Any]:
    return run_command(_repo(repo_path), command, session_id=session_id, timeout=timeout, update_graph=update_graph)


def blackbox_note(note: str, session_id: int | None = None, kind: str = "note", repo_path: Path | None = None) -> dict[str, Any]:
    return record_note(_repo(repo_path), note, session_id=session_id, kind=kind)


def blackbox_sessions(limit: int = 20, repo_path: Path | None = None) -> list[dict[str, Any]]:
    return list_sessions(_repo(repo_path), limit=limit)


def blackbox_report_text(session_id: int, repo_path: Path | None = None) -> str:
    return blackbox_report(_repo(repo_path), session_id)


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
    def mcp_graph_build(update: bool = True, cluster: bool = True) -> str:
        return json.dumps(graph_build(update=update, cluster=cluster, repo_path=repo), indent=2)

    @server.tool()
    def mcp_graph_status() -> str:
        return json.dumps(graph_state(repo), indent=2)

    @server.tool()
    def mcp_blackbox_start(label: str | None = None) -> str:
        return json.dumps(blackbox_start(label=label, repo_path=repo), indent=2)

    @server.tool()
    def mcp_blackbox_run(command: str, session_id: int | None = None, timeout: int = 600, update_graph: bool = False) -> str:
        return json.dumps(
            blackbox_run(command, session_id=session_id, timeout=timeout, update_graph=update_graph, repo_path=repo),
            indent=2,
        )

    @server.tool()
    def mcp_blackbox_note(note: str, session_id: int | None = None, kind: str = "note") -> str:
        return json.dumps(blackbox_note(note, session_id=session_id, kind=kind, repo_path=repo), indent=2)

    @server.tool()
    def mcp_blackbox_sessions(limit: int = 20) -> str:
        return json.dumps(blackbox_sessions(limit=limit, repo_path=repo), indent=2)

    @server.tool()
    def mcp_blackbox_report(session_id: int) -> str:
        return blackbox_report_text(session_id, repo)

    @server.tool()
    def mcp_blackbox_end(session_id: int, status: str = "completed") -> str:
        return json.dumps(blackbox_end(session_id, status=status, repo_path=repo), indent=2)

    server.run()


def _repo(repo_path: Path | None) -> Path:
    return (repo_path or Path(os.environ.get("KEEL_REPO_PATH", "."))).resolve()


if __name__ == "__main__":
    main()
