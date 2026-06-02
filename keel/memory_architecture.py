from __future__ import annotations

from pathlib import Path
from typing import Any


def memory_architecture() -> dict[str, Any]:
    return {
        "name": "Keel Memory Architecture",
        "version": "1.0",
        "principles": [
            "local_first",
            "agent_native",
            "typed_memory",
            "evidence_backed_recall",
            "retrieval_before_generation",
            "continuous_evaluation",
            "privacy_by_default",
        ],
        "layers": [
            {
                "name": "capture",
                "purpose": "Collect candidate memories from CLI, MCP tools, lifecycle hooks, project files, sessions, and Graphify output.",
                "components": ["keel remember", "mcp_memory_write", "keel hooks", "remember_project_context"],
            },
            {
                "name": "encoding_gate",
                "purpose": "Reject low-signal noise and classify useful facts before storage.",
                "components": ["encode_memory", "MEMORY_KINDS", "KIND_HINTS", "keel remember --gate"],
            },
            {
                "name": "durable_store",
                "purpose": "Persist typed memories, events, metadata, tags, and FTS index locally.",
                "components": ["keel-out/keel.sqlite3", "memories", "events", "memories_fts"],
            },
            {
                "name": "retrieval_planner",
                "purpose": "Classify query intent and select target memory types plus retrieval channels.",
                "components": ["recall_plan", "target_kinds", "channels"],
            },
            {
                "name": "hybrid_retrieval",
                "purpose": "Retrieve candidates through FTS, keyword match, tags, type priors, source match, confidence, and recency.",
                "components": ["recall", "_fts_scores", "_score_memory"],
            },
            {
                "name": "verification",
                "purpose": "Check file-backed memories against the repository and mark results verified, stale, or unverified.",
                "components": ["verify_memory", "keel recall --verify"],
            },
            {
                "name": "context_packaging",
                "purpose": "Render concise, source-aware memory bundles for agents before they edit code.",
                "components": ["context_pack", "keel context", "mcp_memory_context"],
            },
            {
                "name": "evaluation",
                "purpose": "Measure memory retrieval quality continuously instead of guessing.",
                "components": ["keel eval", "keel-out/memory-eval.json", "top1", "hit_at_5", "mrr"],
            },
            {
                "name": "automation",
                "purpose": "Connect memory bootstrap, recall, and capture into agent lifecycle hooks.",
                "components": ["keel hooks", "codex", "claude", "cursor", "gemini"],
            },
        ],
        "memory_types": [
            "project",
            "architecture",
            "decision",
            "preference",
            "correction",
            "bug",
            "test",
            "dependency",
            "session",
            "graph",
            "config",
            "note",
        ],
        "quality_controls": [
            "encoding_gate",
            "source_metadata",
            "tag_normalization",
            "repo_verification",
            "stale_memory_detection",
            "built_in_eval_suite",
            "event_audit_log",
        ],
        "future_layers": [
            "local_embedding_index",
            "neural_reranker",
            "memory_compaction",
            "contradiction_detection",
            "cross_repo_identity_memory",
            "benchmark_dataset_adapters",
        ],
    }


def render_memory_architecture() -> str:
    spec = memory_architecture()
    lines = [
        "# Keel Memory Architecture",
        "",
        "Keel is designed as an agent-native memory system for software projects. It stores durable local memory, retrieves task-relevant context, verifies facts against the repository, and measures retrieval quality with built-in evals.",
        "",
        "## Principles",
        "",
    ]
    lines.extend(f"- `{item}`" for item in spec["principles"])
    lines.extend(["", "## Layered System", ""])
    for layer in spec["layers"]:
        lines.extend(
            [
                f"### {layer['name']}",
                layer["purpose"],
                "",
                "Components:",
            ]
        )
        lines.extend(f"- `{component}`" for component in layer["components"])
        lines.append("")
    lines.extend(["## Memory Types", ""])
    lines.extend(f"- `{item}`" for item in spec["memory_types"])
    lines.extend(["", "## Quality Controls", ""])
    lines.extend(f"- `{item}`" for item in spec["quality_controls"])
    lines.extend(["", "## Future Industry Layers", ""])
    lines.extend(f"- `{item}`" for item in spec["future_layers"])
    lines.extend(
        [
            "",
            "## Target Architecture",
            "",
            "```text",
            "agent conversation / repo files / git / CI / Graphify",
            "        |",
            "        v",
            "capture layer",
            "        |",
            "        v",
            "encoding gate -> reject noise",
            "        |",
            "        v",
            "typed durable store + FTS index",
            "        |",
            "        v",
            "retrieval planner",
            "        |",
            "        v",
            "hybrid retrieval + reranking signals",
            "        |",
            "        v",
            "repo verification",
            "        |",
            "        v",
            "context pack for Codex / Claude / Cursor / Gemini",
            "        |",
            "        v",
            "eval feedback loop",
            "```",
            "",
            "## Current Implementation Status",
            "",
            "Implemented now: local SQLite memory, typed classification, encoding gate, FTS-backed retrieval when available, retrieval planner, verification, context packs, MCP memory tools, lifecycle hook configs, and built-in evals.",
            "",
            "Planned next: local embeddings, neural reranking, compaction, contradiction detection, public benchmark adapters, and cross-repo identity memory.",
        ]
    )
    return "\n".join(lines)


def write_memory_architecture(repo_path: Path) -> Path:
    out = repo_path / "keel-out" / "memory-architecture.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_memory_architecture(), encoding="utf-8")
    return out
