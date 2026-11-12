# Semblance Canvas

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Tests: 9 Passing](https://img.shields.io/badge/tests-9%20passing-brightgreen.svg)](tests/)
[![Architecture: Non--Invention](https://img.shields.io/badge/guardrail-Non--Invention%20Rule-emerald.svg)](skills/text_to_semantic_json/SKILL.md)
[![CI/CD: In Construction](https://img.shields.io/badge/CI%2FCD-in%20construction-orange.svg)](KNOWN_ISSUES.md#1-automated-cicd-workflow-in-construction)

If you love visually organizing the buckets of ideas coming spontaneously from your brain, you're gonna love this. I personally struggle drawing schemas because the way I thing better is both speaking AND drawing. So...
This is a local **Real-Time Speech-to-Canvas Reasoning Studio** that listens to user speech, interprets strictly stated facts under the **Non-Invention Rule (Zero Hallucination)**, and dynamically drives an embedded [diagrams.net](https://app.diagrams.net) canvas with auto-reconciled geometry, persistent state, and interactive visual telemetry.

---

## 📖 Open Source Guidelines & Documentation

* 🤝 **Contributing Guide**: See [CONTRIBUTING.md](CONTRIBUTING.md) for local dev setup, coding conventions, and PR workflows.
* ⚠️ **Known Issues & Technical Debt**: See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for transparent tracking of known limitations, CI/CD roadmap, and open refactors.
* 📄 **License**: Permissive open-source [MIT License](LICENSE).
* 🏛️ **System Architecture**: Detailed design in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

> [!NOTE]
> **CI/CD Automation Status**: Automated GitHub Actions workflows for continuous integration and linting are actively in construction and will be published alongside the typed semantic taxonomy milestone. The test suite currently runs locally with a 100% pass rate.

---

## ⚡ Quickstart

### 1. Clone & Install
```bash
git clone https://github.com/Scheuer12/semblance-canvas.git
cd semblance-canvas
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
python -m unittest discover -s tests -t .
```

### 3. Start Bridge Server
```bash
python -m src.server --port 8050
```
Open **`http://127.0.0.1:8050`** in Google Chrome or Microsoft Edge. Use the **`🎙️ Ditar Voz (Mic)`** button or type in the test input.

---

## 🧠 AI Backend: Google Antigravity Subscription

So, since this project started as a personal problem solver, it currently works with the AI backend I had immediately available. The default backend invokes the official Antigravity CLI (`agy`) in headless mode, reusing cached Google OAuth credentials. This allows the pipeline to consume the quota associated with an active Google AI Pro/Ultra subscription without a separate pay-as-you-go Gemini Developer API key. (I mean, I was already paying for it!)

### One-Time Setup
1. Ensure the Antigravity CLI (`agy`) is available on `PATH`.
2. Run `agy` interactively once and sign in with the Google account owning the subscription.
3. Exit the interactive session. The bridge server uses a persistent resident `stream-json` daemon (`subprocess.Popen` with `CREATE_NO_WINDOW`) for sub-second multi-turn reasoning without cold-start overhead.

### Alternative Backends
* `google_genai`: Official Gemini Developer API via `GEMINI_API_KEY`.
* `gemini_cli`: Compatibility adapter for the legacy CLI.
* `mock`: Deterministic offline backend used by unit tests.

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
