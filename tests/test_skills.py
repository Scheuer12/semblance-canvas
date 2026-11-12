"""Unit tests for Semblance Canvas skills and non-invention guardrails."""

import unittest
from unittest.mock import MagicMock, patch

from src.ai.client import AntigravityCliClient, MockAIClient
from src.config import AIConfig
from src.ai.skill_runner import NonInventionViolationError, SkillExecutionError, SkillRunner
from src.audio.realtime_stt import SourceSegment
from src.canvas.mxgraph_converter import canvas_json_to_mxgraph_xml


class TestSkillsAndGuardrails(unittest.TestCase):
    def setUp(self):
        self.mock_client = MockAIClient()
        self.runner = SkillRunner(ai_client=self.mock_client)

    def test_skill_1_and_skill_2_end_to_end(self):
        segments = [
            SourceSegment(
                id="s-1",
                text="The speech recognition engine feeds audio into the semantic interpreter.",
                timestamp_start=0.0,
                timestamp_end=3.5,
            )
        ]

        # Skill 1: Text -> Semantic JSON
        semantic_data = self.runner.run_text_to_semantic(segments)
        self.assertEqual(semantic_data["mode"], "mode_a_ideas")
        self.assertTrue(len(semantic_data["concepts"]) >= 2)
        for c in semantic_data["concepts"]:
            self.assertIn("s-1", c["source_ids"])

        # Skill 2: Semantic JSON -> Canvas JSON
        canvas_data = self.runner.run_semantic_to_canvas(semantic_data)
        self.assertIn("canvas_metadata", canvas_data)
        self.assertTrue(len(canvas_data["nodes"]) >= 2)

        # mxGraph XML serialization
        xml = canvas_json_to_mxgraph_xml(canvas_data)
        self.assertIn("<mxGraphModel>", xml)
        self.assertIn('mxCell id="node-1"', xml)
        self.assertIn('mxCell id="rel-1"', xml)

    def test_non_invention_violation_flagged_on_phantom_source(self):
        class ViolatingMock(MockAIClient):
            def generate_json(self, prompt, system_instruction=None):
                data = super().generate_json(prompt, system_instruction)
                # Fabricate an unsupported relationship citing phantom source ID
                data["relationships"].append({
                    "id": "rel-hallucinated",
                    "source": "node-1",
                    "target": "node-2",
                    "relation_type": "causes",
                    "source_ids": ["s-999"],  # Cites non-existent transcript segment!
                })
                return data

        bad_runner = SkillRunner(ai_client=ViolatingMock())
        segments = [
            SourceSegment(id="s-1", text="Sample", timestamp_start=0.0, timestamp_end=1.0)
        ]

        with self.assertRaises(NonInventionViolationError):
            bad_runner.run_text_to_semantic(segments)

    def test_schema_validation_catches_empty_source_ids(self):
        class EmptySourceMock(MockAIClient):
            def generate_json(self, prompt, system_instruction=None):
                data = super().generate_json(prompt, system_instruction)
                data["relationships"][0]["source_ids"] = []  # Empty array violates schema minItems=1
                return data

        bad_runner = SkillRunner(ai_client=EmptySourceMock())
        segments = [
            SourceSegment(id="s-1", text="Sample", timestamp_start=0.0, timestamp_end=1.0)
        ]

        with self.assertRaises(SkillExecutionError):
            bad_runner.run_text_to_semantic(segments)


class TestAntigravityCliClient(unittest.TestCase):
    @patch("src.ai.client.subprocess.Popen")
    def test_uses_headless_oauth_cli_without_api_key(self, popen_mock):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdout.readline.side_effect = [
            '{"event":"init","init":{}}\n',
            '{"event":"result","result":{"status":"SUCCESS","response":"{\\"ok\\": true}"}}\n',
        ]
        popen_mock.return_value = mock_proc
        client = AntigravityCliClient(
            AIConfig(
                backend="antigravity_cli",
                antigravity_cli_path="agy",
                model=None,
                cli_timeout_seconds=60,
            )
        )

        result = client.generate_json("Return JSON", "Do not invent facts")

        self.assertEqual(result, {"ok": True})
        args, kwargs = popen_mock.call_args
        command = args[0]
        self.assertEqual(command[0], "agy")
        self.assertIn("--input-format", command)
        self.assertIn("--output-format", command)
        self.assertIn("--disable-slash-commands", command)
        self.assertNotIn("GEMINI_API_KEY", kwargs["env"])


if __name__ == "__main__":
    unittest.main()
