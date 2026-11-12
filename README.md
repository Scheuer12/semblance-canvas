# Semblance Canvas

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Tests: 9 Passing](https://img.shields.io/badge/tests-9%20passing-brightgreen.svg)](tests/)
[![Architecture: Provenance-Grounded](https://img.shields.io/badge/guardrail-Non--Invention%20Rule-emerald.svg)](skills/text_to_semantic_json/SKILL.md)
[![CI/CD: In Construction](https://img.shields.io/badge/CI%2FCD-in%20construction-orange.svg)](KNOWN_ISSUES.md#1-automated-cicd-workflow-in-construction)

A local **Real-Time Speech-to-Canvas Reasoning Studio** that listens to user speech, extracts strictly asserted facts under the **Non-Invention Rule (Factual Provenance Guardrail)**, and dynamically drives an embedded [diagrams.net](https://app.diagrams.net) canvas with auto-reconciled geometry, persistent state, and interactive visual telemetry.

![Semblance Canvas Real-time Execution Preview](docs/images/pipeline_preview.jpg)
*Real multi-turn execution: voice/text pipeline ingesting procurement rules into the browser studio, generating dynamic visual clusters, orthogonal arrows with collision-free arc jumps, and persistent session state on an embedded diagrams.net canvas.*

---

## 📖 Open Source Guidelines & Documentation

* 🤝 **Contributing Guide**: See [CONTRIBUTING.md](CONTRIBUTING.md) for local dev setup, coding conventions, and PR workflows.
* ⚠️ **Known Issues & Technical Debt**: See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for transparent tracking of known limitations, CI/CD roadmap, and open refactors.
* 📄 **License**: Permissive open-source [MIT License](LICENSE).
* 🏛️ **System Architecture**: Detailed design in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
* 📐 **Data Schemas & Protocols**: Schema contracts in [docs/DATA_MODELS_AND_SCHEMAS.md](docs/DATA_MODELS_AND_SCHEMAS.md).
* 🗺️ **Long-Term Milestones**: Engineering milestones in [docs/ROADMAP.md](docs/ROADMAP.md).

> [!NOTE]
> **CI/CD Automation Status**: Automated GitHub Actions workflows for continuous integration and linting are actively in construction and will be published alongside the typed semantic taxonomy milestone. The test suite currently runs locally with a 100% pass rate (9 tests passing).

---

## ⚡ Quickstart

### 1. Prerequisites & Installation
* **Python**: 3.10+ recommended.
* **Microphone (Optional)**: Modern versions of Google Chrome or Microsoft Edge natively power browser dictation via the Web Speech API. For direct local audio capture, PyAudio and PortAudio headers are supported.

```bash
git clone https://github.com/Scheuer12/semblance-canvas.git
cd semblance-canvas
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
python -m unittest discover -s tests -t .
```
*(All 9 unit tests run offline in < 0.1s without network dependencies or paid credentials).*

### 3. Start Bridge Server
```bash
python -m src.server --port 8050
```
Open **`http://127.0.0.1:8050`** in Google Chrome or Microsoft Edge. Use the **`🎙️ Ditar Voz (Mic)`** button or type directly into the test input.

---

## 🧠 AI Backend: Google Antigravity Subscription

So, since this project started as a personal problem solver, it currently works with the AI backend I had immediately available. The default backend invokes the official Antigravity CLI (`agy`) in headless mode, reusing cached Google OAuth credentials. This allows the pipeline to consume the quota associated with an active Google AI Pro/Ultra subscription without a separate pay-as-you-go Gemini Developer API key. (I mean, I was already paying for it!)

### One-Time Setup
1. Ensure the Antigravity CLI (`agy`) is available on `PATH`.
2. Run `agy` interactively once and sign in with the Google account owning the subscription.
3. Exit the interactive session. The bridge server uses a persistent resident `stream-json` daemon (`subprocess.Popen` with `CREATE_NO_WINDOW`) for low-latency multi-turn reasoning without per-turn cold-start overhead.

### Alternative Backends
* `google_genai`: Official Gemini Developer API via `GEMINI_API_KEY`.
* `gemini_cli`: Compatibility adapter for the legacy CLI.
* `mock`: Deterministic offline backend used by unit tests.

---

## ✨ Implemented Core Capabilities

1. **Strict Provenance & Non-Invention Guardrail**: Every concept node and relationship edge must trace back to explicit transcript segments (`source_ids`). Unsupported relationships are strictly rejected.
2. **Deterministic Geometric Stabilization (`mxgraph_converter.py`)**:
   * **Dynamic Bounding Boxes**: Containers mathematically enclose member nodes with safe margins (30px lateral, 45px header). Cards never overflow their swimlane.
   * **AABB Collision Buffer**: Overlapping nodes are detected and cleanly spaced downward with a 30px buffer.
   * **Arc Jump Connectors (`jumpStyle=arc`)**: Orthogonal lines that intersect display clean bridge jumps, eliminating line ambiguity.
   * **Adaptive Semantic Edge Routing**: Open relation vocabulary (`requires`, `triggers`, `delivers_to`, `depends_on`) maps dynamically to specialized line styles (dashed dependencies, blue flow triggers, diamond containment).
3. **State Mutation & Deletion Lifecycle (`session_state.py`)**:
   * Spoken commands to remove elements (e.g., *"tire o step 1"*) resolve target IDs, purge dangling edges, mark actions as `DONE`/expired, and synchronize the visual canvas via full state reload (`load`), eliminating ghost shapes.
4. **Dual-Layer Session Persistence**:
   * Auto-saves the complete graph, action history, and transcript segments to `data/session_state.json`.
   * Mirrors XML in browser `localStorage`. Refreshing the browser (**F5**) restores the entire canvas and terminal log instantly.
5. **Interactive Telemetry Semáforo & Resilient Dev Inspector**:
   * 4-stage pipeline semáforo (Audio, Semantic, Layout, Diagrams Bridge) with visual spinners, frozen error state, and zero-overflow diagnostic tooltips.
   * Real-time Semantic JSON streaming: displays raw AI output immediately upon receipt, with red error badges and commented banners if schema warnings arise.
   * Self-healing reflection loops: automatically prompts the resident AI daemon to repair minor schema violations before raising pipeline errors.
6. **Background AI Daemon Pre-warming**:
   * Proactively pre-warms the persistent resident `agy` daemon process on server boot, eliminating the first-turn cold-start latency and logging resident readiness to the Live Logs terminal.
7. **Native Browser Voice Dictation**:
   * One-click microphone toggle utilizing native Web Speech API (`pt-BR` / `en-US`), passing speech chunks into the WebSocket pipeline with continuous interim preview.

---

## 🎯 Next Steps & Architecture Roadmap

For full technical specifications and active issue tracking, refer to [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md). Key milestones include:

1. **Collision Avoidance & Overlap Prevention**: Force-directed layout passes, dynamic padding calculation, and obstacle-aware orthogonal routing with intersection penalties to eliminate accidental edge-node crossovers.
2. **Enhanced Semantic Differentiation**: Fine-grained taxonomy distinguishing operational process steps, informational annotations, naming labels, side observations, and typed edge semantics.
3. **The Reverse Path (Bidirectional Canvas-to-AI Sync)**: Listening to diagrams.net `autosave` postMessage events to ingest manual canvas edits back into Python `CanvasSessionState` and provide manual layout context to the AI model.
4. **Global Semantic Re-scoping**: Automatic heuristic to refactor early micro-clusters into higher-order macro-swimlanes as multi-turn dialogues unfold.
5. **Automated CI/CD Workflow**: GitHub Actions pipeline for automated linting, schema validation, and multi-OS regression testing (in progress).
6. **Mixed-Intent Utterance Disambiguation**: Splitting composite sentences containing both domain facts (Mode A) and canvas layout directives (Mode B).

---

## 🏛️ System Architecture Overview

```text
┌─────────────────┐
│   Microphone    │ (Browser Web Speech API / PyAudio)
└────────┬────────┘
         │ (Audio Stream / Transcribed Segments)
         ▼
┌─────────────────────────┐
│ Semantic Interpretation │ (Skill 1: Mode A: Ideas | Mode B: Direction)
│  & Provenance Validator │ [Enforces Non-Invention Rule via Schema Validation]
└────────┬────────────────┘
         │ Semantic JSON IR (Concepts, Topical Clusters, Explicit Edges)
         ▼
┌─────────────────────────┐
│   Geometric Layout      │ (Skill 2 + Deterministic AABB & Dynamic Bounding Boxes)
│  & mxGraph Serializer   │ [Arc Jumps, Visual Hierarchy, Orthogonal Routing]
└────────┬────────────────┘
         │ mxGraph Model XML
         ▼
┌─────────────────────────┐
│   JavaScript Bridge     │ (FastAPI WebSocket Server -> Browser Client)
└────────┬────────────────┘
         │ postMessage API (action: 'load', autosave: 1)
         ▼
┌─────────────────────────┐
│ diagrams.net (Embedded) │ [Interactive, Fully Editable Visual Canvas]
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

## 📚 Documentation - Deepdive the project structure

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
