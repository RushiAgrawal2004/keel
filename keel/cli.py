from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from .brief import make_brief
from .check import check_repo_result, write_baseline
from .config import default_config, load_config, save_config
from .contracts import approve_contract, load_proposals, reject_contract, save_proposals
from .adr import compile_adr_contracts
from .dashboard import build_dashboard
from .discover import discover_contracts
from .graph import load_graph
from .graph_quality import graph_quality
from .graphify_runner import ensure_graph
from .layers import assign_layers_and_zones
from .memory import export_events_jsonl, list_events, record_event
from .pr_comment import write_pr_comment
from .record import get_session
from .report import render_check_html, render_check_result, render_discover, render_explain, render_replay
from .serve import main as serve_main
from .webhook import send_governance_webhook

app = typer.Typer(no_args_is_help=True)


@app.command()
def build(path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    config = load_config(repo)
    graph = load_graph(ensure_graph(repo))
    assign_layers_and_zones(graph, config)
    out_dir = repo / "keel-out"
    out_dir.mkdir(exist_ok=True)
    layer_counts: dict[str, int] = {}
    for node in graph.nodes.values():
        layer_counts[node.layer] = layer_counts.get(node.layer, 0) + 1
    payload = {
        "nodes": [asdict(node) for node in graph.nodes.values()],
        "connections": [asdict(connection) for connection in graph.connections],
        "layers": layer_counts,
    }
    out = out_dir / "keel-graph.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(f"Built Keel graph: {len(graph.nodes)} nodes, {len(graph.connections)} connections")
    for layer, count in sorted(layer_counts.items()):
        typer.echo(f"  {layer}: {count}")
    typer.echo(f"Wrote {out}")


@app.command()
def init(
    path: Annotated[Path, typer.Argument()] = Path("."),
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing .keel.yml.")] = False,
) -> None:
    target = path.resolve()
    config_path = target / ".keel.yml"
    if config_path.exists() and not force:
        raise typer.BadParameter(".keel.yml already exists. Use --force to overwrite.")
    save_config(target, default_config(target.name))
    typer.echo(f"Wrote {config_path}")


@app.command()
def discover(
    path: Annotated[Path, typer.Argument()] = Path("."),
    write: Annotated[bool, typer.Option("--write", help="Write proposals to keel-out/proposals.yml.")] = False,
    include_low: Annotated[bool, typer.Option("--include-low", help="Include low-confidence proposals.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    repo = path.resolve()
    config = load_config(repo)
    graph = load_graph(ensure_graph(repo))
    assign_layers_and_zones(graph, config)
    proposals = discover_contracts(graph, config, include_low=include_low)
    if write:
        save_proposals(repo, proposals)
        record_event(repo, "proposals_written", {"count": len(proposals), "path": "keel-out/proposals.yml"})
    record_event(repo, "discover", {"proposal_count": len(proposals), "include_low": include_low, "wrote_file": write})
    if json_output:
        typer.echo(json.dumps([_proposal_payload(item) for item in proposals], indent=2))
    else:
        typer.echo(render_discover(proposals))


@app.command()
def proposals(
    path: Annotated[Path, typer.Argument()] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    items = load_proposals(path.resolve())
    if json_output:
        typer.echo(json.dumps(items, indent=2))
    elif not items:
        typer.echo("No stored proposals. Run `keel discover . --write` first.")
    else:
        for item in items:
            typer.echo(f"[{item.get('confidence')}] {item.get('id')} - {item.get('title')}")


@app.command()
def approve(contract_id: Annotated[str, typer.Argument()], path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    approved = approve_contract(repo, contract_id)
    record_event(repo, "contract_approved", {"contract_id": approved.id, "title": approved.title})
    typer.echo(f"Approved {approved.id}")


@app.command()
def reject(contract_id: Annotated[str, typer.Argument()], path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    reject_contract(repo, contract_id)
    record_event(repo, "contract_rejected", {"contract_id": contract_id})
    typer.echo(f"Rejected {contract_id}")


@app.command()
def check(
    path: Annotated[Path, typer.Argument()] = Path("."),
    changed: Annotated[list[str] | None, typer.Option("--changed", help="Only report violations involving these files.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
    html: Annotated[bool, typer.Option("--html", help="Write keel-out/check-report.html.")] = False,
) -> None:
    repo = path.resolve()
    result = check_repo_result(repo, changed_files=changed)
    if html:
        out_dir = repo / "keel-out"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "check-report.html").write_text(render_check_html(result), encoding="utf-8")
    record_event(
        repo,
        "check",
        {
            "blocking_count": len(result.blocking),
            "known_debt_count": len(result.known_debt),
            "changed_files": changed or [],
            "html": html,
        },
    )
    if json_output:
        typer.echo(json.dumps(_check_payload(result), indent=2))
    else:
        typer.echo(render_check_result(result))
    if result.blocking:
        raise typer.Exit(1)


@app.command()
def brief(path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    config = load_config(repo)
    graph = load_graph(ensure_graph(repo))
    assign_layers_and_zones(graph, config)
    typer.echo(make_brief(graph, config))


@app.command()
def replay(session_id: Annotated[int, typer.Argument()], path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    typer.echo(render_replay(get_session(path.resolve(), session_id)))


@app.command()
def serve() -> None:
    serve_main()


@app.command()
def baseline(path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    baseline_path = write_baseline(repo)
    record_event(repo, "baseline_written", {"path": str(baseline_path.relative_to(repo))})
    typer.echo(f"Wrote {baseline_path}")


@app.command()
def explain(
    contract_id: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    config = load_config(path.resolve())
    contract = next((item for item in config.approved_contracts if item.id == contract_id), None)
    if not contract:
        raise typer.BadParameter(f"Contract not found: {contract_id}")
    if json_output:
        typer.echo(json.dumps(asdict(contract), indent=2))
    else:
        typer.echo(render_explain(contract))


@app.command("export")
def export_data(
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[str, typer.Option("--format", help="Currently only json is supported.")] = "json",
) -> None:
    if format != "json":
        raise typer.BadParameter("Only --format json is supported")
    repo = path.resolve()
    config = load_config(repo)
    payload = {
        "config": {
            "version": config.version,
            "project": config.project,
            "graph": config.graph,
            "layers": config.layers,
            "zones": config.zones,
            "ignore": config.ignore,
            "approved_contracts": [asdict(item) for item in config.approved_contracts],
        },
        "proposals": load_proposals(repo),
        "events": list_events(repo, limit=100),
    }
    typer.echo(json.dumps(payload, indent=2))


@app.command()
def events(
    path: Annotated[Path, typer.Argument()] = Path("."),
    limit: Annotated[int, typer.Option("--limit", help="Maximum events to show.")] = 50,
) -> None:
    typer.echo(json.dumps(list_events(path.resolve(), limit=limit), indent=2))


@app.command("export-events")
def export_events(
    path: Annotated[Path, typer.Argument()] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", help="Output JSONL path.")] = None,
) -> None:
    repo = path.resolve()
    out = export_events_jsonl(repo, output)
    typer.echo(f"Wrote {out}")


@app.command("graph-quality")
def graph_quality_command(
    path: Annotated[Path, typer.Argument()] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    quality = graph_quality(path.resolve())
    record_event(path.resolve(), "graph_quality", {"score": quality["score"], "status": quality["status"]})
    if json_output:
        typer.echo(json.dumps(quality, indent=2))
        return
    typer.echo(f"Graph quality: {quality['score']}/100 ({quality['status']})")
    for warning in quality.get("warnings", []):
        typer.echo(f"- {warning}")


@app.command()
def dashboard(
    path: Annotated[Path, typer.Argument()] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", help="Dashboard HTML output path.")] = None,
) -> None:
    repo = path.resolve()
    out = build_dashboard(repo, output)
    record_event(repo, "dashboard_written", {"path": str(out)})
    typer.echo(f"Wrote {out}")


@app.command("pr-comment")
def pr_comment(
    path: Annotated[Path, typer.Argument()] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", help="PR comment markdown output path.")] = None,
) -> None:
    repo = path.resolve()
    out = write_pr_comment(repo, output)
    record_event(repo, "pr_comment_written", {"path": str(out)})
    typer.echo(f"Wrote {out}")


@app.command("adr-compile")
def adr_compile(
    path: Annotated[Path, typer.Argument()] = Path("."),
    write: Annotated[bool, typer.Option("--write", help="Write keel-out/adr-contracts.yml.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    repo = path.resolve()
    contracts = compile_adr_contracts(repo, write=write)
    record_event(repo, "adr_compile", {"contract_count": len(contracts), "wrote_file": write})
    if json_output:
        typer.echo(json.dumps(contracts, indent=2))
    elif write:
        typer.echo(f"Wrote {repo / 'keel-out' / 'adr-contracts.yml'}")
    else:
        typer.echo(f"Compiled {len(contracts)} ADR contract(s).")


@app.command("webhook")
def webhook(
    url: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    event_type: Annotated[str, typer.Option("--event-type", help="Webhook event type.")] = "keel.export",
) -> None:
    repo = path.resolve()
    response = send_governance_webhook(repo, url, event_type=event_type)
    record_event(repo, "webhook_sent", {"url": url, "status": response["status"]})
    typer.echo(json.dumps(response, indent=2))


def _proposal_payload(proposal) -> dict:
    payload = asdict(proposal)
    payload["rule"] = {proposal.rule.kind: proposal.rule.params}
    return payload


def _check_payload(result) -> dict:
    return {
        "status": "failed" if result.blocking else "passed",
        "blocking": [asdict(item) for item in result.blocking],
        "known_debt": [asdict(item) for item in result.known_debt],
    }


if __name__ == "__main__":
    app()
