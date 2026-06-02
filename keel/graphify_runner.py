from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import load_config


GRAPHIFY_API_KEYS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "MOONSHOT_API_KEY",
    "DEEPSEEK_API_KEY",
)


class GraphifyError(RuntimeError):
    """Raised when Keel cannot produce or read the Graphify graph."""


def ensure_graph(repo_path: Path, update: bool = False) -> Path:
    config = load_config(repo_path)
    graph_path = repo_path / config.graph.get("path", "graphify-out/graph.json")
    if graph_path.exists() and not update:
        return graph_path
    graphify = shutil.which("graphify")
    if not graphify:
        raise GraphifyError("Graphify is not installed or not on PATH. Install Graphify, or run `keel sync . --no-graph` for memory-only mode.")
    command = [graphify, str(repo_path)]
    if update:
        command.append("--update")
    env = _graphify_env(repo_path)
    result = _run_graphify(command, repo_path, env)
    if result.returncode != 0 and _is_api_key_failure(result.stderr or result.stdout):
        env_path = _ensure_env_template(repo_path)
        env = _graphify_env(repo_path)
        if _has_graphify_key(env):
            result = _run_graphify(command, repo_path, env)
        if result.returncode != 0:
            raise GraphifyError(_clean_graphify_failure(result.stderr.strip() or result.stdout.strip() or "Graphify failed", env_path))
    if result.returncode != 0:
        raise GraphifyError(result.stderr.strip() or result.stdout.strip() or "Graphify failed")
    if not graph_path.exists():
        raise GraphifyError(f"Graphify did not create {graph_path}")
    return graph_path


def _run_graphify(command: list[str], repo_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=repo_path, env=env, text=True, capture_output=True, check=False)


def _graphify_env(repo_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env_path = repo_path / ".env"
    if not env_path.exists():
        return env
    for key, value in _read_dotenv(env_path).items():
        if key in GRAPHIFY_API_KEYS and _looks_real_secret(value):
            env[key] = value
    return env


def _read_dotenv(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _has_graphify_key(env: dict[str, str]) -> bool:
    return any(_looks_real_secret(env.get(key, "")) for key in GRAPHIFY_API_KEYS)


def _looks_real_secret(value: str) -> bool:
    clean = value.strip()
    if not clean:
        return False
    lowered = clean.lower()
    placeholder_words = ("paste", "your_", "example", "optional", "replace", "<", ">")
    return not any(word in lowered for word in placeholder_words)


def _ensure_env_template(repo_path: Path) -> Path:
    env_path = repo_path / ".env"
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8", errors="ignore")
        if not any(key in existing for key in GRAPHIFY_API_KEYS):
            with env_path.open("a", encoding="utf-8") as handle:
                handle.write("\n" + _env_template())
    else:
        env_path.write_text(_env_template(), encoding="utf-8")
    _ensure_env_ignored(repo_path)
    return env_path


def _env_template() -> str:
    return "\n".join(
        [
            "# Keel / Graphify API keys",
            "# Paste ONE real key below. Leave the others blank.",
            "# Gemini is usually the cheapest first option for Graphify.",
            "GEMINI_API_KEY=paste_your_gemini_key_here",
            "GOOGLE_API_KEY=",
            "OPENAI_API_KEY=",
            "ANTHROPIC_API_KEY=",
            "MOONSHOT_API_KEY=",
            "DEEPSEEK_API_KEY=",
            "",
        ]
    )


def _ensure_env_ignored(repo_path: Path) -> None:
    gitignore = repo_path / ".gitignore"
    try:
        if gitignore.exists():
            lines = gitignore.read_text(encoding="utf-8").splitlines()
            if ".env" in {line.strip() for line in lines}:
                return
            with gitignore.open("a", encoding="utf-8") as handle:
                handle.write("\n.env\n")
            return
        gitignore.write_text(".env\n", encoding="utf-8")
    except OSError:
        return


def _clean_graphify_failure(message: str, env_path: Path | None = None) -> str:
    lower = message.lower()
    if _is_api_key_failure(lower):
        location = f" Keel created/updated `{env_path}`." if env_path else ""
        return (
            "Graphify needs an LLM API key before it can build the semantic graph. "
            "Set GEMINI_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, "
            "or another supported provider key in the project `.env`, then rerun the same Keel command. "
            "Keel automatically loads `.env` for Graphify commands."
            f"{location} "
            "For memory-only testing, run `keel sync . --no-graph`."
        )
    return message


def _is_api_key_failure(message: str) -> bool:
    lower = message.lower()
    return "no llm api key found" in lower or "api key" in lower


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
