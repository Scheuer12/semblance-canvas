---
name: semantic_json_to_canvas_json
description: Translates logical adaptive semantic JSON into the most natural and functional visual canvas schema for diagrams.net rendering.
---

# Skill: Semantic JSON to Canvas JSON

## Objective
Translate logical ideas, clusters, and explicit relationships into an aesthetically balanced, clear, and functional visual 2D layout.

## Design & Layout Guidelines

### 1. Natural Ideas Organization
- **Topical Clustering**: Nodes belonging to the same `cluster_id` should be placed inside or within the spatial bounds of their designated visual cluster.
- **Proximity without Edges**: When nodes share semantic similarity but have NO explicit relationship edge, group them compactly near each other ($x, y$ proximity) with clean margins (minimum 30–50px gap). **Do not draw an arrow between them.**
- **Edge Routing & Flow**:
  - If a sequence or dependency exists (`depends_on`, `leads_to`), order source and target left-to-right (horizontal flow) or top-to-bottom (vertical hierarchy).
  - Use orthogonal connectors (`edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;`) to minimize line crossings.

### 2. Sizing & Aesthetics
- Standard concept node dimensions: `width: 160`, `height: 60`.
- Process/Step node dimensions: `width: 180`, `height: 50`.
- Cluster container dimensions: Dynamically enclose all member nodes with at least `40px` internal padding.
- Modern visual palette:
  - Concept: `rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;fontStyle=1;`
  - Scaffolding/Branch: `rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6B656;fontStyle=1;`
  - Placeholder: `rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#F5F5F5;strokeColor=#666666;fontColor=#333333;`
  - Container/Cluster: `swimlane;startSize=25;rounded=1;collapsible=0;fillColor=#F8CECC;strokeColor=#B85450;`

### 3. Special Templates
- **Ishikawa (Fishbone)**:
  - Central spine line running left to right terminating in the problem head at the far right.
  - 6 diagonal main branches (3 above the spine angled down, 3 below the spine angled up).
  - Placeholder leaves branch off the category stems.
- **Mind Map**:
  - Central root idea placed at canvas center.
  - Secondary branches distributed radially around the root.

---

## Output Contract
Return a JSON object conforming to `schema.json`:
```json
{
  "canvas_metadata": {
    "layout_style": "clustered_freeform",
    "canvas_width": 1000,
    "canvas_height": 700
  },
  "visual_clusters": [
    {
      "id": "c-backend",
      "label": "Backend Services",
      "bounds": { "x": 80, "y": 80, "width": 420, "height": 220 },
      "style": "swimlane;startSize=25;rounded=1;fillColor=#F5F5F5;strokeColor=#CCCCCC;"
    }
  ],
  "nodes": [
    {
      "id": "node-auth",
      "label": "Authentication Server",
      "type": "concept",
      "cluster_id": "c-backend",
      "geometry": { "x": 110, "y": 140, "width": 160, "height": 60 },
      "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;",
      "source_ids": ["s-1"]
    },
    {
      "id": "node-billing",
      "label": "Billing Service",
      "type": "concept",
      "cluster_id": "c-backend",
      "geometry": { "x": 300, "y": 140, "width": 160, "height": 60 },
      "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;",
      "source_ids": ["s-2"]
    }
  ],
  "edges": []
}
```
