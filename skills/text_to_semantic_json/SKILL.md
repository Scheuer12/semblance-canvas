---
name: text_to_semantic_json
description: Translates raw transcript speech segments into a logical adaptive semantic JSON model, maintaining strict factual provenance and non-invention rules.
---

# Skill: Text to Logical Adaptive JSON (Semantic JSON)

## Objective
Analyze transcribed speech segments from the user, determine whether the input represents thoughts/ideas (**Mode A**) or direct diagram instructions (**Mode B**), and synthesize an adaptive semantic JSON representation.

## Fundamental Operating Invariants

### 1. The Non-Invention Rule (ZERO Hallucination)
- **Do not invent unsupported facts**: Every concept extracted into `concepts` must trace back to the user's transcript via `source_ids: ["s-X", ...]`.
- **Do not invent relationships**: Relationships between concepts (`depends_on`, `causes`, `leads_to`, `part_of`, etc.) **MUST ONLY** be created if the spoken words explicitly stated that relationship.
- If two concepts merely discuss the same subject, they may belong to a common `cluster`, but **NO relationship edge may be synthesized**.

### 2. Semantic Proximity vs. Relationships
- **Similarity justifies visual grouping/clustering (`cluster_id`), but DOES NOT justify an edge.**
- Creating an edge requires explicit verbal assertion (e.g., *"Step A triggers Step B"*, *"The database depends on the storage tier"*, *"This failure was caused by overheating"*).

### 3. Dual Processing Modes
- **Mode A (Ideas Design)**: The user provides ideas, concepts, or problem descriptions. Identify entities, assign them to topical clusters, and preserve explicit links.
- **Mode B (Diagram Direction & Mutations)**: The user directly commands diagram modifications (e.g., *"Put these closer"*, *"Group these into a cluster"*, *"Create an Ishikawa for this problem"*, *"Tire o step 1 e 2"*, *"Remova o cluster X"*, *"Delete node Y"*).
  - **Deletions / Removals**: When the user requests removing or deleting an existing concept, step, or cluster:
    1. Set `"mode": "mode_b_direction"`.
    2. Exclude the deleted elements from the active `concepts` and `relationships` lists.
    3. Include a deletion entry in `direct_actions`:
       ```json
       {
         "action": "delete",
         "target_ids": ["step 1", "step 2", "Process Steps"],
         "parameters": { "reason": "User commanded removal" }
       }
       ```
  - **Template Scaffolding**: When a recognized framework (like Ishikawa / Fishbone) is requested, standard structural categories (e.g., Man, Machine, Method, Material, Measurement, Environment) may be generated as `template_scaffolding`, but leaves/causes remain empty placeholders unless explicitly supplied.

---

## Input Format
The skill receives a JSON array of transcript segments:
```json
[
  {
    "id": "s-1",
    "text": "We need to set up the authentication server before configuring the user dashboard.",
    "timestamp_start": 0.0,
    "timestamp_end": 4.2
  },
  {
    "id": "s-2",
    "text": "Also, the billing service handles payments independently.",
    "timestamp_start": 4.5,
    "timestamp_end": 7.8
  }
]
```

---

## Output Contract
Return a single valid JSON object adhering to this schema:
```json
{
  "mode": "mode_a_ideas",
  "template": null,
  "clusters": [
    { "id": "c-backend", "label": "Backend Services", "theme": "infrastructure" },
    { "id": "c-frontend", "label": "Frontend Views", "theme": "ui" }
  ],
  "concepts": [
    {
      "id": "node-auth",
      "label": "Authentication Server",
      "type": "concept",
      "cluster_id": "c-backend",
      "source_ids": ["s-1"]
    },
    {
      "id": "node-dashboard",
      "label": "User Dashboard",
      "type": "concept",
      "cluster_id": "c-frontend",
      "source_ids": ["s-1"]
    },
    {
      "id": "node-billing",
      "label": "Billing Service",
      "type": "concept",
      "cluster_id": "c-backend",
      "source_ids": ["s-2"]
    }
  ],
  "relationships": [
    {
      "id": "rel-1",
      "source": "node-auth",
      "target": "node-dashboard",
      "relation_type": "depends_on",
      "label": "before configuring",
      "directed": true,
      "source_ids": ["s-1"]
    }
  ],
  "direct_actions": []
}
```
*Notice that `node-billing` is placed in `c-backend` due to topical proximity, but has NO edge connecting it to `node-auth` because the user did not state one.*
