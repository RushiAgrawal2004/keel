# Keel

Keel finds the unwritten rules of your codebase and makes them executable.

Architecture regression tests for AI-generated code, powered by Graphify.

## Quickstart

```bash
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
keel events .
keel export-events .
keel export . --format json
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

## Limitations

- Keel depends on Graphify's graph quality.
- Keel proposes likely invariants, not universal truths.
- Human approval is required before enforcement.
- Layer and zone assignment are folder-based in v1.
- Keel is not a general code quality reviewer and does not replace tests.
