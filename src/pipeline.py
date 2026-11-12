"""End-to-End Speech-to-Canvas Pipeline.

Listens to speech (or receives simulated transcripts), passes segments through
Skill 1 (Text -> Semantic JSON) and Skill 2 (Semantic JSON -> Canvas JSON),
and converts the output to diagrams.net mxGraph XML.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import List, Optional

from src.ai import SkillRunner, get_ai_client
from src.audio import RealtimeVoiceTranscriber, SourceSegment
from src.canvas import canvas_json_to_mxgraph_xml
from src.config import config


class SpeechToCanvasPipeline:
    def __init__(self, ai_backend: Optional[str] = None):
        cfg = config.ai
        if ai_backend:
            cfg.backend = ai_backend
        self.ai_client = get_ai_client(cfg)
        self.skill_runner = SkillRunner(ai_client=self.ai_client)
        self.accumulated_segments: List[SourceSegment] = []

    def process_segments(self, segments: List[SourceSegment]) -> dict:
        """Runs Skill 1 and Skill 2 over the provided segments."""
        print(f"\n[Pipeline] Processing {len(segments)} transcript segments...")
        for s in segments:
            print(f"  [{s.id}] {s.text}")

        # Step 1: Skill 1 (Text -> Semantic JSON)
        print("\n[Pipeline] Running Skill 1: text_to_semantic_json...")
        semantic_json = self.skill_runner.run_text_to_semantic(segments)
        print("[Pipeline] Semantic JSON Output:")
        print(json.dumps(semantic_json, indent=2))

        # Step 2: Skill 2 (Semantic JSON -> Canvas JSON)
        print("\n[Pipeline] Running Skill 2: semantic_json_to_canvas_json...")
        canvas_json = self.skill_runner.run_semantic_to_canvas(semantic_json)
        print("[Pipeline] Canvas JSON Output:")
        print(json.dumps(canvas_json, indent=2))

        # Step 3: Format diagrams.net XML
        mxgraph_xml = canvas_json_to_mxgraph_xml(canvas_json)
        print("\n[Pipeline] diagrams.net mxGraph XML:")
        print(mxgraph_xml[:400] + ("..." if len(mxgraph_xml) > 400 else ""))

        return {
            "semantic_json": semantic_json,
            "canvas_json": canvas_json,
            "mxgraph_xml": mxgraph_xml,
        }

    def on_stt_segment(self, segment: SourceSegment) -> None:
        """Callback triggered on every newly transcribed speech segment."""
        self.accumulated_segments.append(segment)
        try:
            self.process_segments(self.accumulated_segments)
        except Exception as e:
            print(f"[Pipeline] Processing error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Semblance Canvas Pipeline")
    parser.add_argument("--backend", choices=["antigravity_cli", "gemini_cli", "google_genai", "mock"], default=None,
                        help="AI backend (defaults to config.json)")
    parser.add_argument("--simulate", action="store_true", help="Interactive text simulation mode")
    parser.add_argument("--demo", action="store_true", help="Run with built-in demo phrases")
    args = parser.parse_args()

    pipeline = SpeechToCanvasPipeline(ai_backend=args.backend)

    if args.demo:
        demo_segments = [
            SourceSegment(
                id="s-1",
                text="The speech recognition engine feeds audio into the semantic interpreter.",
                timestamp_start=0.0,
                timestamp_end=3.5,
            ),
            SourceSegment(
                id="s-2",
                text="The canvas renderer is also part of the architecture.",
                timestamp_start=4.0,
                timestamp_end=6.2,
            ),
        ]
        pipeline.process_segments(demo_segments)
        return

    if args.simulate:
        transcriber = RealtimeVoiceTranscriber(on_segment=pipeline.on_stt_segment)
        print("\n=== Semblance Canvas Pipeline (Simulation Mode) ===")
        print("Type user speech sentences below. Type 'exit' to quit.\n")
        while True:
            try:
                line = input("Speech > ")
                if not line or line.strip().lower() == "exit":
                    break
                transcriber.simulate_segment(line)
            except (KeyboardInterrupt, EOFError):
                break
        return

    # Real microphone mode
    transcriber = RealtimeVoiceTranscriber(
        language=config.audio.language,
        device_index=config.audio.device_index,
        on_segment=pipeline.on_stt_segment,
    )
    print("\n=== Semblance Canvas Pipeline (Live Microphone Mode) ===")
    print("Listening to your microphone... Press Ctrl+C to stop.")
    try:
        transcriber.start_listening()
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        transcriber.stop_listening()


if __name__ == "__main__":
    main()
