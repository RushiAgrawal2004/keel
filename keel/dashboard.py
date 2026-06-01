from __future__ import annotations

import json
from dataclasses import asdict
from html import escape
from pathlib import Path

from .check import check_repo_result
from .config import load_config
from .contracts import load_proposals
from .graph_quality import graph_quality
from .memory import list_events
from .report import render_check_html


def build_dashboard(repo_path: Path, output: Path | None = None) -> Path:
    out = output or (repo_path / "keel-out" / "dashboard.html")
    out.parent.mkdir(exist_ok=True)
    quality = _safe_graph_quality(repo_path)
    result = check_repo_result(repo_path)
    config = load_config(repo_path)
    proposals = load_proposals(repo_path)
    events = list_events(repo_path, limit=10)
    out.write_text(
        _render_dashboard(config, quality, result, proposals, events),
        encoding="utf-8",
    )
    return out


def _safe_graph_quality(repo_path: Path) -> dict:
    try:
        return graph_quality(repo_path)
    except Exception as exc:  # pragma: no cover - defensive for missing external graph state
        return {"score": 0, "status": "unavailable", "warnings": [str(exc)]}


def _render_dashboard(config, quality: dict, result, proposals: list[dict], events: list[dict]) -> str:
    payload = {
        "quality": quality,
        "blocking": [asdict(item) for item in result.blocking],
        "known_debt": [asdict(item) for item in result.known_debt],
        "proposals": proposals,
        "events": events,
    }
    return "\n".join(
        [
            "<!doctype html>",
            "<html><head><meta charset=\"utf-8\"><title>Keel Dashboard</title>",
            "<style>",
            "body{font-family:Inter,system-ui,sans-serif;margin:0;background:#f7f7f3;color:#1f2933}",
            "header{background:#102a43;color:white;padding:28px 40px}",
            "main{max-width:1180px;margin:0 auto;padding:28px 20px 48px}",
            ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}",
            ".card{background:white;border:1px solid #d9e2ec;border-radius:8px;padding:16px}",
            ".metric{font-size:34px;font-weight:700}.muted{color:#627d98}",
            "pre{white-space:pre-wrap;background:#102a43;color:#f0f4f8;padding:14px;border-radius:8px;overflow:auto}",
            "a{color:#0b69a3} h2{margin-top:30px}",
            "</style></head><body>",
            f"<header><h1>Keel Dashboard</h1><p>{escape(config.project.get('name', 'project'))}</p></header>",
            "<main>",
            "<section class=\"grid\">",
            _metric_card("Graph Quality", str(quality.get("score", 0)), quality.get("status", "")),
            _metric_card("Blocking", str(len(result.blocking)), "new regressions"),
            _metric_card("Known Debt", str(len(result.known_debt)), "baseline violations"),
            _metric_card("Proposals", str(len(proposals)), "stored candidates"),
            "</section>",
            "<h2>Graph Quality</h2>",
            _warnings(quality.get("warnings", [])),
            "<h2>Check Report</h2>",
            render_check_html(result).split("<body>", 1)[-1].rsplit("</body>", 1)[0],
            "<h2>Recent Events</h2>",
            "<pre>" + escape(json.dumps(events, indent=2)) + "</pre>",
            "<h2>Machine Data</h2>",
            "<pre>" + escape(json.dumps(payload, indent=2)) + "</pre>",
            "</main></body></html>",
        ]
    )


def _metric_card(title: str, value: str, subtitle: str) -> str:
    return f"<div class=\"card\"><div class=\"muted\">{escape(title)}</div><div class=\"metric\">{escape(value)}</div><div>{escape(str(subtitle))}</div></div>"


def _warnings(warnings: list[str]) -> str:
    if not warnings:
        return "<p>No graph quality warnings.</p>"
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in warnings) + "</ul>"

