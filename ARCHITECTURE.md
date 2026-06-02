# Keel Architecture

Keel is a local-first project memory engine for coding agents.

The goal is not to clone generic agent memory. Keel's sharper target is:

```text
agent memory + Graphify project graph + evidence + contradiction detection
```

Keel should help Codex, Claude, Cursor, Gemini, and other MCP-compatible agents remember what is still true about a software project.

## Product Thesis

Generic agent memory remembers sessions.

Keel remembers the project as a living engineering system:

- what commands were run
- what failed
- what passed
- what files changed
- what the user corrected
- what the Graphify project graph says
- what facts became stale or contradicted
- what context the next agent should receive

## Design Principles

1. Evidence first.
   Every important memory must point back to a command, file, graph node, git state, user note, or session event.

2. Graphify first.
   The project graph is not an optional decoration. It is the structural memory layer that links facts to files, modules, functions, docs, and communities.

3. Safe context.
   Agents should receive confidence-ranked context, not random remembered text.

4. Local first.
   SQLite and local files are the default. External APIs are optional and explicit.

5. Contradictions are product value.
   If README says `npm test` but blackbox evidence says the project has no test script, Keel should say so.

6. Narrow surface.
   Keel exposes graph, memory, blackbox, and MCP. It avoids unrelated dashboards, rule engines, and noisy features until the core works.

## High-Level Flow

```text
Agent / User / CLI / MCP
        |
        v
Observation Layer
  - commands
  - tool calls
  - file edits
  - test output
  - user corrections
  - Graphify graph updates
        |
        v
Evidence Store
  - raw events
  - command outputs
  - git snapshots
  - graph snapshots
        |
        v
Memory Compiler
  - dedup
  - classify
  - summarize
  - extract facts
  - link to Graphify nodes
  - detect contradiction/staleness
        |
        v
Memory Index
  - SQLite tables
  - BM25 / FTS
  - vector embeddings later
  - graph links
        |
        v
Context Engine
  - retrieve
  - rerank
  - verify
  - mark stale/contradicted
  - produce agent context pack
        |
        v
Agent receives safe project context
```

## Core Components

### 1. Graph Layer

Purpose:

- build project graph using Graphify
- keep `graphify-out/graph.json` current
- generate `graphify-out/graph.html`
- expose graph status through CLI and MCP
- map memories to graph nodes

Current public commands:

```bash
keel graph .
keel graph-status .
keel graph-open .
```

Future memory link:

```text
memory -> graph_node_id
memory -> source_file
memory -> symbol/module/community
```

### 2. Blackbox Layer

Purpose:

- record what happened during agent work
- capture evidence, not guesses
- preserve command failures and successes
- store user corrections and decisions

Current storage:

```text
keel-out/keel.db
```

Current tables:

```text
sessions
events
```

Current public commands:

```bash
keel session-start .
keel run "npm run build" --repo . --session 1
keel blackbox-note "Decision: use yarn locally." --repo . --session 1 --kind decision
keel sessions .
keel blackbox-report 1 .
keel session-end 1 .
```

Each `keel run` captures:

- command
- exit code
- duration
- timeout state
- stdout/stderr tails
- stdout/stderr hashes
- git head
- git branch
- git status
- changed files
- diff stat
- Graphify graph status

### 3. Memory Compiler

This is the next important build.

It converts raw blackbox events into durable memories.

Input:

```text
command_started
command_finished
decision
finding
user_correction
graph_snapshot
file_change
```

Output memory tiers:

```text
working memory
  raw events from current session

episodic memory
  compressed summary of what happened in a session

semantic memory
  durable facts and decisions

procedural memory
  workflows and project-specific how-to knowledge

graph memory
  links between memories and Graphify nodes
```

Example:

```text
Raw evidence:
- npm test failed: missing script
- npm run build passed
- user noted that Yarn should be used locally

Compiled memory:
- "This project has no npm test script."
- "npm run build is a verified build command."
- "Use Yarn for local development unless package scripts prove otherwise."
```

### 4. Contradiction Engine

This is Keel's key differentiator.

It compares new evidence against existing memories and project files.

Examples:

```text
README says:
  run npm test

package.json says:
  no test script

blackbox says:
  npm test failed with missing script

Keel should mark:
  README testing instruction = contradicted/stale
```

Memory statuses:

```text
verified
unverified
stale
contradicted
inferred
```

Confidence signals:

```text
command evidence > user note > current file > graph inference > old summary
```

### 5. Retrieval Engine

The retrieval engine should answer:

```text
What should the agent know before doing this task?
```

Retrieval sources:

- blackbox events
- compiled memories
- Graphify nodes and communities
- current files
- git state

Ranking signals:

- text match
- memory type
- graph proximity
- recency
- verification status
- contradiction status
- source reliability

Target output:

```markdown
# Keel Context

Coverage: HIGH

## Verified Facts
- npm run build passed in session #1.
- npm test failed because package.json has no test script.

## Relevant Graph Nodes
- package.json
- vite.config.js
- src/App.jsx

## Warnings
- README testing instructions appear stale.

## Suggested Next Action
- Use npm run build as verification unless the user asks for test setup.
```

### 6. MCP Layer

Purpose:

- let agents use Keel without manually typing CLI commands
- expose graph and memory operations to Codex/Claude/Cursor/Gemini

Current MCP tools:

```text
mcp_graph_build
mcp_graph_status
mcp_blackbox_start
mcp_blackbox_run
mcp_blackbox_note
mcp_blackbox_sessions
mcp_blackbox_report
mcp_blackbox_end
```

Future MCP tools:

```text
mcp_memory_consolidate
mcp_memory_search
mcp_memory_context
mcp_memory_contradictions
mcp_memory_verify
```

## Target SQLite Schema

Current:

```text
sessions(id, started_at, ended_at, label, status, repo)
events(id, session_id, ts, kind, payload_json)
```

Next:

```text
memories(
  id,
  created_at,
  updated_at,
  tier,
  kind,
  title,
  content,
  status,
  confidence,
  source_event_ids_json,
  graph_node_ids_json,
  file_paths_json,
  tags_json,
  metadata_json
)

memory_links(
  id,
  source_memory_id,
  target_type,
  target_id,
  relation,
  confidence
)

contradictions(
  id,
  memory_id,
  contradicting_source_type,
  contradicting_source_id,
  summary,
  status,
  detected_at
)
```

## Minimal Build Plan

Phase 1: Keep current graph and blackbox.

Already present:

- `keel graph`
- `keel run`
- `keel blackbox-report`
- MCP graph/blackbox tools

Phase 2: Add memory compiler.

Commands:

```bash
keel consolidate --session 1
keel memories .
```

MCP:

```text
mcp_memory_consolidate
```

Phase 3: Add retrieval and context.

Commands:

```bash
keel search "how do I test this project?"
keel context "modify the todo app"
```

MCP:

```text
mcp_memory_search
mcp_memory_context
```

Phase 4: Add contradiction detection.

Commands:

```bash
keel contradictions .
keel verify .
```

MCP:

```text
mcp_memory_contradictions
mcp_memory_verify
```

Phase 5: Evaluate.

Benchmark tasks:

- retrieve correct build/test command
- avoid repeated failed command
- identify stale README instruction
- remember user correction
- link task to correct Graphify nodes
- reduce context tokens

## Success Definition

Keel is better than generic agent memory when it can say:

```text
The README says npm test, but that is contradicted.
In session #1, npm test failed because no test script exists.
npm run build passed.
The relevant files are package.json and vite.config.js.
Use npm run build as the verified command.
```

That is the product.
