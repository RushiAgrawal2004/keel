from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import load_config


def ensure_graph(repo_path: Path, update: bool = False) -> Path:
    config = load_config(repo_path)
    graph_path = repo_path / config.graph.get("path", "graphify-out/graph.json")
    if graph_path.exists() and not update:
        return graph_path
    graphify = shutil.which("graphify")
    if not graphify:
        raise RuntimeError("Graphify is not installed or not on PATH")
    command = [graphify, str(repo_path)]
    if update:
        command.append("--update")
    result = subprocess.run(command, cwd=repo_path, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Graphify failed")
    if not graph_path.exists():
        raise RuntimeError(f"Graphify did not create {graph_path}")
    return graph_path


def graph_status(repo_path: Path) -> dict[str, Any]:
    config = load_config(repo_path)
    graph_path = repo_path / config.graph.get("path", "graphify-out/graph.json")
    graphify = shutil.which("graphify")
    status: dict[str, Any] = {
        "provider": config.graph.get("provider", "graphify"),
        "path": str(graph_path),
        "exists": graph_path.exists(),
        "graphify_cli": graphify,
        "nodes": 0,
        "edges": 0,
        "report_exists": (repo_path / "graphify-out" / "GRAPH_REPORT.md").exists(),
    }
    if graph_path.exists():
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            status["nodes"] = len(data.get("nodes", []) or [])
            status["edges"] = len((data.get("links") or data.get("edges") or []) or [])
            status["modified_at"] = graph_path.stat().st_mtime
        except (OSError, json.JSONDecodeError) as exc:
            status["error"] = str(exc)
    return status
