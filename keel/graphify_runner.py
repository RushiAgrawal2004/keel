from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

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

