from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from .config import load_config, save_config
from .graphify_runner import ensure_graph
from .models import Config, Rule


PRESET_LAYERS = {
    "generic": {
        "UI": ["src/components", "src/pages", "app/components", "app/pages", "frontend/src"],
        "API": ["src/api", "app/api", "src/routes", "routes"],
        "SERVICE": ["src/services", "services", "app/services"],
        "DATABASE": ["src/db", "src/models", "src/repositories", "prisma"],
        "TEST": ["tests", "__tests__", "src/__tests__"],
    },
    "python": {
        "API": ["app/api", "src/api", "routes"],
        "SERVICE": ["app/services", "src/services", "services"],
        "DATABASE": ["app/db", "src/db", "models", "repositories"],
        "TEST": ["tests"],
    },
    "node": {
        "UI": ["src/components", "src/pages", "app"],
        "API": ["src/api", "app/api", "routes"],
        "SERVICE": ["src/services", "services"],
        "DATABASE": ["src/db", "prisma", "repositories"],
        "TEST": ["tests", "__tests__"],
    },
}


def config_for_preset(repo_path: Path, preset: str) -> Config:
    preset_key = preset.lower()
    if preset_key not in PRESET_LAYERS:
        raise ValueError(f"Unknown preset {preset!r}. Choose one of: {', '.join(sorted(PRESET_LAYERS))}")
    layers = PRESET_LAYERS[preset_key]
    rules: list[Rule] = [Rule(kind="no_cycles")]
    if "UI" in layers and "DATABASE" in layers:
        rules.insert(0, Rule(kind="forbid", from_layer="UI", to_layer="DATABASE"))
    return Config(
        version=1,
        project={"name": repo_path.name},
        graph={"provider": "graphify", "path": "graphify-out/graph.json"},
        layers=layers,
        zones={},
        ignore=["node_modules", "dist", "build", "coverage", "generated", ".venv"],
        approved_contracts=[],
        rules=rules,
    )


def write_preset_config(repo_path: Path, preset: str, force: bool = False) -> Path:
    path = repo_path / ".keel.yml"
    if path.exists() and not force:
        raise FileExistsError(".keel.yml already exists. Use --force to overwrite.")
    config = config_for_preset(repo_path, preset)
    save_config(repo_path, config)
    return path


def doctor(repo_path: Path) -> dict:
    config_path = repo_path / ".keel.yml"
    graph_path = repo_path / "graphify-out" / "graph.json"
    graphify_bin = shutil.which("graphify")
    checks = [
        {"name": "python", "ok": True, "detail": sys.version.split()[0]},
        {"name": "keel_config", "ok": config_path.exists(), "detail": str(config_path)},
        {"name": "graphify_cli", "ok": graphify_bin is not None, "detail": graphify_bin or "not found"},
        {"name": "graphify_graph", "ok": graph_path.exists(), "detail": str(graph_path)},
    ]
    if config_path.exists():
        try:
            config = load_config(repo_path)
            checks.append({"name": "layers_configured", "ok": bool(config.layers), "detail": f"{len(config.layers)} layer(s)"})
            checks.append(
                {
                    "name": "rules_configured",
                    "ok": bool(config.rules or config.approved_contracts),
                    "detail": f"{len(config.rules)} rule(s), {len(config.approved_contracts)} approved contract(s)",
                }
            )
        except Exception as exc:
            checks.append({"name": "config_valid", "ok": False, "detail": str(exc)})
    ok = all(item["ok"] for item in checks if item["name"] != "graphify_graph")
    return {"ok": ok, "checks": checks}


def mcp_config(repo_path: Path, client: str) -> dict:
    repo = str(repo_path.resolve())
    command = "keel"
    args = ["serve", "--repo", repo]
    if client == "codex":
        return {"mcp_servers": {"keel": {"command": command, "args": args}}}
    if client == "claude":
        return {"mcpServers": {"keel": {"command": command, "args": args}}}
    if client == "cursor":
        return {"mcpServers": {"keel": {"command": command, "args": args}}}
    raise ValueError("client must be one of: codex, claude, cursor")


def quickstart(repo_path: Path, preset: str, force: bool = False, skip_graph: bool = False) -> dict:
    config_path = write_preset_config(repo_path, preset, force=force) if force or not (repo_path / ".keel.yml").exists() else repo_path / ".keel.yml"
    graph_path = None
    graph_error = None
    if not skip_graph:
        try:
            graph_path = ensure_graph(repo_path)
        except Exception as exc:
            graph_error = str(exc)
    return {
        "config_path": str(config_path),
        "graph_path": str(graph_path) if graph_path else None,
        "graph_error": graph_error,
        "doctor": doctor(repo_path),
        "mcp": mcp_config(repo_path, "codex"),
        "next": [
            "keel build .",
            "keel brief .",
            "keel check .",
            "keel dashboard .",
            "keel serve --repo .",
        ],
    }


def pretty_json(data: dict) -> str:
    return json.dumps(data, indent=2)

