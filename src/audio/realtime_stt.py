"""Real-Time Voice-to-Text Transcriber with Monotonic Provenance Tracking.

Captures speech from the microphone in real time, applies ambient noise calibration,
transcribes segments, and tags each utterance with an immutable provenance ID (s-1, s-2, ...).
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
from dataclasses import asdict, dataclass
from typing import Callable, List, Optional

try:
    import speech_recognition as sr
except ImportError:
    sr = None  # Handled gracefully in Transcriber


@dataclass
class SourceSegment:
    """Transcript segment carrying strict factual provenance."""
    id: str
    text: str
    timestamp_start: float
    timestamp_end: float
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


class RealtimeVoiceTranscriber:
    """Manages continuous audio capture, VAD/segmentation, and transcription."""

    def __init__(
        self,
        language: str = "en-US",
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
        phrase_time_limit: float = 15.0,
        device_index: Optional[int] = None,
        on_segment: Optional[Callable[[SourceSegment], None]] = None,
    ):
        self.language = language
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.phrase_time_limit = phrase_time_limit
        self.device_index = device_index
        self.on_segment = on_segment

        self._counter = 0
        self._counter_lock = threading.Lock()
        self._session_start_time = time.time()
        self._is_running = False
        self._stop_listening_fn: Optional[Callable] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None

        if sr is not None:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = self.energy_threshold
            self.recognizer.pause_threshold = self.pause_threshold
            self.recognizer.dynamic_energy_threshold = True
        else:
            self.recognizer = None

    @staticmethod
    def list_microphones() -> List[str]:
        """List available audio input devices."""
        if sr is None:
            return []
        try:
            return sr.Microphone.list_microphone_names()
        except Exception as e:
            print(f"[Audio] Error listing microphones: {e}")
            return []

    def _next_segment_id(self) -> str:
        with self._counter_lock:
            self._counter += 1
            return f"s-{self._counter}"

    def start_listening(self) -> None:
        """Starts real-time continuous background listening."""
        if sr is None:
            raise RuntimeError(
                "SpeechRecognition package is not installed. Run: pip install SpeechRecognition pyaudio"
            )

        if self._is_running:
            print("[Audio] Already listening.")
            return

        print("[Audio] Initializing microphone...")
        try:
            mic = sr.Microphone(device_index=self.device_index)
        except Exception as e:
            raise RuntimeError(f"Failed to access microphone (device {self.device_index}): {e}")

        with mic as source:
            print("[Audio] Calibrating for ambient noise (1 second)...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            print(f"[Audio] Calibrated energy threshold: {self.recognizer.energy_threshold:.1f}")

        self._is_running = True
        self._session_start_time = time.time()

        # Audio consumer worker thread
        self._worker_thread = threading.Thread(target=self._process_audio_queue, daemon=True)
        self._worker_thread.start()

        # Background listener
        def audio_callback(recognizer: sr.Recognizer, audio_data: sr.AudioData):
            receive_time = time.time() - self._session_start_time
            self._audio_queue.put((audio_data, receive_time))

        self._stop_listening_fn = self.recognizer.listen_in_background(
            mic, audio_callback, phrase_time_limit=self.phrase_time_limit
        )
        print("[Audio] Real-time listening started. Speak into the microphone...")

    def _process_audio_queue(self) -> None:
        """Processes audio slices off the queue and runs STT recognition."""
        while self._is_running:
            try:
                audio_data, receive_time = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                # Transcribe using Google STT (standard zero-config engine in SpeechRecognition)
                transcription = self.recognizer.recognize_google(
                    audio_data, language=self.language
                )
                if not transcription or not transcription.strip():
                    continue

                duration = len(audio_data.frame_data) / (audio_data.sample_rate * audio_data.sample_width)
                start_time = max(0.0, receive_time - duration)
                end_time = receive_time

                segment = SourceSegment(
                    id=self._next_segment_id(),
                    text=transcription.strip(),
                    timestamp_start=round(start_time, 2),
                    timestamp_end=round(end_time, 2),
                    confidence=0.95,
                )

                print(f"[STT] [{segment.id}] ({segment.timestamp_start}s -> {segment.timestamp_end}s): {segment.text}")

                if self.on_segment:
                    try:
                        self.on_segment(segment)
                    except Exception as err:
                        print(f"[Audio] Error in segment callback: {err}")

            except sr.UnknownValueError:
                # Audio heard but no recognizable speech detected
                pass
            except sr.RequestError as e:
                print(f"[Audio] Recognition service request error: {e}")
            except Exception as e:
                print(f"[Audio] Unexpected error during recognition: {e}")
            finally:
                self._audio_queue.task_done()

    def simulate_segment(self, text: str) -> SourceSegment:
        """Injects a simulated text segment with valid provenance for testing without a microphone."""
        now = time.time() - self._session_start_time
        segment = SourceSegment(
            id=self._next_segment_id(),
            text=text.strip(),
            timestamp_start=round(now, 2),
            timestamp_end=round(now + 1.5, 2),
            confidence=1.0,
        )
        print(f"[STT-Simulated] [{segment.id}]: {segment.text}")
        if self.on_segment:
            self.on_segment(segment)
        return segment

    def stop_listening(self) -> None:
        """Stops the real-time background listener."""
        self._is_running = False
        if self._stop_listening_fn:
            self._stop_listening_fn(wait_for_stop=False)
            self._stop_listening_fn = None
        print("[Audio] Listening stopped.")


def main():
    parser = argparse.ArgumentParser(description="Semblance Canvas Realtime STT")
    parser.add_argument("--list-devices", action="store_true", help="List available microphones")
    parser.add_argument("--device", type=int, default=None, help="Input microphone device index")
    parser.add_argument("--lang", type=str, default="en-US", help="Language code (default: en-US)")
    parser.add_argument("--simulate", action="store_true", help="Interactive text simulation mode")
    args = parser.parse_args()

    if args.list_devices:
        mics = RealtimeVoiceTranscriber.list_microphones()
        print("Available Microphones:")
        for idx, name in enumerate(mics):
            print(f"  [{idx}] {name}")
        return

    transcriber = RealtimeVoiceTranscriber(
        language=args.lang,
        device_index=args.device,
        on_segment=lambda seg: print(f"==> Broadcasted segment: {seg}"),
    )

    if args.simulate:
        print("Running in simulation mode. Type phrases and press Enter (type 'exit' to quit):")
        while True:
            try:
                line = input("> ")
                if not line or line.strip().lower() == "exit":
                    break
                transcriber.simulate_segment(line)
            except (KeyboardInterrupt, EOFError):
                break
        return

    try:
        transcriber.start_listening()
        print("Press Ctrl+C to stop listening...")
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        transcriber.stop_listening()


if __name__ == "__main__":
    main()
