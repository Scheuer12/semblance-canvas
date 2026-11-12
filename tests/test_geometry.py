"""Unit tests for deterministic layout stabilization and bounds reconciliation."""

import unittest
from src.canvas.mxgraph_converter import canvas_json_to_mxgraph_xml, reconcile_layout_geometry


class TestLayoutGeometryStabilization(unittest.TestCase):
    def test_container_expands_to_enclose_overflowing_node(self):
        canvas_data = {
            "visual_clusters": [
                {
                    "id": "c-proc",
                    "label": "Processo de Compras",
                    "bounds": {"x": 50, "y": 50, "width": 300, "height": 180},
                }
            ],
            "nodes": [
                # Node positioned way below original cluster height (y=260 > 180)
                {
                    "id": "n-batch",
                    "label": "Ordens em Blocos",
                    "cluster_id": "c-proc",
                    "geometry": {"x": 70, "y": 260, "width": 160, "height": 60},
                }
            ],
            "edges": [],
        }

        stabilized = reconcile_layout_geometry(canvas_data)
        cluster = stabilized["visual_clusters"][0]
        node = stabilized["nodes"][0]

        # The cluster bounds must now strictly enclose the node with padding
        c_x = cluster["bounds"]["x"]
        c_y = cluster["bounds"]["y"]
        c_w = cluster["bounds"]["width"]
        c_h = cluster["bounds"]["height"]

        n_x = node["geometry"]["x"]
        n_y = node["geometry"]["y"]
        n_w = node["geometry"]["width"]
        n_h = node["geometry"]["height"]

        self.assertLessEqual(c_x, n_x)
        self.assertLessEqual(c_y, n_y)
        self.assertGreaterEqual(c_x + c_w, n_x + n_w)
        self.assertGreaterEqual(c_y + c_h, n_y + n_h)

    def test_overlapping_nodes_are_nudged_downward(self):
        canvas_data = {
            "visual_clusters": [],
            "nodes": [
                {"id": "n1", "label": "Node 1", "geometry": {"x": 100, "y": 100, "width": 160, "height": 60}},
                {"id": "n2", "label": "Node 2", "geometry": {"x": 105, "y": 110, "width": 160, "height": 60}},  # Heavy overlap
            ],
            "edges": [],
        }

        stabilized = reconcile_layout_geometry(canvas_data)
        n1 = stabilized["nodes"][0]
        n2 = stabilized["nodes"][1]

        # n2 must have been nudged below n1
        self.assertGreaterEqual(n2["geometry"]["y"], n1["geometry"]["y"] + n1["geometry"]["height"])

    def test_edges_contain_jump_arc_style(self):
        canvas_data = {
            "visual_clusters": [],
            "nodes": [
                {"id": "n1", "label": "A", "geometry": {"x": 100, "y": 100, "width": 100, "height": 50}},
                {"id": "n2", "label": "B", "geometry": {"x": 300, "y": 100, "width": 100, "height": 50}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "relation_type": "leads_to", "source_ids": ["s-1"]}
            ],
        }

        xml = canvas_json_to_mxgraph_xml(canvas_data)
        self.assertIn("jumpStyle=arc", xml)
        self.assertIn("jumpSize=8", xml)

    def test_deterministic_de_para_layout(self):
        from src.canvas.deterministic_layout import compute_deterministic_canvas_layout

        semantic_data = {
            "mode": "mode_a_ideas",
            "clusters": [{"id": "c1", "label": "Pipeline"}],
            "concepts": [
                {"id": "step1", "label": "Verificar Escopo", "type": "process_step", "cluster_id": "c1", "source_ids": ["s-1"]},
                {"id": "note1", "label": "Aviso Importante", "type": "side_annotation", "cluster_id": "c1", "source_ids": ["s-1"]},
                {"id": "db1", "label": "Planilha de Gestão", "type": "data_store", "cluster_id": "c1", "source_ids": ["s-1"]},
            ],
            "relationships": [
                {"id": "r1", "source": "step1", "target": "db1", "relation_type": "leads_to", "source_ids": ["s-1"]}
            ],
        }

        canvas_json = compute_deterministic_canvas_layout(semantic_data)
        self.assertEqual(len(canvas_json["nodes"]), 3)
        self.assertEqual(len(canvas_json["visual_clusters"]), 1)

        nodes = {n["id"]: n for n in canvas_json["nodes"]}
        # Verify De-Para styling
        self.assertIn("fillColor=#DBEAFE", nodes["step1"]["style"])
        self.assertIn("shape=note", nodes["note1"]["style"])
        self.assertIn("shape=cylinder3", nodes["db1"]["style"])

        # Verify cluster bounds strictly enclose all nodes
        cluster = canvas_json["visual_clusters"][0]
        self.assertGreater(cluster["bounds"]["width"], 200)
        self.assertGreater(cluster["bounds"]["height"], 100)


if __name__ == "__main__":
    unittest.main()
