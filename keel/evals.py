from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .memory import recall, remember


EVAL_MEMORIES = [
    {
        "kind": "preference",
        "title": "Build Log Preference",
        "content": "Always update buildkeelupdates.md after changing Keel.",
        "tags": ["agent", "logs"],
        "queries": ["what file must be updated after build changes?", "what should agents do after changing keel?"],
    },
    {
        "kind": "test",
        "title": "Test Command",
        "content": "Run the project test suite with python -m pytest.",
        "tags": ["tests"],
        "queries": ["how do I test the project?", "which command runs the test suite?"],
    },
    {
        "kind": "decision",
        "title": "Package Name Decision",
        "content": "The installable package is keel-arch because the PyPI name keel is already taken.",
        "tags": ["package", "pypi"],
        "queries": ["why is the package called keel-arch?", "what happened with the keel pypi name?"],
    },
    {
        "kind": "architecture",
        "title": "Graphify And Keel Relationship",
        "content": "Graphify makes the project knowledge graph; Keel stores memory and checks architecture rules on top of that graph.",
        "tags": ["graphify", "architecture"],
        "queries": ["how does keel use graphify?", "what creates the project graph?"],
    },
    {
        "kind": "correction",
        "title": "Do Not Expose Secrets",
        "content": "Never print or commit API keys from .env; secrets must stay local.",
        "tags": ["security", "env"],
        "queries": ["what should happen with api keys?", "can the agent print .env secrets?"],
    },
]


def run_memory_eval(repo_path: Path) -> dict[str, Any]:
    with TemporaryDirectory(ignore_cleanup_errors=True) as raw_tmp:
        tmp = Path(raw_tmp)
        expected: dict[str, str] = {}
        cases: list[dict[str, str]] = []
        for item in EVAL_MEMORIES:
            memory_id = remember(
                tmp,
                item["content"],
                kind=item["kind"],
                title=item["title"],
                tags=item["tags"],
                source="eval",
                gate=True,
            )
            for query in item["queries"]:
                expected[query] = str(memory_id)
                cases.append({"query": query, "expected_id": str(memory_id), "expected_title": item["title"]})

        results: list[dict[str, Any]] = []
        top1 = 0
        hit_at_5 = 0
        reciprocal_rank_total = 0.0
        for case in cases:
            matches = recall(tmp, case["query"], limit=5, verify=True)
            ids = [str(match["id"]) for match in matches]
            rank = ids.index(case["expected_id"]) + 1 if case["expected_id"] in ids else 0
            if rank == 1:
                top1 += 1
            if rank:
                hit_at_5 += 1
                reciprocal_rank_total += 1 / rank
            results.append(
                {
                    **case,
                    "rank": rank,
                    "top_match": matches[0]["title"] if matches else None,
                    "top_score": matches[0]["score"] if matches else 0,
                }
            )

    total = len(cases)
    mrr = round(reciprocal_rank_total / total, 3) if total else 0.0
    score_percent = round((0.7 * (top1 / total) + 0.3 * (hit_at_5 / total)) * 100, 1) if total else 0.0
    return {
        "suite": "keel-memory-v1",
        "repo": str(repo_path),
        "cases": total,
        "top1": top1,
        "hit_at_5": hit_at_5,
        "mrr": mrr,
        "score_percent": score_percent,
        "results": results,
    }
