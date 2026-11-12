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

### 2. Semantic Taxonomy & Entity Discrimination (Fine-Grained Classification)
* **Severity**: Medium (Semantic Fidelity)
* **Current State**: Concepts extracted by Skill 1 (`text_to_semantic_json`) are primarily categorized under general types (`concept`, `process_step`, `cluster_container`).
* **Planned Resolution**: Extend schema and skill prompts with an explicit, typed domain taxonomy:
  * 👤 **Actor / Role**: External actors, human roles, client systems.
  * ⚙️ **Process Step / Action**: Operational tasks, state transitions.
  * 🗄️ **Data Source / Store**: Relational databases, files, caches, queues.
  * 📝 **Annotation / Side Note**: Non-flow commentary or business constraints.
  * 🔀 **Decision Gateway**: Conditional branching (*if/else*, approval gates).
* **Impact**: Eliminates homogeneous rendering and generates tailored shapes/icons in diagrams.net.

---

### 3. Global Semantic Re-scoping & Granularity Refactoring
* **Severity**: Medium (Visual Coherence across Extended Dialogues)
* **Current State**: If an early utterance establishes a topical cluster (e.g., *"Purchasing Process"* with 2 nodes), and subsequent turns detail 4 downstream phases (Approval, Execution, Warehouse Verification), the original cluster may remain topologically parallel rather than being refactored into a specific sub-phase (*"Requisition / Initial Issuance"*) or elevated into a macro-container.
* **Planned Resolution**: Implement a topological re-scoping heuristic in the semantic engine. When new clusters are discovered to be downstream or subsidiary to an existing container, the engine automatically re-labels or restructures the hierarchy into parent-child swimlanes.

---

### 4. Mixed-Intent Utterance Disambiguation (Mode A vs. Mode B)
* **Severity**: Low (Input Edge Case)
* **Current State**: The system accurately classifies pure domain descriptions as **Mode A** and imperative diagram commands as **Mode B**. However, composite sentences combining both (e.g., *"Move the approval sheet closer to purchasing, and also note that deliveries occur only on Tuesdays"*) can create classification ambiguity.
* **Planned Resolution**: Add a pre-parsing speech classifier that splits compound sentences into atomic factual assertions and imperative diagram mutations before skill execution.

---

### 5. Multi-Client Concurrency & CLI Thread Balancing
* **Severity**: Low (Current Scope: Single-User Desktop Studio)
* **Current State**: The local FastAPI/WebSocket server maintains a single persistent `agy` daemon. If multiple browser tabs send speech segments simultaneously, their requests are queued synchronously.
* **Planned Resolution**: Introduce an instance pool and worker load-balancer for multi-tenant deployments or team collaborative canvas sessions.

---

### 6. Browser Microphone Compatibility (Web Speech API)
* **Severity**: Low (Client-side)
* **Current State**: The real-time microphone dictation feature leverages the browser's native `webkitSpeechRecognition` / `SpeechRecognition` API, which delivers zero-latency transcription out-of-the-box in Google Chrome and Microsoft Edge, but is limited in Firefox or Safari.
* **Workaround / Fallback**: Manual text input and pastable XML are fully supported across all browsers. Furthermore, the local Python acoustic engine (`src/audio/realtime_stt.py`) is available for direct hardware capture.

---

## 📌 Reporting New Issues
Found a bug or an undocumented edge case? Please open an issue on the [GitHub Issue Tracker](https://github.com/Scheuer12/semblance-canvas/issues).
