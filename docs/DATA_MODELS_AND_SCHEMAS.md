# Data Models & Schemas: Semblance Canvas

This document defines the formal data models and JSON payload contracts across each stage of the Semblance Canvas pipeline.

---

## 1. Transcript Provenance Schema

Every recognized speech segment receives an immutable identifier and timestamped entry in the transcript record.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SourceSegment",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique monotonic segment identifier (e.g., 's-1', 's-2')"
    },
    "text": {
      "type": "string",
      "description": "Raw transcribed text"
    },
    "timestamp_start": {
      "type": "number",
      "description": "Start time in seconds relative to session start"
    },
    "timestamp_end": {
      "type": "number",
      "description": "End time in seconds relative to session start"
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Transcriber confidence score"
    }
  },
  "required": ["id", "text", "timestamp_start", "timestamp_end"]
}
```

---

## 2. Graph Intermediate Representation (IR)

### 2.1 Concept Node (`CanvasNode`)
Represents an individual visual entity on the canvas.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CanvasNode",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique node identifier (e.g., 'node-101')"
    },
    "label": {
      "type": "string",
      "description": "Text label displayed inside the node"
    },
    "type": {
      "type": "string",
      "enum": [
        "concept",
        "process_step",
        "side_annotation",
        "data_store",
        "decision_gate",
        "actor",
        "group",
        "template_branch",
        "placeholder"
      ],
      "description": "Classification of the node determining its visual geometry and De-Para styling"
    },
    "source_ids": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 0,
      "description": "Mandatory list of transcript source segment IDs supporting this node. Only empty for structural template scaffolding."
    },
    "spatial_hint": {
      "type": "object",
      "properties": {
        "cluster_group": { "type": "string" },
        "relative_to": { "type": "string" },
        "direction": { "type": "string", "enum": ["left", "right", "above", "below", "inside", "near"] },
        "coordinates": {
          "type": "object",
          "properties": {
            "x": { "type": "number" },
            "y": { "type": "number" }
          }
        }
      }
    },
    "style": {
      "type": "object",
      "description": "Visual styling attributes (fill color, shape, stroke, etc.)"
    }
  },
  "required": ["id", "label", "type", "source_ids"]
}
```

### 2.2 Relationship Edge (`CanvasEdge`)
Represents an explicit connection between two nodes.

> **Strict Non-Invention Rule**: `source_ids` **MUST NOT** be empty. If no speech segment explicitly asserts the relationship, this edge cannot exist.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CanvasEdge",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique edge identifier (e.g., 'edge-202')"
    },
    "source": {
      "type": "string",
      "description": "ID of the source CanvasNode"
    },
    "target": {
      "type": "string",
      "description": "ID of the target CanvasNode"
    },
    "relation": {
      "type": "string",
      "description": "Semantic relationship type, e.g., 'depends_on', 'causes', 'leads_to', 'part_of', 'references'"
    },
    "directed": {
      "type": "boolean",
      "default": true
    },
    "source_ids": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1,
      "description": "Non-empty array of transcript segment IDs providing factual basis for this relationship."
    }
  },
  "required": ["id", "source", "target", "relation", "source_ids"]
}
```

---

## 3. Diagram Instruction Package

Communication unit emitted by the semantic layer to the JavaScript bridge.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "InstructionPackage",
  "type": "object",
  "properties": {
    "package_id": {
      "type": "string"
    },
    "mode": {
      "type": "string",
      "enum": ["mode_a_ideas", "mode_b_direction"]
    },
    "originating_sources": {
      "type": "array",
      "items": { "type": "string" }
    },
    "operations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "action": {
            "type": "string",
            "enum": [
              "ADD_NODE",
              "UPDATE_NODE",
              "REMOVE_NODE",
              "ADD_EDGE",
              "REMOVE_EDGE",
              "MOVE_NODE",
              "CLUSTER_NODES",
              "APPLY_TEMPLATE"
            ]
          },
          "payload": {
            "type": "object"
          }
        },
        "required": ["action", "payload"]
      }
    }
  },
  "required": ["package_id", "mode", "originating_sources", "operations"]
}
```

---

## 4. Standard Structural Templates (Mode B)

When the user requests structured diagrams, standard scaffolding may be used. Factual causes remain empty placeholders until the user provides statements.

### 4.1 Ishikawa (Fishbone) 6M Template Definition
```json
{
  "template_id": "ishikawa_6m",
  "name": "Ishikawa Diagram (6M)",
  "head": {
    "label": "Problem Statement",
    "is_placeholder": true
  },
  "branches": [
    { "category_id": "b-man", "label": "Man", "type": "template_branch", "source_ids": [] },
    { "category_id": "b-machine", "label": "Machine", "type": "template_branch", "source_ids": [] },
    { "category_id": "b-method", "label": "Method", "type": "template_branch", "source_ids": [] },
    { "category_id": "b-material", "label": "Material", "type": "template_branch", "source_ids": [] },
    { "category_id": "b-measurement", "label": "Measurement", "type": "template_branch", "source_ids": [] },
    { "category_id": "b-mother-nature", "label": "Mother Nature / Environment", "type": "template_branch", "source_ids": [] }
  ],
  "leaves": []
}
```

---

## 5. JavaScript Bridge & diagrams.net Protocol

### 5.1 Host Window to diagrams.net IFrame (`window.postMessage`)

#### Merge XML Operation (Incremental Canvas Update)
```json
{
  "action": "merge",
  "xml": "<mxGraphModel><root><mxCell id=\"node-1\" value=\"Semantic interpretation\" vertex=\"1\" parent=\"1\"><mxGeometry x=\"100\" y=\"100\" width=\"140\" height=\"60\" as=\"geometry\"/></mxCell></root></mxGraphModel>"
}
```

#### Template Load Operation (Initial or full diagram load)
```json
{
  "action": "load",
  "xml": "<mxGraphModel>...</mxGraphModel>",
  "autosave": 1
}
```

### 5.2 diagrams.net IFrame to Host Window Feedback
When diagrams.net changes state or completes an action, it emits JSON payloads back:
```json
{
  "event": "save",
  "xml": "<mxGraphModel>...</mxGraphModel>"
}
```
Or initialization handshake:
```json
{
  "event": "init"
}
```
