"""Configuration loader for Semblance Canvas.

Loads settings from config.json with overrides from environment variables.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AIConfig:
    backend: str = "antigravity_cli"
    antigravity_cli_path: str = "agy"
    gemini_cli_path: str = "gemini"
    model: Optional[str] = None
    gemini_api_key: Optional[str] = None
    use_google_auth: bool = True  # Legacy Gemini CLI compatibility only.
    skip_trust: bool = True
    cli_timeout_seconds: int = 60
    temperature: float = 0.1


@dataclass
class AudioConfig:
    language: str = "en-US"
    energy_threshold: int = 300
    pause_threshold: float = 0.8
    phrase_time_limit: float = 15.0
    device_index: Optional[int] = None


@dataclass
class CanvasConfig:
    default_node_width: int = 160
    default_node_height: int = 60
    horizontal_spacing: int = 80
    vertical_spacing: int = 60


@dataclass
class AppConfig:
    ai: AIConfig = field(default_factory=AIConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    canvas: CanvasConfig = field(default_factory=CanvasConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> AppConfig:
        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent / "config.json"

        raw_data: Dict[str, Any] = {}
        if config_path.is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            except Exception as e:
                print(f"[Config] Warning: Failed to read {config_path}: {e}")

        ai_raw = raw_data.get("ai", {})
        audio_raw = raw_data.get("audio", {})
        canvas_raw = raw_data.get("canvas", {})

        # Environment variable overrides
        api_key = os.getenv("GEMINI_API_KEY", ai_raw.get("gemini_api_key"))
        backend = os.getenv("AI_BACKEND", ai_raw.get("backend", "antigravity_cli"))
        antigravity_cli_path = os.getenv(
            "ANTIGRAVITY_CLI_PATH", ai_raw.get("antigravity_cli_path", "agy")
        )
        cli_path = os.getenv("GEMINI_CLI_PATH", ai_raw.get("gemini_cli_path", "gemini"))
        use_google_auth = os.getenv("GOOGLE_GENAI_USE_GCA", str(ai_raw.get("use_google_auth", True))).lower() in ("true", "1")

        ai_cfg = AIConfig(
            backend=backend,
            antigravity_cli_path=antigravity_cli_path,
            gemini_cli_path=cli_path,
            model=ai_raw.get("model") or None,
            gemini_api_key=api_key if api_key else None,
            use_google_auth=use_google_auth,
            skip_trust=ai_raw.get("skip_trust", True),
            cli_timeout_seconds=int(ai_raw.get("cli_timeout_seconds", 60)),
            temperature=float(ai_raw.get("temperature", 0.1)),
        )

        audio_cfg = AudioConfig(
            language=audio_raw.get("language", "en-US"),
            energy_threshold=int(audio_raw.get("energy_threshold", 300)),
            pause_threshold=float(audio_raw.get("pause_threshold", 0.8)),
            phrase_time_limit=float(audio_raw.get("phrase_time_limit", 15.0)),
            device_index=audio_raw.get("device_index"),
        )

        canvas_cfg = CanvasConfig(
            default_node_width=int(canvas_raw.get("default_node_width", 160)),
            default_node_height=int(canvas_raw.get("default_node_height", 60)),
            horizontal_spacing=int(canvas_raw.get("horizontal_spacing", 80)),
            vertical_spacing=int(canvas_raw.get("vertical_spacing", 60)),
        )

        return cls(ai=ai_cfg, audio=audio_cfg, canvas=canvas_cfg)


# Global default configuration instance
config = AppConfig.load()
