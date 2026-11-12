# Known Issues & Technical Debt

This document tracks known architectural limitations, edge cases, and in-progress infrastructure items for **Semblance Canvas**. As an open, production-minded project, we maintain this registry transparently to guide contributors and set clear expectations for production readiness.

---

## 🚦 Active Known Issues & In-Progress Items

### 1. Automated CI/CD Workflow (In Construction)
* **Severity**: Low (Development Infrastructure)
* **Current State**: The project maintains a complete offline test suite (9 unit tests validating schemas, Non-Invention invariants, state mutations, and geometry stabilization) which currently runs locally via `python -m unittest discover tests`.
* **Planned Resolution**: An automated GitHub Actions CI/CD pipeline (covering multi-platform testing on Ubuntu/Windows/macOS, Flake8 linting, and JSON schema verification) is actively in construction.  
  * **Milestone**: It will be deployed immediately following the completion of the **Typed Semantic Taxonomy Optimization** (Item #2 below).

---

### 2. Enhanced Semantic Differentiation (Annotations, Notes, Steps & Relations)
* **Severity**: Medium (Semantic Fidelity)
* **Current State**: Concepts extracted by Skill 1 (`text_to_semantic_json`) currently classify entities into broad categories (`concept`, `process_step`, `cluster_container`). When users provide contextual observations, side constraints, or annotations (e.g., *"essa planilha ainda não existe, será criada"*), the system often treats them as standard workflow nodes rather than distinct annotative callouts.
* **Planned Resolution**: Extend schema and skill prompts with a fine-grained, typed domain taxonomy:
  * ⚙️ **Process Step / Operational Action**: Standard sequential actions and state transitions.
  * 📝 **Annotation / Side Note / Observation**: Informational commentary, caveats, or metadata rendered as dashed sticky notes or callout shapes.
  * 👤 **Actor / System Role**: Department, human persona, or automated microservice initiating actions.
  * 🗄️ **Data Store / Artifact**: Databases, spreadsheets, forms, physical warehouse storage.
  * 🔀 **Decision Gateway**: Conditional branching (*if/else*, approval gates).
  * 🔗 **Typed Relations**: Explicit semantic edge markers (`data_flow`, `triggers`, `requires`, `delivers_to`).
* **Impact**: Eliminates visual ambiguity between what is an actionable workflow stage versus an explanatory side note.

---

### 3. Collision Avoidance & Line/Object Overlapping Prevention
* **Severity**: Medium (Visual Ergonomics)
* **Current State**: The canvas generator applies deterministic Axis-Aligned Bounding Box (AABB) container calculation and dynamic margins (30px lateral padding, 45px header buffer), and edge intersections render arc jumps (`jumpStyle=arc`). However, in dense multi-step workflows with multiple converging branches, edges can still cross boxes or cards can sit too close to swimlane borders, requiring manual user realignment.
* **Planned Resolution**: Implement a force-directed repulsion pass and orthogonal obstacle-avoidance routing:
  * **Dynamic Container Growth**: Containers recursively measure the true convex hull of child cards plus connecting labels.
  * **Obstacle-Aware Pathfinding**: Edges route orthogonally around bounding boxes with intersection penalties, preventing lines from cutting through unrelated nodes.
  * **Vertical Layer Spacing**: Topological rank assignment ensures parallel branches maintain distinct $Y$-lanes.

---

### 4. Bidirectional Canvas Sync / The Reverse Path (UI-to-AI Synchronization)
* **Severity**: High (Architectural Evolution)
* **Current State**: State flow is currently **unidirectional**: `Speech / Text -> Semantic IR -> Layout Geometry -> diagrams.net (load)`. If a user manually drags a node, renames a card, or adjusts an arrow directly inside the diagrams.net canvas UI, diagrams.net retains those changes visually, but the backend `session_state.py` and the AI context are unaware of them. A subsequent speech utterance will re-render the canvas from backend state, potentially reverting manual layout tweaks.
* **Planned Resolution**: Establish the **Reverse Path**:
  * Listen to iframe `postMessage` events (`autosave` and `export` XML payloads) emitted whenever the user modifies the canvas manually.
  * A reverse parser in `src/canvas/` extracts modified node coordinates, labels, and removed vertices back into `CanvasSessionState`.
  * Inject the user's manual adjustments into the AI prompt context so subsequent voice commands respect and build upon manual canvas edits rather than overwriting them.

---

### 5. Global Semantic Re-scoping & Granularity Refactoring
* **Severity**: Medium (Visual Coherence across Extended Dialogues)
* **Current State**: If an early utterance establishes a topical cluster (e.g., *"Purchasing Process"* with 2 nodes), and subsequent turns detail 4 downstream phases (Approval, Execution, Warehouse Verification), the original cluster may remain topologically parallel rather than being refactored into a specific sub-phase (*"Requisition / Initial Issuance"*) or elevated into a macro-container.
* **Planned Resolution**: Implement a topological re-scoping heuristic in the semantic engine. When new clusters are discovered to be downstream or subsidiary to an existing container, the engine automatically re-labels or restructures the hierarchy into parent-child swimlanes.

---

### 6. Mixed-Intent Utterance Disambiguation (Mode A vs. Mode B)
* **Severity**: Low (Input Edge Case)
* **Current State**: The system accurately classifies pure domain descriptions as **Mode A** and imperative diagram commands as **Mode B**. However, composite sentences combining both (e.g., *"Move the approval sheet closer to purchasing, and also note that deliveries occur only on Tuesdays"*) can create classification ambiguity.
* **Planned Resolution**: Add a pre-parsing speech classifier that splits compound sentences into atomic factual assertions and imperative diagram mutations before skill execution.

---

### 7. Multi-Client Concurrency & CLI Thread Balancing
* **Severity**: Low (Current Scope: Single-User Desktop Studio)
* **Current State**: The local FastAPI/WebSocket server maintains a single persistent `agy` daemon. If multiple browser tabs send speech segments simultaneously, their requests are queued synchronously.
* **Planned Resolution**: Introduce an instance pool and worker load-balancer for multi-tenant deployments or team collaborative canvas sessions.

---

### 8. Browser Microphone Compatibility (Web Speech API)
* **Severity**: Low (Client-side)
* **Current State**: The real-time microphone dictation feature leverages the browser's native `webkitSpeechRecognition` / `SpeechRecognition` API, which delivers zero-latency transcription out-of-the-box in Google Chrome and Microsoft Edge, but is limited in Firefox or Safari.
* **Workaround / Fallback**: Manual text input and pastable XML are fully supported across all browsers. Furthermore, the local Python acoustic engine (`src/audio/realtime_stt.py`) is available for direct hardware capture.

---

## 📌 Reporting New Issues
Found a bug or an undocumented edge case? Please open an issue on the [GitHub Issue Tracker](https://github.com/Scheuer12/semblance-canvas/issues).
