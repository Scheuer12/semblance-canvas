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

The default backend invokes the official Antigravity CLI (`agy`) in headless mode, reusing cached Google OAuth credentials. This allows the pipeline to consume the quota associated with an active Google AI Pro/Ultra subscription without a separate pay-as-you-go Gemini Developer API key.

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
