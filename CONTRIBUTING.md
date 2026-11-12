# Contributing to Semblance Canvas

Thank you for your interest in contributing to **Semblance Canvas**! We welcome community contributions to build the next-generation real-time speech-to-diagram reasoning platform.

---

## 🏛️ Fundamental Guiding Invariant: The Non-Invention Rule

Before submitting code or skill modifications, you must understand our primary design pillar:

> **The Non-Invention Rule (Zero Hallucination)**:  
> Semblance Canvas translates human speech into diagrammatic structures with verifiable factual provenance.  
> * **Concepts** must cite valid transcript `source_ids` (`s-1`, `s-2`, ...).
> * **Relationships** (`depends_on`, `causes`, `leads_to`, etc.) **must NEVER be synthesized** merely because two entities share topical similarity.
> * Similarity justifies visual proximity and clustering, but an edge requires explicit verbal assertion.

Any contribution that introduces speculative or unasserted relationship generation will be rejected.

---

## 🛠️ Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Scheuer12/semblance-canvas.git
cd semblance-canvas
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🧪 Running Unit Tests

We maintain an offline test suite validating schemas, non-invention guardrails, persistent state transitions, and deterministic geometry:

```bash
# Set PYTHONPATH to project root and execute the test runner
python -m unittest discover -s tests -t .
```

All Pull Requests must maintain **100% test pass rate** before merging.

---

## 🚀 Running the Local Bridge Server

To test browser interactions and diagrams.net rendering:

```bash
python -m src.server --port 8050
```

Open `http://127.0.0.1:8050` in Google Chrome or Microsoft Edge.

---

## 🌿 Pull Request Workflow

1. **Fork & Branch**: Create a feature branch with a descriptive name:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```
2. **Follow Coding Standards**:
   * Code formatting adheres to PEP 8.
   * Type annotations are encouraged for public interfaces.
   * Add unit tests in `tests/` for any new logic, skill modification, or geometry handler.
3. **Commit Messages**: Write clear, imperative commit messages (e.g., `Add typed entity discrimination for data sources`, `Fix AABB collision margin`).
4. **Open a PR**: Reference any relevant items documented in [`KNOWN_ISSUES.md`](./KNOWN_ISSUES.md) or open GitHub discussions.

---

## 💬 Community & Questions

For architecture discussions, roadmap proposals, or bug reports, please open an Issue on [GitHub Issues](https://github.com/Scheuer12/semblance-canvas/issues).
