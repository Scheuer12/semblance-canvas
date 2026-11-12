"""Canvas Session State Manager for Semblance Canvas.

Maintains the persistent visual graph across multi-turn speech interactions.
Handles incremental additions, updates, deletions, and command lifecycle (DONE/expired).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class CanvasSessionState:
    """Manages persistent canvas state and mutation lifecycles."""

    def __init__(self):
        self.layout_style: str = "clustered_freeform"
        self.canvas_width: int = 1200
        self.canvas_height: int = 800
        self.clusters: Dict[str, Dict[str, Any]] = {}
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[str, Dict[str, Any]] = {}
        self.action_history: List[Dict[str, Any]] = []
        self.last_xml: str = ""
        self.saved_segments: List[Dict[str, Any]] = []

    def reset(self):
        """Resets the canvas state to empty."""
        self.clusters.clear()
        self.nodes.clear()
        self.edges.clear()
        self.action_history.clear()
        self.last_xml = ""
        self.saved_segments.clear()

    def save_to_disk(self, filepath: Path | str):
        """Persists session state to a JSON file on disk."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "saved_at": datetime.datetime.now().isoformat(),
            "layout_style": self.layout_style,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "clusters": self.clusters,
            "nodes": self.nodes,
            "edges": self.edges,
            "action_history": self.action_history,
            "last_xml": self.last_xml,
            "saved_segments": self.saved_segments,
        }
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_from_disk(self, filepath: Path | str) -> bool:
        """Restores state from disk. Returns True if restored, False otherwise."""
        target = Path(filepath)
        if not target.is_file():
            return False
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            self.layout_style = data.get("layout_style", "clustered_freeform")
            self.canvas_width = data.get("canvas_width", 1200)
            self.canvas_height = data.get("canvas_height", 800)
            self.clusters = data.get("clusters", {})
            self.nodes = data.get("nodes", {})
            self.edges = data.get("edges", {})
            self.action_history = data.get("action_history", [])
            self.last_xml = data.get("last_xml", "")
            self.saved_segments = data.get("saved_segments", [])
            return True
        except Exception as e:
            print(f"[SessionState] Failed to restore from {filepath}: {e}")
            return False

    def clear_disk(self, filepath: Path | str):
        """Deletes persistent save file from disk."""
        target = Path(filepath)
        if target.is_file():
            try:
                target.unlink()
            except Exception:
                pass

    def apply_deletion(self, target_ids: List[str], reason: str = "") -> List[str]:
        """Removes nodes, clusters, and connected edges matching target_ids or labels."""
        deleted_ids: List[str] = []
        now_iso = datetime.datetime.now().isoformat()

        targets_lower = {t.lower().strip() for t in target_ids if t}

        # 1. Check nodes (by ID or matching label)
        nodes_to_remove = set()
        for nid, node in self.nodes.items():
            n_label = (node.get("label") or "").lower().strip()
            if nid.lower() in targets_lower or n_label in targets_lower or any(t in n_label for t in targets_lower):
                nodes_to_remove.add(nid)

        for nid in nodes_to_remove:
            del self.nodes[nid]
            deleted_ids.append(nid)

        # 2. Check clusters (by ID or label)
        clusters_to_remove = set()
        for cid, cluster in self.clusters.items():
            c_label = (cluster.get("label") or "").lower().strip()
            if cid.lower() in targets_lower or c_label in targets_lower or any(t in c_label for t in targets_lower):
                clusters_to_remove.add(cid)

        for cid in clusters_to_remove:
            del self.clusters[cid]
            deleted_ids.append(cid)
            # Also remove orphan nodes belonging to deleted cluster
            orphan_nodes = [nid for nid, node in self.nodes.items() if node.get("cluster_id") == cid]
            for nid in orphan_nodes:
                del self.nodes[nid]
                deleted_ids.append(nid)

        # 3. Clean up dangling edges attached to removed nodes
        edges_to_remove = set()
        for eid, edge in self.edges.items():
            if edge.get("source") in deleted_ids or edge.get("target") in deleted_ids:
                edges_to_remove.add(eid)

        for eid in edges_to_remove:
            del self.edges[eid]
            deleted_ids.append(eid)

        # 4. Record action in lifecycle history as DONE and EXPIRED
        self.action_history.append({
            "action": "delete",
            "targets": target_ids,
            "resolved_deleted_ids": deleted_ids,
            "reason": reason,
            "status": "DONE",
            "timestamp": now_iso,
            "expired": True,
        })

        return deleted_ids

    def sync_from_semantic(self, semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reconciles persistent state against new semantic extraction, processing commands."""
        now_iso = datetime.datetime.now().isoformat()

        # Process explicit direct actions (e.g. deletions, reorganization)
        for act in semantic_data.get("direct_actions", []):
            action_name = (act.get("action") or "").lower()
            if any(k in action_name for k in ("delete", "remov", "exclui")):
                target_ids = act.get("target_ids", [])
                self.apply_deletion(target_ids, reason="Direct action from speech")
            else:
                self.action_history.append({
                    "action": action_name,
                    "targets": act.get("target_ids", []),
                    "status": "DONE",
                    "timestamp": now_iso,
                    "expired": True,
                })

        # Sync clusters
        current_cluster_ids = set()
        for c in semantic_data.get("clusters", []):
            cid = c.get("id")
            if not cid:
                continue
            current_cluster_ids.add(cid)
            if cid not in self.clusters:
                self.clusters[cid] = {
                    "id": cid,
                    "label": c.get("label", cid),
                    "bounds": {"x": 60, "y": 60, "width": 450, "height": 240},
                    "style": "swimlane;startSize=25;rounded=1;fillColor=#F1F5F9;strokeColor=#94A3B8;fontStyle=1;",
                }
            else:
                self.clusters[cid]["label"] = c.get("label", self.clusters[cid]["label"])

        # Sync concepts (nodes)
        semantic_concept_ids = set()
        for concept in semantic_data.get("concepts", []):
            nid = concept.get("id")
            if not nid:
                continue
            semantic_concept_ids.add(nid)
            label = concept.get("label", nid)
            c_type = concept.get("type", "concept")
            cluster_id = concept.get("cluster_id")
            sources = concept.get("source_ids", [])

            if nid not in self.nodes:
                # Assign default starting layout position if new
                idx = len(self.nodes)
                col = idx % 3
                row = idx // 3
                x_pos = 90 + (col * 220)
                y_pos = 120 + (row * 100)

                self.nodes[nid] = {
                    "id": nid,
                    "label": label,
                    "type": c_type,
                    "cluster_id": cluster_id,
                    "geometry": {"x": x_pos, "y": y_pos, "width": 180, "height": 60},
                    "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;fontStyle=1;",
                    "source_ids": sources,
                }
            else:
                # Update existing node attributes
                self.nodes[nid]["label"] = label
                self.nodes[nid]["cluster_id"] = cluster_id
                self.nodes[nid]["source_ids"] = list(set(self.nodes[nid].get("source_ids", []) + sources))

        # Sync explicit relationships (edges)
        semantic_rel_ids = set()
        for rel in semantic_data.get("relationships", []):
            eid = rel.get("id")
            src = rel.get("source")
            tgt = rel.get("target")
            if not eid or not src or not tgt:
                continue

            # Only include edge if both endpoints exist in our active nodes
            if src in self.nodes and tgt in self.nodes:
                semantic_rel_ids.add(eid)
                self.edges[eid] = {
                    "id": eid,
                    "source": src,
                    "target": tgt,
                    "relation_type": rel.get("relation_type", "leads_to"),
                    "label": rel.get("label", ""),
                    "show_label": False,  # Graphical-first: avoid text overlap
                    "directed": rel.get("directed", True),
                    "source_ids": rel.get("source_ids", []),
                }

        # If semantic extraction completely purged concepts previously in session
        # (e.g. user commanded full replacement or deletion in conversation context):
        if semantic_data.get("mode") == "mode_b_direction" or "delete" in [a.get("action") for a in semantic_data.get("direct_actions", [])]:
            missing_nodes = [nid for nid in list(self.nodes.keys()) if nid not in semantic_concept_ids]
            if missing_nodes:
                self.apply_deletion(missing_nodes, reason="Omitted in updated semantic model")

        return self.to_canvas_json()

    def to_canvas_json(self) -> Dict[str, Any]:
        """Returns the clean, consolidated Canvas JSON ready for rendering."""
        return {
            "canvas_metadata": {
                "layout_style": self.layout_style,
                "canvas_width": self.canvas_width,
                "canvas_height": self.canvas_height,
            },
            "visual_clusters": list(self.clusters.values()),
            "nodes": list(self.nodes.values()),
            "edges": list(self.edges.values()),
        }
