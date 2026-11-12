# Semblance Canvas

A local **Speech-to-Canvas MVP** that listens to user speech, interprets only explicitly stated information with strict factual provenance, and dynamically manipulates an embedded [diagrams.net](https://app.diagrams.net) canvas in near real time.

## AI backend: Google Antigravity subscription

The default backend invokes the official Antigravity CLI in headless mode and reuses its cached Google OAuth credentials. This allows the pipeline to consume the quota associated with a Google AI Pro/Ultra subscription without a Gemini Developer API key.

### One-time setup

1. Install the Antigravity CLI so the `agy` executable is available on `PATH`.
2. Run `agy` interactively once and sign in with the Google account that owns the subscription.
3. Exit the interactive session. Subsequent pipeline calls use `agy --print` and the cached OAuth session.

The default `config.json` uses:

```json
{
  "ai": {
    "backend": "antigravity_cli",
    "antigravity_cli_path": "agy",
    "model": "",
    "cli_timeout_seconds": 60
  }
}
```

Leave `model` empty to use the account's current default model. Set it only to an identifier returned by the installed Antigravity CLI. The Antigravity child process deliberately receives neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY`, preventing accidental fallback to separately billed Developer API usage.

### Alternative backends

- `google_genai`: official Gemini Developer API via `GEMINI_API_KEY`; its billing and quota are separate from Google AI subscriptions.
- `gemini_cli`: compatibility with the deprecated legacy CLI; not the default.
- `mock`: deterministic offline backend used by tests.

### Operational Architecture

The Antigravity backend runs via a persistent resident `stream-json` daemon (`subprocess.Popen` with `CREATE_NO_WINDOW`). The CLI process initializes once at server boot, eliminating per-turn cold-start overhead and maintaining state while consuming the user's active Google AI Pro/Ultra subscription quota.

---

## ⚠️ Known Limitations & Future Architecture

### 1. Sequential Turn Processing vs. Multi-Worker Concurrency
- **Current State:** The backend operates with dedicated threads per pipeline stage (audio capture -> semantic extraction -> canvas geometry -> diagram bridge). Because a single LLM session is inherently stateful and sequential, phrases are processed turn-by-turn in FIFO order. While stage pipelining allows simultaneous audio capture during model inference, multiple concurrent semantic extractions on the same session are not parallelized.
- **Future Feature (Worker Pooling & Load Balancer):** Implement an actor-based pool with an automatic load balancer spanning multiple warm Antigravity CLI daemon instances, allowing parallel processing of concurrent audio segments while preserving graph consistency.

### 2. Standalone Operation Without Microphone
- The pipeline is fully sanitized for headless and text-only execution: if no microphone hardware is available, the server defaults to simulation/WebSockets mode without raising input errors.

### 3. Diagrammatic Relationship Representation vs. Text Labels
- **Observed Issue:** Edge labels (e.g., verbal connection phrases) currently render directly over connector paths. When nodes are spaced closely, label text collides with neighboring node boxes.
- **Planned Refactor:** Shift relationship representation from verbal label text to strictly graphical signifiers (arrowhead types, line dash patterns, color weighting, or separate legend annotations), reserving inline text only for anomalous/non-standard relationships.

### 4. Canvas Spatial Collision Prevention
- **Observed Issue:** Geometric placement in Skill 2 relies on semi-static grid offsets, occasionally resulting in node overlap when text length exceeds standard card bounds or cluster boundaries are tight.
- **Planned Refactor:** Introduce automated force-directed layout relaxation or dynamic AABB (Axis-Aligned Bounding Box) collision detection with variable padding based on rendered label metrics.

### 5. Unified Single-Turn Semantic + Graphical Schema
- **Research Goal:** Explore combining Skill 1 (semantic extraction) and Skill 2 (canvas layout calculation) into a single cohesive turn. Generating semantic validation and layout coordinates in one round-trip will cut per-utterance latency by approximately 50%, enabling true near-real-time streaming to the canvas.

### 6. Deletion Lifecycle & Object Tracking (Remove Action Invalidation)
- **Observed Issue:** Spoken commands to remove elements (e.g., *"remove step 1 and step 2"*) do not clear the shapes from the canvas.
- **Root Cause & Resolution:**
  - The diagrams.net bridge currently issues `'merge'` actions via `postMessage`. In draw.io semantics, `'merge'` is strictly additive and modifying—it never removes existing cells that are absent from the incoming XML.
  - To support deletion, the bridge must either transition to full state reloads (`'load'`) or emit targeted cell removal commands matching persistent concept IDs mapped to `mxCell` IDs.

---

## 🎯 Project Mission & Philosophy

Semblance Canvas is **not** a speculative brainstorming partner, planning assistant, or autonomous agent.

The AI's mandate is strictly bounded:
1. **Listen & Transcribe**: Ingest spoken input with zero hallucination.
2. **Interpret Explicit Meaning**: Extract only concepts and connections explicitly stated by the user.
3. **Organize Visually**: Cluster semantically related ideas without synthesizing unsubstantiated semantic relationships.
4. **Direct Diagram Modifications**: Execute diagram operations (e.g., standard templates, alignments, moves) upon command.
5. **Non-Invention Guarantee**: Never fabricate facts, relationships, or structural dependencies.

---

## 🏛️ System Architecture Overview

```text
┌─────────────────┐
│   Microphone    │
└────────┬────────┘
         │ (Audio Stream / PCM)
         ▼
┌─────────────────┐
│   Python STT    │ (e.g., Local Whisper / Faster-Whisper)
└────────┬────────┘
         │ Transcript chunks + Timestamps/Source IDs
         ▼
┌─────────────────────────┐
│ Semantic Interpretation │ (Mode A: Ideas Design | Mode B: Diagram Direction)
│  & Provenance Validator │ [Enforces Non-Invention Rule]
└────────┬────────────────┘
         │ Graph / Diagram Instruction Package (JSON IR)
         ▼
┌─────────────────────────┐
│   JavaScript Bridge     │ (Local WebSocket / HTTP Server -> Browser)
└────────┬────────────────┘
         │ postMessage API / XML-mxGraph manipulation
         ▼
┌─────────────────────────┐
│ diagrams.net (Embedded) │
└─────────────────────────┘
```

---

## 🔄 Two Core Processing Modes

### Mode A: Ideas Design
- **Objective**: Ingest user thoughts, identify explicit concepts, and place them on the canvas.
- **Visual Spatial Proximity vs. Relationships**:
  - Concepts sharing semantic context may be positioned close to each other.
  - **No edge (dependency, causality, hierarchy, sequence, or ownership) is created unless explicitly spoken by the user.**
- **Provenance**: Every node and relationship links back to its exact transcript source IDs (`source_ids`).

### Mode B: Diagram Direction
- **Objective**: Execute direct structural or layout instructions (e.g., *"Put these closer"*, *"X depends on Y"*, *"Create an Ishikawa for this problem"*).
- **Templates & Standards**: Recognized frameworks (e.g., Ishikawa 6M: *Man, Machine, Method, Material, Measurement, Mother Nature*) may supply structural scaffolding labels, but leaves/causes remain empty placeholders unless explicitly provided by the user.

---

## 🚫 The Non-Invention Rule

Every factual entity in the diagram must maintain verifiable provenance:
- **Concept Node**: Must track the `source_ids` from which it was extracted.
- **Relationship Edge**: Must track the `source_ids` asserting the connection. If unsupported, the relationship is forbidden.

---

## 📚 Project Documentation

- [Project Architecture & System Design](file:///docs/ARCHITECTURE.md)
- [Data Models, Schemas & Protocols](file:///docs/DATA_MODELS_AND_SCHEMAS.md)
- [Implementation Roadmap & Milestones](file:///docs/ROADMAP.md)

---

## ⚡ Current Status
The Python real-time bridge server (`src.server`), persistent headless `agy` CLI daemon (`stream-json`), diagrams.net embedded iframe, non-invention verification suite, intelligent 4-stage pipeline semáforo, interactive Dev Tab inspector, and session-state deletion lifecycle are fully implemented and running locally.

---

## 🎯 Next Steps & Architecture Roadmap

### 1. Hybrid Deterministic Compilation vs. LLM Spatial Reasoning
- **Core Principle**: Reserve the LLM strictly for natural language comprehension and semantic entity extraction; delegate geometry, coordinates ($x, y$), padding, container wrapping, and mxGraph XML generation to **deterministic Python layout algorithms** (DAG topological sort, grid packing, swimlane partitioning).
- **Benefit**: Drastically reduces token usage, eliminates LLM spatial drift, prevents card overlapping, and cuts pipeline latency by more than 50%.

### 2. Semantic Taxonomy & Entity Discrimination
Refine Skill 1 (`text_to_semantic_json`) to categorize spoken entities into a formal typed taxonomy:
- 👤 **Actor / Role**: External actors, human roles, internal departments, or client apps.
- ⚙️ **Process Step / Action**: Discrete operational tasks or state transitions.
- 🗄️ **Data Source / Store**: Relational databases, object storage, caches, or messaging queues.
- 📝 **Annotation / Side Note**: Non-flow remarks, constraints, or metadata attached by proximity.
- 🔀 **Decision Gateway**: Branching conditions (*if/else*, approval gates).
*Note: Because skills are loaded once into persistent session memory, enriching the JSON Schema with typed enums and short one-line docstrings maintains sub-second inference speeds without prompt bloat.*

### 3. Proactive Daemon Pre-warming (Zero Starting Delay)
- **Problem**: When a session first spawns, the initial turn incurs a warm-up handshake cost (~2–3s) while the CLI daemon registers the schema.
- **Solution**: Trigger a background pre-warming turn as soon as `src.server` boots or when `preview.html` opens. When the user speaks or types their first phrase, the resident daemon is already primed, guaranteeing instant sub-second response from turn 1.

### 4. Single-Pass Consolidated Pipeline (Evaluation)
- Run offline benchmark tests comparing the 2-step pipeline (Semantic -> Canvas) against a single-pass unified prompt with Chain-of-Thought to evaluate latency gains while strictly verifying that the **Non-Invention Rule** is not compromised by premature geometric assumptions.

### 5. Global Semantic Re-scoping & Granularity Refactoring
- **Context**: During multi-turn voice dictation, a cluster created in turn 1 (e.g., *"Purchasing Process"*) may later be discovered to represent only an initial sub-phase once subsequent turns detail downstream stages (Approval, Execution, Warehouse Verification).
- **Architecture Goal**: Introduce an automatic scope-refactoring heuristic in the semantic engine. When new clusters are topologically downstream or subsidiary to an existing container, the engine either:
  1. Re-labels the original cluster to its specific sub-phase (e.g., *"Requisition / Initial Issuance"*), or
  2. Wraps all subsidiary clusters into a higher-order macro-swimlane (Enterprise Scope).

### 6. Mixed-Intent Utterance Disambiguation (Mode A vs Mode B)
- Support mixed natural speech where domain descriptions interleave with direct screen commands (e.g., *"Also, move the approval spreadsheet closer to purchasing, and add a note saying this happens only on Tuesdays"*).
- The semantic layer splits the utterance into an atomic factual assertion (`concepts`/`relationships`) and an imperative screen mutation (`direct_actions`).

### 7. Dual-Layer Local Session Persistence (Implemented)
- **Problem Solved**: Page refreshes or temporary disconnections previously cleared the visual canvas.
- **Implementation**:
  - **Backend**: Auto-persists the entire session graph, action history, and transcript segments to `data/session_state.json` upon every successful pipeline turn.
  - **Frontend**: Mirrors active mxGraph XML in browser `localStorage`.
  - **Reconnection Handshake**: On browser reloads or WebSocket reconnects, the server and client automatically restore the diagram state seamlessly.
