from __future__ import annotations

from .models import Config, KeelGraph


def make_brief(graph: KeelGraph, config: Config) -> str:
    lines = ["# Keel Architecture Brief", "", "## Layer Map"]
    if config.layers:
        for layer, prefixes in config.layers.items():
            lines.append(f"- **{layer}**: {', '.join(prefixes)}")
    else:
        lines.append("- No layers configured.")

    lines.extend(["", "## Rules"])
    if config.rules:
        for rule in config.rules:
            lines.append(f"- {rule.describe()}")
    elif config.approved_contracts:
        for contract in config.approved_contracts:
            if contract.status == "approved":
                lines.append(f"- {contract.title}")
    else:
        lines.append("- No approved rules configured.")

    layer_counts: dict[str, int] = {}
    for node in graph.nodes.values():
        layer_counts[node.layer] = layer_counts.get(node.layer, 0) + 1
    lines.extend(["", "## Current Graph"])
    for layer, count in sorted(layer_counts.items()):
        lines.append(f"- {layer}: {count} code node(s)")

    lines.extend(
        [
            "",
            "Follow these architectural rules. Route calls through the correct layer.",
        ]
    )
    return "\n".join(lines[:40])

