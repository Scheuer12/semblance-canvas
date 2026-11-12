# Known Issues & Technical Debt

This document tracks known architectural limitations, edge cases, and in-progress infrastructure items for **Semblance Canvas**. As an open, production-minded project, we maintain this registry transparently to guide contributors and set clear expectations for production readiness.

---

## 🚦 Active Known Issues & In-Progress Items

### 1. Automated CI/CD Workflow (In Construction)
* **Severity**: Low (Development Infrastructure)
* **Current State**: The project maintains a complete offline test suite (10 unit tests validating schemas, Non-Invention invariants, state mutations, deterministic layout type mapping, and geometry stabilization) which currently runs locally via `python -m unittest discover tests`.
* **Planned Resolution**: An automated GitHub Actions CI/CD pipeline (covering multi-platform testing on Ubuntu/Windows/macOS, Flake8 linting, and JSON schema verification) is actively in construction.  
  * **Milestone**: It will be deployed following the completion of the pre-publication validation suite.

---

### 2. Collision Avoidance & Long Edge Obstacle Routing
* **Severity**: Medium (Visual Ergonomics)
* **Current State**: The canvas generator applies deterministic Axis-Aligned Bounding Box (AABB) container calculation, dynamic margins, and arc jump connectors (`jumpStyle=arc`). However, in dense multi-step workflows with multiple converging cross-container branches (e.g. from *Processo de Compras* across to *Canais de Entrada*), long straight edges can still intersect cards or cross through intermediate nodes.
* **Planned Resolution**: Implement obstacle-aware orthogonal edge routing with intersection penalties:
  * **Convex Obstacle Avoidance**: Edges route around the perimeter of intermediate bounding boxes rather than traversing their centers.
  * **Dynamic Multi-Cluster Lane Assignment**: Long cross-swimlane lines are assigned dedicated vertical gutters between containers.
  * **Topological Layer Spacing**: Ensures parallel branches maintain distinct $Y$-lanes.

---

### 3. Bidirectional Canvas Sync / The Reverse Path (UI-to-AI Synchronization)
* **Severity**: High (Architectural Evolution)
* **Current State**: State flow is currently **unidirectional**: `Speech / Text -> Semantic IR -> Layout Geometry -> diagrams.net (load)`. If a user manually drags a node, renames a card, or adjusts an arrow directly inside the diagrams.net canvas UI, diagrams.net retains those changes visually, but the backend `session_state.py` and the AI context are unaware of them. A subsequent speech utterance will re-render the canvas from backend state, potentially reverting manual layout tweaks.
* **Planned Resolution**: Establish the **Reverse Path**:
  * Listen to iframe `postMessage` events (`autosave` and `export` XML payloads) emitted whenever the user modifies the canvas manually.
  * A reverse parser in `src/canvas/` extracts modified node coordinates, labels, and removed vertices back into `CanvasSessionState`.
  * Inject the user's manual adjustments into the AI prompt context so subsequent voice commands respect and build upon manual canvas edits rather than overwriting them.

---

### 4. Global Semantic Re-scoping & Granularity Refactoring
* **Severity**: Medium (Visual Coherence across Extended Dialogues)
* **Current State**: If an early utterance establishes a topical cluster (e.g., *"Purchasing Process"* with 2 nodes), and subsequent turns detail 4 downstream phases (Approval, Execution, Warehouse Verification), the original cluster may remain topologically parallel rather than being refactored into a specific sub-phase (*"Requisition / Initial Issuance"*) or elevated into a macro-container.
* **Planned Resolution**: Implement a topological re-scoping heuristic in the semantic engine. When new clusters are discovered to be downstream or subsidiary to an existing container, the engine automatically re-labels or restructures the hierarchy into parent-child swimlanes.

---

### 5. Mixed-Intent Utterance Disambiguation (Mode A vs. Mode B)
* **Severity**: Low (Input Edge Case)
* **Current State**: The system accurately classifies pure domain descriptions as **Mode A** and imperative diagram commands as **Mode B**. However, composite sentences combining both (e.g., *"Move the approval sheet closer to purchasing, and also note that deliveries occur only on Tuesdays"*) can create classification ambiguity.
* **Planned Resolution**: Add a pre-parsing speech classifier that splits compound sentences into atomic factual assertions and imperative diagram mutations before skill execution.

---

### 6. Multi-Client Concurrency & CLI Thread Balancing
* **Severity**: Low (Current Scope: Single-User Desktop Studio)
* **Current State**: The local FastAPI/WebSocket server maintains a single persistent `agy` daemon. If multiple browser tabs send speech segments simultaneously, their requests are queued synchronously.
* **Planned Resolution**: Introduce an instance pool and worker load-balancer for multi-tenant deployments or team collaborative canvas sessions.

---

### 7. Browser Microphone Compatibility (Web Speech API)
* **Severity**: Low (Client-side)
* **Current State**: The real-time microphone dictation feature leverages the browser's native `webkitSpeechRecognition` / `SpeechRecognition` API, which delivers zero-latency transcription out-of-the-box in Google Chrome and Microsoft Edge, but is blocked by default in Brave privacy shields and limited in Firefox.
* **Workaround / Fallback**: Manual text input and pastable XML are fully supported across all browsers. Furthermore, the local Python acoustic engine (`src/audio/realtime_stt.py`) is available for direct hardware capture.

---

## ✅ Recently Resolved & Landed Optimizations

### Landed: Enhanced Semantic Differentiation & Deterministic Type Mapping Engine
* **Status**: Completed (`src/canvas/deterministic_layout.py`)
* **Impact**: Eliminated the secondary 25-second LLM layout call (Skill 2) from the critical loop. Geometry and visual typing are now calculated in **< 5ms** directly in Python:
  * ⚙️ `process_step` ➔ Rounded blue card (Operational Action)
  * 📝 `side_annotation` ➔ Yellow dashed sticky note (Observations / Caveats)
  * 🗄️ `data_store` ➔ Green cylinder (Databases, Spreadsheets, Physical storage)
  * 🔀 `decision_gate` ➔ Yellow diamond (Approvals / Conditions)
  * 👤 `actor` ➔ Persona figure (Departments, Roles)
  * 💡 `concept` ➔ Lavender rounded card

### Landed: Speech Debounce & Queue Coalescing (4x Speedup)
* **Status**: Completed (`preview.html` & `src/server.py`)
* **Impact**: Added an 8-word / 1.2s silence debounce buffer in the browser, eliminating single-word fragment turns (*"separado"*, *"então"*). Implemented asynchronous non-blocking queue coalescing on the WebSocket server, folding multi-turn incoming speech into a single prompt when the LLM is busy. Overall dialogue latency reduced from **~8 minutes down to 1m53s**!

---

## 📌 Reporting New Issues
Found a bug or an undocumented edge case? Please open an issue on the [GitHub Issue Tracker](https://github.com/Scheuer12/semblance-canvas/issues).
