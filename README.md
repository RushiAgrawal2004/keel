# Keel

Keel is a blackbox recorder and Graphify launcher for coding agents.

It does only three things:

- builds and opens the Graphify project graph
- records agent sessions, commands, outputs, repo state, and decisions
- exposes the same graph and blackbox tools through MCP

## Install

```bash
pip install keel-arch
```

The package name is `keel-arch`; the installed command is `keel`.

## Graph

```bash
keel graph .
keel graph-status .
keel graph-open .
```

`keel graph` runs Graphify, then runs the cluster/report pass so these files are produced when possible:

- `graphify-out/graph.json`
- `graphify-out/graph.html`
- `graphify-out/GRAPH_REPORT.md`

If no API key is available, Keel creates a project `.env` template and adds `.env` to `.gitignore`.

## Blackbox

```bash
keel session-start . --label codex
keel run "python -m pytest" --repo . --session 1
keel blackbox-note "Decision: pytest is the verification gate." --repo . --session 1 --kind decision
keel sessions .
keel blackbox-report 1 .
keel session-end 1 .
```

Every `keel run` records:

- command
- exit code
- duration
- timeout state
- stdout/stderr tails
- stdout/stderr hashes
- git head and branch
- git status
- changed files
- diff stat
- Graphify graph status

Records are stored locally in `keel-out/keel.db`.

## MCP

```bash
keel mcp-config . --client codex
keel agent-setup . --client claude-code --write
keel serve --repo .
```

The MCP server exposes only:

- `mcp_graph_build`
- `mcp_graph_status`
- `mcp_blackbox_start`
- `mcp_blackbox_run`
- `mcp_blackbox_note`
- `mcp_blackbox_sessions`
- `mcp_blackbox_report`
- `mcp_blackbox_end`

## What Keel Is Not

Keel is not an architecture rule engine now.
Keel is not a dashboard generator now.
Keel is not a broad memory chatbot now.

Those older internals may still exist in the repository, but the public product surface is intentionally limited to Graphify, blackbox recording, CLI, and MCP.
