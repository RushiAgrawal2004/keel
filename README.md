# Keel

Keel finds the unwritten rules of your codebase and makes them executable.

Architecture regression tests for AI-generated code, powered by Graphify.

## Quickstart

```bash
pip install keel-arch
keel init .
keel discover . --write
keel proposals .
keel approve ui_never_touches_database .
keel check .
```

Keel reads `graphify-out/graph.json`, proposes deterministic architecture contracts from the graph, and enforces only contracts a human approved in `.keel.yml`.

## Commands

```bash
keel discover . --json
keel proposals .
keel approve ui_never_touches_database .
keel check . --json --html
keel baseline .
keel build .
keel brief .
keel replay SESSION_ID .
keel events .
keel export-events .
keel export . --format json
keel graph-quality . --json
keel dashboard .
keel pr-comment .
keel adr-compile . --write
```

`keel check` exits `1` only for new blocking violations. Violations captured by `keel baseline` are reported as known debt.

## Demo

```powershell
.\scripts\demo.ps1
```

The demo maps `demo-app`, discovers `UI must not access DATABASE directly`, approves it, and runs a clean architecture check.

## Agent And CI Integration

Keel exposes stable JSON for adapters:

- `keel discover . --json`
- `keel check . --json`
- `keel explain CONTRACT_ID . --json`
- `keel export . --format json`
- `keel export-events .`

The GitHub Actions workflow in `.github/workflows/keel.yml` runs tests and `keel check . --json --html`.

## Agent Briefing And MCP

```bash
keel build .
keel brief .
keel serve
```

`keel build` writes a layered graph snapshot to `keel-out/keel-graph.json`. `keel brief` prints a short markdown briefing for coding agents. `keel serve` starts a stdio MCP server exposing:

- `get_brief`
- `check_change`
- `record_action`
- `get_replay`

Set `KEEL_REPO_PATH` or pass `--repo` to point the server at a target repo.

## Plug-And-Play Setup

The PyPI distribution is `keel-arch` because the exact `keel` package name is already taken on PyPI. The installed command is still `keel`.

```bash
pip install keel-arch
keel quickstart /path/to/repo --preset generic
keel doctor /path/to/repo
keel mcp-config /path/to/repo --client codex
```

## Dashboard And Reports

```bash
keel dashboard .
keel graph-quality .
keel pr-comment .
```

These commands generate local HTML and Markdown artifacts under `keel-out/` for humans, pull requests, and CI artifacts.

## ADR Compiler

Add ADR files under `docs/adr/*.md` with YAML frontmatter:

```yaml
---
keel_contract:
  id: ui_never_touches_database
  title: UI must not access DATABASE directly
  rule:
    forbid_edge:
      from_layer: UI
      to_layer: DATABASE
      relation: "*"
---
```

Then run:

```bash
keel adr-compile . --write
```

## PyPI And Hosted Docs

The repo includes:

- `.github/workflows/publish.yml` for PyPI publishing from GitHub releases or manual workflow dispatch.
- `.github/workflows/docs.yml` for GitHub Pages deployment from `docs/`.

Publishing requires configuring PyPI trusted publishing or an equivalent repository secret.

## Limitations

- Keel depends on Graphify's graph quality.
- Keel proposes likely invariants, not universal truths.
- Human approval is required before enforcement.
- Layer and zone assignment are folder-based in v1.
- Keel is not a general code quality reviewer and does not replace tests.
