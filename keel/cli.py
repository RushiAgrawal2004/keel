from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .agent_setup import agent_setup as build_agent_setup
from .agent_setup import write_agent_setup
from .graphify_runner import GraphifyError, build_graph, graph_status
from .onboard import mcp_config, pretty_json
from .record import blackbox_report, end_session, list_sessions, record_note, run_command, start_session
from .serve import main as serve_main

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.command("graph")
def graph_command(
    path: Annotated[Path, typer.Argument(help="Repository path to graph.")] = Path("."),
    update: Annotated[bool, typer.Option("--update/--no-update", help="Rebuild changed graph data before clustering.")] = True,
    cluster: Annotated[bool, typer.Option("--cluster/--no-cluster", help="Generate Graphify report and HTML from graph.json.")] = True,
    open_html: Annotated[bool, typer.Option("--open", help="Open graphify-out/graph.html after generation.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    try:
        result = build_graph(path.resolve(), update=update, cluster=cluster, open_html=open_html)
    except GraphifyError as exc:
        _graphify_exit(exc)
    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return
    typer.echo(f"Graph: {result['graph_path']}")
    typer.echo(f"HTML: {result['html_path'] or 'not generated'}")
    typer.echo(f"Nodes: {result['status']['nodes']} Edges: {result['status']['edges']}")
    if result["cluster_error"]:
        typer.echo(f"Cluster warning: {result['cluster_error']}")


@app.command("graph-status")
def graph_status_command(
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    status = graph_status(path.resolve())
    if json_output:
        typer.echo(json.dumps(status, indent=2))
        return
    typer.echo(f"Graph provider: {status['provider']}")
    typer.echo(f"Graph path: {status['path']}")
    typer.echo(f"Exists: {status['exists']}")
    typer.echo(f"Nodes: {status['nodes']} Edges: {status['edges']}")


@app.command("graph-open")
def graph_open(
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
) -> None:
    html_path = path.resolve() / "graphify-out" / "graph.html"
    if not html_path.exists():
        raise typer.BadParameter("graphify-out/graph.html is missing. Run `keel graph .` first.")
    import webbrowser

    webbrowser.open(html_path.as_uri())
    typer.echo(f"Opened {html_path}")


@app.command("session-start")
def session_start(
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
    label: Annotated[str | None, typer.Option("--label", help="Human label for this blackbox session.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    repo = path.resolve()
    session_id = start_session(repo, label=label)
    payload = {"session_id": session_id, "repo": str(repo), "label": label, "status": "running"}
    typer.echo(json.dumps(payload, indent=2) if json_output else f"Started Keel blackbox session #{session_id}")


@app.command("session-end")
def session_end(
    session_id: Annotated[int, typer.Argument(help="Session id to close.")],
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
    status: Annotated[str, typer.Option("--status", help="Final session status.")] = "completed",
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    payload = end_session(path.resolve(), session_id, status=status)
    typer.echo(json.dumps(payload, indent=2) if json_output else f"Ended Keel blackbox session #{session_id} as {status}")


@app.command("sessions")
def sessions_command(
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
    limit: Annotated[int, typer.Option("--limit", help="Maximum sessions to show.")] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    sessions = list_sessions(path.resolve(), limit=limit)
    if json_output:
        typer.echo(json.dumps(sessions, indent=2))
        return
    if not sessions:
        typer.echo("No Keel blackbox sessions yet.")
        return
    for item in sessions:
        label = f" {item['label']}" if item.get("label") else ""
        typer.echo(f"#{item['id']} {item['status']}{label} events={item['event_count']} started={item['started_at']}")


@app.command("run")
def run_command_cli(
    command: Annotated[str, typer.Argument(help="Shell command to run and record.")],
    path: Annotated[Path, typer.Option("--repo", help="Repository path.")] = Path("."),
    session_id: Annotated[int | None, typer.Option("--session", help="Existing blackbox session id.")] = None,
    timeout: Annotated[int, typer.Option("--timeout", help="Command timeout in seconds.")] = 600,
    update_graph: Annotated[bool, typer.Option("--update-graph", help="Update Graphify after the command finishes.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    result = run_command(path.resolve(), command, session_id=session_id, timeout=timeout, update_graph=update_graph)
    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        typer.echo(f"Keel recorded command in session #{result['session_id']} event #{result['event_id']}")
        typer.echo(f"Exit: {result['returncode']} Duration: {result['duration_ms']}ms")
        if result["changed_files"]:
            typer.echo("Changed files:")
            for item in result["changed_files"][:20]:
                typer.echo(f"  {item}")
        if result["stdout_tail"].strip():
            typer.echo("stdout:")
            typer.echo(result["stdout_tail"])
        if result["stderr_tail"].strip():
            typer.echo("stderr:")
            typer.echo(result["stderr_tail"])
    if result["returncode"] != 0:
        raise typer.Exit(result["returncode"])


@app.command("blackbox-note")
def blackbox_note(
    note: Annotated[str, typer.Argument(help="Note or decision to record.")],
    path: Annotated[Path, typer.Option("--repo", help="Repository path.")] = Path("."),
    session_id: Annotated[int | None, typer.Option("--session", help="Existing blackbox session id.")] = None,
    kind: Annotated[str, typer.Option("--kind", help="Event kind for this note.")] = "note",
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    payload = record_note(path.resolve(), note, session_id=session_id, kind=kind)
    typer.echo(json.dumps(payload, indent=2) if json_output else f"Recorded {kind} in session #{payload['session_id']}")


@app.command("blackbox-report")
def blackbox_report_command(
    session_id: Annotated[int, typer.Argument(help="Session id to report.")],
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", help="Optional markdown output path.")] = None,
) -> None:
    report = blackbox_report(path.resolve(), session_id)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        typer.echo(f"Wrote {output}")
        return
    typer.echo(report)


@app.command("mcp-config")
def mcp_config_command(
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
    client: Annotated[str, typer.Option("--client", help="codex, claude, or cursor.")] = "codex",
) -> None:
    typer.echo(pretty_json(mcp_config(path.resolve(), client)))


@app.command("agent-setup")
def agent_setup_command(
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
    client: Annotated[str, typer.Option("--client", help="claude-code, codex, cursor, gemini, or generic.")] = "claude-code",
    write: Annotated[bool, typer.Option("--write", help="Write setup files under keel-out/agent-setup.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    repo = path.resolve()
    setup = write_agent_setup(repo, client) if write else build_agent_setup(repo, client)
    if json_output:
        typer.echo(json.dumps(setup, indent=2))
        return
    if write:
        typer.echo(f"Wrote {setup['setup_path']}")
        typer.echo(f"Wrote {setup['instructions_path']}")
        return
    typer.echo(setup["manager_instructions"])


@app.command()
def serve(path: Annotated[Path, typer.Option("--repo", help="Repository path to serve over MCP.")] = Path(".")) -> None:
    serve_main(["--repo", str(path.resolve())])


def _graphify_exit(exc: GraphifyError) -> None:
    typer.echo(f"Graphify not ready: {exc}", err=True)
    raise typer.Exit(2)


if __name__ == "__main__":
    app()
