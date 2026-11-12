"""Unit tests for local session state disk persistence."""

import json
import tempfile
import unittest
from pathlib import Path

from src.canvas.session_state import CanvasSessionState


class TestSessionPersistence(unittest.TestCase):
    def test_save_and_load_session_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "data" / "session_state.json"

            state = CanvasSessionState()
            state.clusters["c1"] = {"id": "c1", "label": "Backend Cluster"}
            state.nodes["n1"] = {"id": "n1", "label": "Auth API", "cluster_id": "c1", "geometry": {"x": 50, "y": 50, "width": 160, "height": 60}}
            state.edges["e1"] = {"id": "e1", "source": "n1", "target": "n2", "relation_type": "leads_to"}
            state.last_xml = "<mxGraphModel><root><mxCell id='n1'/></root></mxGraphModel>"
            state.saved_segments = [{"id": "s-1", "text": "Deploy Auth API", "timestamp_start": 0.0, "timestamp_end": 2.0}]

            # 1. Save to disk
            state.save_to_disk(save_path)
            self.assertTrue(save_path.is_file())

            # 2. Load into a fresh session instance
            new_state = CanvasSessionState()
            loaded = new_state.load_from_disk(save_path)
            self.assertTrue(loaded)
            self.assertIn("c1", new_state.clusters)
            self.assertIn("n1", new_state.nodes)
            self.assertIn("e1", new_state.edges)
            self.assertEqual(new_state.last_xml, state.last_xml)
            self.assertEqual(len(new_state.saved_segments), 1)

            # 3. Clear disk
            new_state.clear_disk(save_path)
            self.assertFalse(save_path.is_file())


if __name__ == "__main__":
    unittest.main()
