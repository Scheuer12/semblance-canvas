"""Deterministic Layout and Semantic Type Mapping Engine for Semblance Canvas.

Translates logical semantic JSON (Skill 1) into a visually structured Canvas JSON
in < 5ms without requiring a secondary LLM generation pass.

Features:
- Semantic Entity Type Mapping:
  - process_step  -> Rounded blue card (Operational Action / Workflow stage)
  - side_annotation -> Dashed yellow sticky note (Informational note / Caveat)
  - data_store    -> Green cylinder (Spreadsheet / DB / Physical archive)
  - decision_gate -> Yellow diamond (Approval / Conditional branch)
  - actor         -> Purple persona / Role
  - concept       -> Clean indigo rounded card (General entity)
- Multi-Cluster Spatial Separation:
  - Dynamically calculates bounding boxes so cards never escape containers.
  - Places clusters in clean horizontal lanes with wrap-around to prevent container overlap.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List


# Semantic Type -> Visual Style and Dimension Mapping
SEMANTIC_TYPE_STYLES: Dict[str, Dict[str, Any]] = {
    "process_step": {
        "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DBEAFE;strokeColor=#3B82F6;fontColor=#1E3A8A;fontStyle=1;arcSize=14;fontSize=12;",
        "width": 180,
        "height": 60,
    },
    "side_annotation": {
        "style": "shape=note;whiteSpace=wrap;html=1;size=14;verticalAlign=top;align=left;spacingLeft=8;spacingRight=8;spacingTop=6;fillColor=#FEF3C7;strokeColor=#D97706;fontColor=#78350F;dashed=1;dashPattern=4 4;fontSize=11;",
        "width": 170,
        "height": 65,
    },
    "data_store": {
        "style": "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=12;fillColor=#DCFCE7;strokeColor=#16A34A;fontColor=#14532D;fontStyle=1;fontSize=11;",
        "width": 170,
        "height": 65,
    },
    "decision_gate": {
        "style": "rhombus;whiteSpace=wrap;html=1;fillColor=#FEF08A;strokeColor=#CA8A04;fontColor=#713F12;fontStyle=1;fontSize=11;",
        "width": 130,
        "height": 75,
    },
    "actor": {
        "style": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor=#F3E8FF;strokeColor=#9333EA;fontColor=#581C87;fontSize=11;",
        "width": 60,
        "height": 75,
    },
    "concept": {
        "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#EDE9FE;strokeColor=#8B5CF6;fontColor=#4C1D95;fontStyle=1;arcSize=12;fontSize=12;",
        "width": 180,
        "height": 60,
    },
}

# Cluster Container Color Palettes
CLUSTER_PALETTES = [
    {"fill": "#F8FAFC", "stroke": "#64748B", "title": "#334155"},  # Slate
    {"fill": "#F0FDF4", "stroke": "#22C55E", "title": "#15803D"},  # Emerald
    {"fill": "#FEF2F2", "stroke": "#EF4444", "title": "#B91C1C"},  # Rose
    {"fill": "#EFF6FF", "stroke": "#3B82F6", "title": "#1D4ED8"},  # Sky
    {"fill": "#FAF5FF", "stroke": "#A855F7", "title": "#7E22CE"},  # Purple
    {"fill": "#FFFBEB", "stroke": "#F59E0B", "title": "#B45309"},  # Amber
]


def resolve_semantic_type(concept: Dict[str, Any]) -> str:
    """Infers or validates the semantic entity type for graphical type mapping."""
    raw_type = (concept.get("type") or "concept").lower().strip()
    if raw_type in SEMANTIC_TYPE_STYLES:
        return raw_type

    label = (concept.get("label") or "").lower()

    # Heuristic keyword fallback if LLM omitted typed token
    if any(k in label for k in ("observaç", "nota", "aviso", "ainda não existe", "será criado", "imprevisto")):
        return "side_annotation"
    if any(k in label for k in ("planilha", "banco", "tabela", "backlog", "repositório", "store", "galpão")):
        return "data_store"
    if any(k in label for k in ("aprovad", "decisão", "verificar se", "condição", "gateway", "liberad")):
        return "decision_gate"
    if any(k in label for k in ("gestão de compras", "equipe", "usuário", "cliente", "gerente", "ator")):
        return "actor"
    if any(k in label for k in ("ordem", "verificar", "execut", "início", "inicia", "conclus", "gerar")):
        return "process_step"

    return "concept"


def compute_deterministic_canvas_layout(semantic_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generates complete Canvas JSON with spatial coordinates in < 5ms."""
    concepts: List[Dict[str, Any]] = copy.deepcopy(semantic_data.get("concepts", []))
    raw_clusters: List[Dict[str, Any]] = copy.deepcopy(semantic_data.get("clusters", []))
    relationships: List[Dict[str, Any]] = copy.deepcopy(semantic_data.get("relationships", []))

    cluster_map: Dict[str, Dict[str, Any]] = {c["id"]: c for c in raw_clusters if "id" in c}

    # Group concepts by cluster
    clustered_nodes: Dict[str, List[Dict[str, Any]]] = {}
    unclustered_nodes: List[Dict[str, Any]] = []

    for c in concepts:
        cid = c.get("cluster_id")
        if cid and cid in cluster_map:
            clustered_nodes.setdefault(cid, []).append(c)
        else:
            unclustered_nodes.append(c)

    layout_nodes: List[Dict[str, Any]] = []
    layout_clusters: List[Dict[str, Any]] = []

    curr_cluster_x = 60
    curr_cluster_y = 60
    max_row_height = 0
    max_canvas_x = 1200

    # 1. Position Clustered Nodes & Compute Container Bounding Boxes
    for idx, (cid, members) in enumerate(clustered_nodes.items()):
        palette = CLUSTER_PALETTES[idx % len(CLUSTER_PALETTES)]
        cluster_meta = cluster_map[cid]

        # Calculate nodes inside cluster
        cols_per_row = 3 if len(members) >= 3 else len(members)
        if cols_per_row == 0:
            cols_per_row = 1

        node_pad_x = 30
        node_pad_top = 50
        col_spacing = 210
        row_spacing = 95

        c_min_x = curr_cluster_x + node_pad_x
        c_min_y = curr_cluster_y + node_pad_top

        member_bounds = []

        for m_idx, node in enumerate(members):
            s_type = resolve_semantic_type(node)
            type_style = SEMANTIC_TYPE_STYLES[s_type]

            col = m_idx % cols_per_row
            row = m_idx // cols_per_row

            gx = c_min_x + (col * col_spacing)
            gy = c_min_y + (row * row_spacing)
            gw = type_style["width"]
            gh = type_style["height"]

            node["type"] = s_type
            node["style"] = type_style["style"]
            node["geometry"] = {"x": gx, "y": gy, "width": gw, "height": gh}
            layout_nodes.append(node)
            member_bounds.append((gx, gy, gw, gh))

        # Enclosing cluster bounding box
        if member_bounds:
            max_right = max(bx + bw for bx, by, bw, bh in member_bounds)
            max_bottom = max(by + bh for bx, by, bw, bh in member_bounds)
            c_width = (max_right - curr_cluster_x) + 30
            c_height = (max_bottom - curr_cluster_y) + 30
        else:
            c_width = 300
            c_height = 150

        # Cluster Style with colored swimlane title
        cluster_style = (
            f"swimlane;startSize=26;rounded=1;collapsible=0;"
            f"fillColor={palette['fill']};strokeColor={palette['stroke']};"
            f"fontColor={palette['title']};fontStyle=1;fontSize=12;"
        )

        layout_clusters.append({
            "id": cid,
            "label": cluster_meta.get("label", cid),
            "bounds": {
                "x": curr_cluster_x,
                "y": curr_cluster_y,
                "width": max(c_width, 240),
                "height": max(c_height, 140),
            },
            "style": cluster_style,
        })

        max_row_height = max(max_row_height, c_height)
        curr_cluster_x += max(c_width, 240) + 40

        # Wrap to next row if canvas exceeds boundary
        if curr_cluster_x > max_canvas_x and (idx + 1) < len(clustered_nodes):
            curr_cluster_x = 60
            curr_cluster_y += max_row_height + 40
            max_row_height = 0

    # 2. Position Unclustered Nodes (Below Clusters)
    if unclustered_nodes:
        unclustered_y = curr_cluster_y + max_row_height + 40
        unclustered_x = 60

        for u_idx, node in enumerate(unclustered_nodes):
            s_type = resolve_semantic_type(node)
            type_style = SEMANTIC_TYPE_STYLES[s_type]

            node["type"] = s_type
            node["style"] = type_style["style"]
            node["geometry"] = {
                "x": unclustered_x + (u_idx * 210),
                "y": unclustered_y,
                "width": type_style["width"],
                "height": type_style["height"],
            }
            layout_nodes.append(node)

    # 3. Clean Edges
    edges: List[Dict[str, Any]] = []
    for rel in relationships:
        edges.append({
            "id": rel.get("id"),
            "source": rel.get("source"),
            "target": rel.get("target"),
            "relation_type": rel.get("relation_type", "leads_to"),
            "label": rel.get("label", ""),
            "show_label": False,
            "directed": rel.get("directed", True),
            "source_ids": rel.get("source_ids", []),
        })

    return {
        "canvas_metadata": {
            "layout_style": "deterministic_type_mapping",
            "canvas_width": 1600,
            "canvas_height": 1200,
        },
        "visual_clusters": layout_clusters,
        "nodes": layout_nodes,
        "edges": edges,
    }
