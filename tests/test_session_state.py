"""Unit tests for CanvasSessionState and deletion lifecycles."""

import unittest
from src.canvas.session_state import CanvasSessionState


class TestCanvasSessionState(unittest.TestCase):
    def setUp(self):
        self.state = CanvasSessionState()

    def test_incremental_addition_and_deletion(self):
        semantic_1 = {
            "mode": "mode_a_ideas",
            "clusters": [{"id": "c-steps", "label": "Process Steps"}],
            "concepts": [
                {"id": "node-s1", "label": "Step 1", "type": "process_step", "cluster_id": "c-steps", "source_ids": ["s-1"]},
                {"id": "node-s2", "label": "Step 2", "type": "process_step", "cluster_id": "c-steps", "source_ids": ["s-1"]},
            ],
            "relationships": [
                {"id": "rel-1", "source": "node-s1", "target": "node-s2", "relation_type": "leads_to", "source_ids": ["s-1"]}
            ],
            "direct_actions": [],
        }

        # 1. First turn: 2 nodes and 1 edge added
        canvas_json = self.state.sync_from_semantic(semantic_1)
        self.assertEqual(len(canvas_json["nodes"]), 2)
        self.assertEqual(len(canvas_json["edges"]), 1)
        self.assertEqual(len(canvas_json["visual_clusters"]), 1)

        # 2. Second turn: User commands deletion of Step 1
        semantic_2 = {
            "mode": "mode_b_direction",
            "clusters": [{"id": "c-steps", "label": "Process Steps"}],
            "concepts": [
                {"id": "node-s2", "label": "Step 2", "type": "process_step", "cluster_id": "c-steps", "source_ids": ["s-1"]},
            ],
            "relationships": [],
            "direct_actions": [
                {"action": "delete", "target_ids": ["Step 1"]}
            ],
        }

        canvas_json_2 = self.state.sync_from_semantic(semantic_2)

        # Step 1 must be gone
        node_labels = [n["label"] for n in canvas_json_2["nodes"]]
        self.assertNotIn("Step 1", node_labels)
        self.assertIn("Step 2", node_labels)

        # Dangling edge attached to Step 1 must be automatically cleaned
        self.assertEqual(len(canvas_json_2["edges"]), 0)

        # Verify command lifecycle: marked DONE and expired
        self.assertTrue(len(self.state.action_history) > 0)
        last_action = self.state.action_history[-1]
        self.assertEqual(last_action["action"], "delete")
        self.assertEqual(last_action["status"], "DONE")
        self.assertTrue(last_action["expired"])
        self.assertIn("node-s1", last_action["resolved_deleted_ids"])


if __name__ == "__main__":
    unittest.main()
