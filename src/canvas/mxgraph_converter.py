"""Converts Semblance Canvas JSON into diagrams.net / mxGraph XML.

Includes deterministic layout stabilization:
- Automatic cluster bounding-box reconciliation (prevents cards from overflowing containers).
- Overlap avoidance & clearance enforcement.
- Orthogonal line-jumping (jumpStyle=arc) to cleanly disambiguate crossed edges.
"""

from __future__ import annotations

import copy
import html
from typing import Any, Dict, List


def reconcile_layout_geometry(canvas_data: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically prevents node collisions and resizes visual cluster containers."""
    data = copy.deepcopy(canvas_data)
    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    clusters: List[Dict[str, Any]] = data.get("visual_clusters", [])

    # 1. Resolve node overlaps within same cluster / freeform plane
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            n1 = nodes[i]
            n2 = nodes[j]
            g1 = n1.get("geometry", {})
            g2 = n2.get("geometry", {})

            x1, y1 = g1.get("x", 100), g1.get("y", 100)
            w1, h1 = g1.get("width", 160), g1.get("height", 60)

            x2, y2 = g2.get("x", 100), g2.get("y", 100)
            w2, h2 = g2.get("width", 160), g2.get("height", 60)

            # Check bounding box intersection with 20px buffer
            overlap_x = (x1 < x2 + w2 + 20) and (x1 + w1 + 20 > x2)
            overlap_y = (y1 < y2 + h2 + 20) and (y1 + h1 + 20 > y2)

            if overlap_x and overlap_y:
                # Nudge n2 downward to clear overlap
                g2["y"] = y1 + h1 + 30
                n2["geometry"] = g2

    # 2. Dynamically compute container bounding boxes to enclose all member nodes
    for cluster in clusters:
        cid = cluster["id"]
        members = [n for n in nodes if n.get("cluster_id") == cid]

        if members:
            min_x = min(n["geometry"]["x"] for n in members)
            min_y = min(n["geometry"]["y"] for n in members)
            max_x = max(n["geometry"]["x"] + n["geometry"].get("width", 160) for n in members)
            max_y = max(n["geometry"]["y"] + n["geometry"].get("height", 60) for n in members)

            pad_x = 30
            pad_top = 45   # Room for swimlane title bar
            pad_bottom = 30

            cluster["bounds"] = {
                "x": min_x - pad_x,
                "y": min_y - pad_top,
                "width": max((max_x - min_x) + (pad_x * 2), 220),
                "height": max((max_y - min_y) + pad_top + pad_bottom, 140),
            }

    return data


def canvas_json_to_mxgraph_xml(canvas_data: Dict[str, Any]) -> str:
    """Serializes Canvas JSON into valid mxGraphModel XML for diagrams.net."""
    # Apply deterministic spatial and bounds stabilization
    stabilized_data = reconcile_layout_geometry(canvas_data)
    cells_xml = []

    # 1. Root cells required by mxGraph
    cells_xml.append('<mxCell id="0"/>')
    cells_xml.append('<mxCell id="1" parent="0"/>')

    # 2. Visual Clusters (Containers)
    for cluster in stabilized_data.get("visual_clusters", []):
        cid = cluster["id"]
        label = html.escape(cluster.get("label", ""))
        bounds = cluster.get("bounds", {"x": 50, "y": 50, "width": 400, "height": 300})
        style = cluster.get(
            "style",
            "swimlane;startSize=25;rounded=1;collapsible=0;fillColor=#F5F5F5;strokeColor=#B0B0B0;fontStyle=1;",
        )
        bx = bounds.get("x", 50)
        by = bounds.get("y", 50)
        bw = bounds.get("width", 400)
        bh = bounds.get("height", 300)

        cell = (
            f'<mxCell id="{cid}" value="{label}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{bx}" y="{by}" width="{bw}" height="{bh}" as="geometry"/>'
            f'</mxCell>'
        )
        cells_xml.append(cell)

    # 3. Concept Nodes
    for node in stabilized_data.get("nodes", []):
        nid = node["id"]
        label = html.escape(node.get("label", ""))
        geom = node.get("geometry", {"x": 100, "y": 100, "width": 160, "height": 60})
        style = node.get(
            "style",
            "rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;",
        )
        gx = geom.get("x", 100)
        gy = geom.get("y", 100)
        gw = geom.get("width", 160)
        gh = geom.get("height", 60)
        parent_id = "1"

        cell = (
            f'<mxCell id="{nid}" value="{label}" style="{style}" vertex="1" parent="{parent_id}">'
            f'<mxGeometry x="{gx}" y="{gy}" width="{gw}" height="{gh}" as="geometry"/>'
            f'</mxCell>'
        )
        cells_xml.append(cell)

    # 4. Edges (Prioritize Graphical Distinctions + jumpStyle=arc to cleanly handle line crossings)
    for edge in stabilized_data.get("edges", []):
        eid = edge["id"]
        source_id = edge["source"]
        target_id = edge["target"]
        raw_label = edge.get("label", "")
        rel_type = edge.get("relation_type", "").lower()
        base_style = edge.get("style", "")

        # Base orthogonal routing with arc jumping to avoid ambiguity on intersecting lines
        jump_opts = "jumpStyle=arc;jumpSize=8;targetPerimeterSpacing=4;sourcePerimeterSpacing=4;"

        if any(k in rel_type for k in ("depend", "require", "need")):
            # Dashed indigo line with solid block arrow (Requirement / Dependency)
            style = f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;dashed=1;dashPattern=6 6;strokeColor=#6366F1;strokeWidth=2;endArrow=block;{jump_opts}"
        elif any(k in rel_type for k in ("cause", "lead", "trigger", "create", "generat", "send", "receiv")):
            # Solid blue classic arrow (Action / Flow / Transition)
            style = f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#2563EB;strokeWidth=2;endArrow=classic;{jump_opts}"
        elif any(k in rel_type for k in ("part_of", "belong", "contain")):
            # Emerald line with diamond marker (Composition / Membership)
            style = f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#059669;strokeWidth=2;endArrow=diamond;endFill=1;{jump_opts}"
        elif base_style:
            style = f"{base_style};{jump_opts}"
        else:
            style = f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#64748B;strokeWidth=1.5;endArrow=block;{jump_opts}"

        # Graphical-first rule: keep edge value empty unless explicitly marked,
        # preventing verbose text labels from colliding with neighboring cards.
        label = ""
        if edge.get("show_label", False) and raw_label:
            label = html.escape(raw_label)
            style += "labelBackgroundColor=#FFFFFF;rounded=1;"

        cell = (
            f'<mxCell id="{eid}" value="{label}" style="{style}" edge="1" parent="1" source="{source_id}" target="{target_id}">'
            f'<mxGeometry relative="1" as="geometry"/>'
            f'</mxCell>'
        )
        cells_xml.append(cell)

    root_content = "".join(cells_xml)
    return f"<mxGraphModel><root>{root_content}</root></mxGraphModel>"
