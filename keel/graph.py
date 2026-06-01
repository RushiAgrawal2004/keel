from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Connection, ExternalImport, KeelGraph, Node


def load_graph(graph_path: Path) -> KeelGraph:
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    graph = KeelGraph()
    raw_nodes = {str(raw.get("id") or raw.get("key")): raw for raw in data.get("nodes", []) or []}
    for raw in data.get("nodes", []) or []:
        node = _parse_node(raw)
        if node and node.file_type == "code":
            graph.nodes[node.id] = node

    for raw in (data.get("links") or data.get("edges") or []):
        connection = _parse_connection(raw)
        if not connection or connection.relation == "semantically_similar_to":
            continue
        if connection.source in graph.nodes and connection.target in graph.nodes:
            graph.connections.append(connection)
        elif connection.source in graph.nodes:
            package = _external_package_name(connection.target, raw_nodes.get(connection.target))
            if not package:
                continue
            graph.external_imports.append(
                ExternalImport(
                    source_id=connection.source,
                    source_file=graph.nodes[connection.source].source_file,
                    package=package,
                    relation=connection.relation,
                )
            )
    return graph


def _parse_node(raw: dict[str, Any]) -> Node | None:
    try:
        node_id = str(raw.get("id") or raw.get("key"))
        source_file = str(raw.get("source_file") or "")
        file_type = str(raw.get("file_type") or "")
        if not node_id or not source_file:
            return None
        return Node(
            id=node_id,
            label=str(raw.get("label") or node_id),
            source_file=source_file,
            file_type=file_type,
        )
    except (TypeError, ValueError):
        return None


def _parse_connection(raw: dict[str, Any]) -> Connection | None:
    source = raw.get("source")
    target = raw.get("target")
    if source is None or target is None:
        return None
    return Connection(
        source=str(source),
        target=str(target),
        relation=str(raw.get("relation") or raw.get("type") or "references"),
        confidence=str(raw.get("confidence") or "EXTRACTED"),
    )


def _external_package_name(target: str, raw_node: dict[str, Any] | None) -> str | None:
    if raw_node:
        file_type = str(raw_node.get("file_type") or raw_node.get("type") or "").lower()
        if file_type in {"package", "external", "dependency"}:
            return str(raw_node.get("package") or raw_node.get("label") or target)
    if target and "/" not in target and "\\" not in target and "::" not in target:
        return target
    return None
