# Keel Memory Architecture

Keel's memory architecture is built for coding agents, not generic chat memory. The goal is to give Codex, Claude, Cursor, Gemini, and CI systems a durable local intelligence layer that knows the project, recalls the right context before edits, verifies facts against the repo, and improves through evals.

## Product Thesis

Graph tools map what exists. Memory tools remember what happened. Keel combines both and adds verification.

```text
project graph + durable memory + agent history + architecture rules + evals
```

That makes Keel a project cognition layer:

- remembers project facts, decisions, corrections, preferences, bugs, tests, dependencies, and sessions
- retrieves task-relevant context before the agent edits code
- checks whether memory is still true by looking at files
- records events and sessions for replay
- measures retrieval quality with a benchmark loop

## Industry-Level Requirements

| Requirement | Keel Design |
| --- | --- |
| Local-first privacy | Memories live in `keel-out/keel.sqlite3`. |
| Agent-native integration | CLI plus MCP tools for Codex, Claude, Cursor, Gemini, and generic clients. |
| Typed memory | Memories are classified into explicit kinds, not dumped as generic notes. |
| Noise control | Encoding gate rejects low-signal memory. |
| Hybrid retrieval | FTS, keyword scoring, tags, source, type priors, confidence, and recency. |
| Repo grounding | Verification checks file-backed memories against the repository. |
| Context delivery | `keel context` renders compact memory packs for agents. |
| Evaluation | `keel eval` reports top-1, hit@5, MRR, and score percentage. |
| Automation | `keel hooks` creates lifecycle hook configs. |
| Extensibility | Embeddings, neural rerankers, compaction, and contradiction detection can be added later. |

## Memory Pipeline

```text
capture
  -> encoding gate
  -> typed durable store
  -> retrieval planner
  -> hybrid retrieval
  -> verification
  -> context pack
  -> agent action
  -> session/event log
  -> eval feedback
```

## Layer 1: Capture

Capture sources:

- manual CLI memory: `keel remember`
- project bootstrap: `keel remember --from-project`
- MCP writes: `mcp_memory_write`
- lifecycle hooks: `keel hooks`
- Graphify summaries: `graphify-out/GRAPH_REPORT.md`
- architecture/config files: `ARCHITECTURE.md`, `.keel.yml`
- agent session facts: `keel record`, `mcp_record_action`

The capture layer should eventually support automatic conversation capture from supported clients, but the current implementation already supports the command and MCP paths.

## Layer 2: Encoding Gate

The encoding gate decides whether a candidate memory deserves long-term storage.

Current behavior:

- trims empty content
- rejects very short low-signal content like `ok`
- classifies memory kind
- normalizes tags
- records encoding confidence and reason in metadata

Command:

```bash
keel remember "Always update buildkeelupdates.md after Keel changes." --kind preference --gate
```

## Layer 3: Typed Memory Store

The current store is SQLite:

```text
keel-out/keel.sqlite3
```

Memory fields:

- `id`
- `created_at`
- `updated_at`
- `kind`
- `title`
- `content`
- `scope`
- `source`
- `tags_json`
- `metadata_json`

Memory kinds:

- `project`
- `architecture`
- `decision`
- `preference`
- `correction`
- `bug`
- `test`
- `dependency`
- `session`
- `graph`
- `config`
- `note`

Why typed memory matters:

```text
"why is this package named keel-arch?"
  -> decision memory

"how do I run tests?"
  -> test memory

"can UI touch database?"
  -> architecture memory
```

## Layer 4: Retrieval Planner

The planner turns a query into target memory types and retrieval channels.

Examples:

| Query | Target |
| --- | --- |
| `why is package called keel-arch?` | `decision` |
| `how do I run tests?` | `test` |
| `can UI access database?` | `architecture` |
| `what did we build last session?` | `session` |

Command:

```bash
keel recall "why is package called keel-arch?" --plan
```

## Layer 5: Hybrid Retrieval

Current retrieval signals:

- SQLite FTS5 when available
- title keyword hits
- content keyword hits
- tag hits
- source hits
- memory type match
- encoding confidence
- id/recency tie-break

The result includes channels so an agent can inspect why a memory was retrieved.

```bash
keel recall "how do I run tests?" --verify --plan
```

## Layer 6: Verification

Verification checks whether file-backed memory still matches the repository.

States:

- `verified`: source file or mentioned paths exist
- `stale`: source file or mentioned paths are missing
- `unverified`: no file-backed evidence exists

This is one of Keel's key advantages over generic memory systems: memory can be checked against the real codebase.

## Layer 7: Context Packaging

Agents should not receive the whole database. They need a compact task-specific memory pack.

Command:

```bash
keel context "debug dashboard failing test" --repo .
```

Output is Markdown with:

- query
- memory id
- memory kind
- score
- source
- verification status
- content

MCP tool:

```text
mcp_memory_context
```

## Layer 8: Evaluation

Keel includes a built-in memory eval loop:

```bash
keel eval .
```

Metrics:

- top-1
- hit@5
- MRR
- score percentage

Output:

```text
keel-out/memory-eval.json
```

The current built-in suite is small and internal. It is not a public SOTA benchmark claim. Its purpose is to make memory improvements measurable from day one.

## Layer 9: Lifecycle Automation

Keel can generate hook configs:

```bash
keel hooks . --client codex --write
```

Supported clients:

- `codex`
- `claude`
- `cursor`
- `gemini`
- `generic`

Lifecycle phases:

- session start: bootstrap project memory
- before task: fetch context pack
- after task: store concise session memory

## MCP Surface

Current MCP memory tools:

- `mcp_memory_search`
- `mcp_memory_write`
- `mcp_memory_bootstrap`
- `mcp_memory_context`

These sit beside architecture tools like:

- `mcp_get_brief`
- `mcp_check_change`
- `mcp_record_action`
- `mcp_get_replay`

## Future Industry Layers

The next serious upgrades are:

- local embedding index
- neural reranker
- contradiction detection
- memory compaction
- stale memory cleanup policies
- benchmark adapters for public memory evals
- graph-aware retrieval using Graphify node paths
- git-aware recall from commits and CI failures
- cross-repo identity memory
- user-scoped memory separate from repo-scoped memory

## Target End State

```text
agent/task/query
  -> planner
  -> typed memory retrieval
  -> graph retrieval
  -> session retrieval
  -> reranker
  -> repo verifier
  -> compact context pack
  -> agent action
  -> action log
  -> memory update
  -> benchmark feedback
```

Keel should become the local intelligence substrate that coding agents use before they touch a repository.
