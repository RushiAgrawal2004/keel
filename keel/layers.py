from __future__ import annotations

from pathlib import PurePosixPath

from .models import Config, KeelGraph


def assign_layers_and_zones(graph: KeelGraph, config: Config) -> None:
    for node in graph.nodes.values():
        path = _normalize(node.source_file)
        node.layer = _longest_prefix(path, config.layers) or "UNKNOWN"
        node.zones = [
            zone
            for zone, prefixes in config.zones.items()
            if any(_matches_prefix(path, prefix) for prefix in prefixes)
        ]


def _longest_prefix(path: str, mapping: dict[str, list[str]]) -> str | None:
    winner: tuple[int, str] | None = None
    for name, prefixes in mapping.items():
        for prefix in prefixes:
            normalized = _normalize(prefix)
            if _matches_prefix(path, normalized):
                score = len(PurePosixPath(normalized).parts)
                if winner is None or score > winner[0]:
                    winner = (score, name)
    return winner[1] if winner else None


def _matches_prefix(path: str, prefix: str) -> bool:
    path = _normalize(path)
    prefix = _normalize(prefix).rstrip("/")
    return path == prefix or path.startswith(prefix + "/")


def _normalize(path: str) -> str:
    return path.replace("\\", "/").strip("/")

