# Keel Operations Guide

This guide explains how to use Keel, monitor it, test it, and keep developing it.

Keel is a local project manager for coding agents. It stores memory in SQLite, keeps project context, integrates with Graphify, exposes MCP tools, and gives agents safe context before they edit code.

## 1. What Keel Does

Keel sits beside Codex, Claude Code, Cursor, Gemini, or another coding agent.

```text
agent starts
  -> keel sync .
  -> Keel stores project memory and refreshes Graphify

agent receives task
  -> keel context "<task>"
  -> Keel returns safe memory context

agent finishes task
  -> keel remember "<summary>" --kind session --tag agent --gate
  -> Keel records what happened

next session
  -> Keel recalls previous project context
```

Keel is not the AI brain. The agent reasons. Keel stores, retrieves, verifies, checks, and reports.

## 2. Install Keel

From PyPI once published:

```bash
pip install keel-arch
```

From this repo during development:

```bash
python -m pip install -e ".[dev]"
```

Check the CLI:

```bash
keel --help
```

## 3. First-Time Setup In A Project

Run this inside the target repo:

```bash
keel init . --preset generic
keel doctor .
```

For a Node-style app:

```bash
keel init . --preset node
```

For a Python-style app:

```bash
keel init . --preset python
```

This creates `.keel.yml`, which tells Keel how to map folders into layers.

## 4. Build Or Refresh Project Context

Run:

```bash
keel sync .
```

This does two things:

- stores project memory from files like `README.md`, `ARCHITECTURE.md`, `MEMORY_ARCHITECTURE.md`, `.keel.yml`, and Graphify reports
- asks Graphify to update the project graph when available

If you do not want Graphify/API use:

```bash
keel sync . --no-graph
```

Use this when you only want SQLite memory refreshed.

## 5. Connect To Claude Code Or Another Agent

Generate setup files:

```bash
keel agent-setup . --client claude-code --write
```

Other clients:

```bash
keel agent-setup . --client codex --write
keel agent-setup . --client cursor --write
keel agent-setup . --client gemini --write
keel agent-setup . --client generic --write
```

Generated files appear in:

```text
keel-out/agent-setup/
```

Start the MCP server:

```bash
keel serve --repo .
```

The agent should use this lifecycle:

```text
session start:
  keel sync .

before each task:
  keel context "<task>" --repo . --limit 8

after each task:
  keel remember "<summary>" --repo . --kind session --tag agent --gate

before finishing:
  run tests
  keel check .
  keel eval .
```

## 6. Fetch Safe Context

Before coding, ask Keel for context:

```bash
keel context "fix failing dashboard test" --repo .
```

Keel returns:

- coverage label: `HIGH`, `MEDIUM`, or `LOW`
- safety instructions
- matching memories
- memory scores
- source files
- verification status

If context is weak, Keel tells the agent to inspect files directly.

You can inspect retrieval in detail:

```bash
keel recall "how do I run tests?" --repo . --verify --plan
```

## 7. Store Memory

Manual memory:

```bash
keel remember "Run tests with python -m pytest." --repo . --kind test --gate
```

Session memory:

```bash
keel remember "Fixed dashboard test by updating the service mock." --repo . --kind session --tag agent --gate
```

List memories:

```bash
keel memories --repo .
```

Delete bad memory:

```bash
keel forget MEMORY_ID --repo .
```

## 8. Monitor Keel

Check manager health:

```bash
keel manager-status .
keel manager-status . --json
```

This reports:

- memory count
- recent events
- latest sync event
- Graphify graph status
- warnings

Check Graphify health:

```bash
keel graph-status .
keel graph-status . --json
```

This reports:

- graph provider
- graph path
- whether graph exists
- Graphify CLI path
- node count
- edge count
- report status

Check recent events:

```bash
keel events .
```

Export event log:

```bash
keel export-events .
```

## 9. Architecture Rules

Discover candidate rules:

```bash
keel discover . --write
```

List proposals:

```bash
keel proposals .
```

Approve a rule:

```bash
keel approve CONTRACT_ID .
```

Run architecture check:

```bash
keel check .
```

Generate HTML check report:

```bash
keel check . --html
```

Create baseline for existing known debt:

```bash
keel baseline .
```

## 10. Dashboards And Reports

Build layered graph snapshot:

```bash
keel build .
```

Agent architecture brief:

```bash
keel brief .
```

Dashboard:

```bash
keel dashboard .
```

Graph quality:

```bash
keel graph-quality .
```

PR comment body:

```bash
keel pr-comment .
```

Memory architecture blueprint:

```bash
keel memory-architecture .
keel memory-architecture . --json
keel memory-architecture . --write
```

## 11. Test Keel As A User

Run the demo:

```powershell
.\scripts\demo.ps1
```

Basic manual test:

```bash
keel doctor .
keel sync . --no-graph
keel remember "Run tests with python -m pytest." --kind test --gate
keel context "how do I run tests?"
keel manager-status .
keel eval .
```

Graphify integration test:

```bash
keel sync .
keel graph-status .
```

Agent setup test:

```bash
keel agent-setup . --client claude-code --write
keel serve --repo .
```

## 12. Test Keel As A Developer

Run all tests:

```bash
python -m pytest
```

Run focused tests:

```bash
python -m pytest tests/test_memory.py
python -m pytest tests/test_cli.py
python -m pytest tests/test_brief_record_serve.py
```

Build package:

```bash
python -m build
```

Check package metadata:

```bash
python -m twine check dist/*
```

Run built-in memory eval:

```bash
python -m keel.cli eval . --json
```

## 13. Development Workflow

Use this loop when developing Keel:

```text
1. Decide the feature.
2. Update or add tests.
3. Implement the feature.
4. Run focused tests.
5. Run full pytest.
6. Run package build and twine check if packaging changed.
7. Update docs.
8. Update buildkeelupdates.md.
9. Refresh Graphify if files changed meaningfully.
10. Commit and push.
```

Commands:

```bash
python -m pytest
python -m build
python -m twine check dist/*
keel sync . --no-graph
keel manager-status .
```

Graphify refresh when needed:

```bash
graphify . --update --backend gemini
graphify cluster-only . --backend gemini
```

## 14. What To Build Next

Recommended order:

1. Real Claude Code setup testing.
2. Real Codex setup testing.
3. `keel doctor-memory` or stronger manager diagnostics.
4. Automatic stale-memory cleanup.
5. Contradiction detection.
6. Local embeddings.
7. Neural reranker.
8. Graph-aware context expansion.
9. Public benchmark adapters.
10. Agent Graph Mode later.

Do not build Agent Graph Mode until the manager loop is stable in real Claude Code/Codex use.

## 15. Debugging Checklist

If context is missing:

```bash
keel manager-status .
keel memories --repo .
keel sync . --no-graph
keel context "<task>" --repo .
```

If graph is missing:

```bash
keel graph-status .
keel sync .
```

If MCP is not working:

```bash
keel agent-setup . --client claude-code --write
keel serve --repo .
```

If architecture check fails:

```bash
keel check . --json --html
keel explain CONTRACT_ID .
```

If tests fail:

```bash
python -m pytest -q
```

## 16. Mental Model

```text
LLM agent = reasoning
Keel = memory + manager + guardrails
SQLite = durable local storage
Graphify = project graph
tests/CI = proof
```

Keel should never pretend memory is perfect. It should show sources, confidence, coverage, and verification status.
