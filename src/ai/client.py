"""AI Connectivity Client for Semblance Canvas.

Provides access to Google Antigravity (subscription OAuth), the legacy Gemini CLI,
the Google GenAI SDK, or a deterministic mock backend.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.config import AIConfig, config


def extract_json(text: str) -> Dict[str, Any]:
    """Robustly extracts JSON from an LLM response string."""
    text = text.strip()

    # Try 1: Direct JSON parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try 2: Markdown fenced code block (```json ... ``` or ``` ...)
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        block = match.group(1).strip()
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass

    # Try 3: Search for outermost curly braces { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        slice_text = text[first_brace : last_brace + 1]
        try:
            return json.loads(slice_text)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")


class BaseAIClient(ABC):
    """Abstract base class for AI connectivity backends."""

    is_ready: bool = False

    @abstractmethod
    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Sends prompt and returns parsed JSON dictionary."""
        pass

    def warm_up(self) -> None:
        """Pre-warms the backend process if resident/daemonized. Default is no-op."""
        pass


class AntigravityCliClient(BaseAIClient):
    """Runs prompts through Antigravity CLI using its cached Google OAuth session.

    Uses a persistent resident child process (stream-json daemon) to eliminate
    per-turn cold-start latency, preserve session cache, and silence window popups.
    """

    def __init__(self, ai_cfg: AIConfig):
        self.cli_path = ai_cfg.antigravity_cli_path
        self.model = ai_cfg.model or "gemini-3.8-flash-low"
        self.timeout_seconds = ai_cfg.cli_timeout_seconds or 120
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.is_ready = False

    def _ensure_proc(self) -> subprocess.Popen:
        """Starts or restarts the resident agy stream-json daemon."""
        if self._proc is not None and self._proc.poll() is None:
            return self._proc

        env = os.environ.copy()
        env.pop("GEMINI_API_KEY", None)
        env.pop("GOOGLE_API_KEY", None)
        env.pop("GOOGLE_GENAI_USE_GCA", None)

        cmd = [
            self.cli_path,
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--disable-slash-commands",
            "--effort",
            "low",
        ]
        if self.model:
            cmd.extend(["--model", self.model])

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env=env,
                creationflags=creationflags,
            )
            # Read one-time handshake init line
            init_line = self._proc.stdout.readline()
            if not init_line:
                err = self._proc.stderr.read()
                raise RuntimeError(f"Antigravity CLI failed during startup initialization: {err}")
            self.is_ready = True
            return self._proc
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Antigravity CLI not found at '{self.cli_path}'. Install 'agy' and authenticate once interactively."
            ) from e

    def warm_up(self) -> None:
        """Pre-starts the resident agy daemon in the background to eliminate cold start."""
        with self._lock:
            try:
                self._ensure_proc()
                self.is_ready = True
            except Exception as e:
                print(f"[AIClient] Pre-warm warning: {e}")

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        combined_prompt = prompt
        if system_instruction:
            combined_prompt = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER REQUEST:\n{prompt}"

        with self._lock:
            proc = self._ensure_proc()
            payload = json.dumps({"event": "user", "message": {"content": combined_prompt}}) + "\n"

            try:
                proc.stdin.write(payload)
                proc.stdin.flush()

                # Read streamed lines until final result event is emitted
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        # Process closed unexpectedly
                        err = proc.stderr.read() if proc.stderr else ""
                        self._proc = None
                        raise RuntimeError(f"Antigravity CLI daemon terminated unexpectedly: {err}")

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if data.get("event") == "result":
                        res = data.get("result", {})
                        if res.get("status") == "ERROR":
                            raise RuntimeError(f"Antigravity CLI error: {res.get('error')}")
                        raw_response = res.get("response", "")
                        return extract_json(raw_response)

            except Exception as e:
                # Force restart daemon on fatal I/O failure
                if self._proc:
                    try:
                        self._proc.terminate()
                    except Exception:
                        pass
                    self._proc = None
                raise e


class GeminiCliClient(BaseAIClient):
    """Executes requests using the installed Gemini CLI tool."""

    def __init__(self, ai_cfg: AIConfig):
        self.cli_path = ai_cfg.gemini_cli_path
        self.model = ai_cfg.model
        self.api_key = ai_cfg.gemini_api_key
        self.use_google_auth = ai_cfg.use_google_auth
        self.skip_trust = ai_cfg.skip_trust

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        combined_prompt = prompt
        if system_instruction:
            combined_prompt = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER REQUEST:\n{prompt}"

        # Setup environment variables
        env = os.environ.copy()
        if self.api_key:
            env["GEMINI_API_KEY"] = self.api_key
        elif self.use_google_auth:
            # Authenticates via Google Account subscription (Gemini Code Assist / Google OAuth)
            env["GOOGLE_GENAI_USE_GCA"] = "true"

        if self.skip_trust:
            env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        cmd = [self.cli_path]
        if self.skip_trust:
            cmd.append("--skip-trust")
        if self.model:
            cmd.extend(["-m", self.model])
        cmd.extend(["-p", combined_prompt])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
                shell=True,  # For Windows .cmd resolution
            )
        except Exception as e:
            raise RuntimeError(f"Failed to execute Gemini CLI: {e}")

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or proc.stdout.strip()
            raise RuntimeError(f"Gemini CLI exited with code {proc.returncode}: {error_msg}")

        output = proc.stdout.strip()
        return extract_json(output)


class GoogleGenAIClient(BaseAIClient):
    """Uses official google-genai Python SDK."""

    def __init__(self, ai_cfg: AIConfig):
        try:
            from google import genai
        except ImportError:
            raise ImportError("google-genai package not installed. Run: pip install google-genai")

        self.api_key = ai_cfg.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for google_genai backend.")
        self.client = genai.Client(api_key=self.api_key)
        self.model = ai_cfg.model or "gemini-2.5-flash"

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "system_instruction": system_instruction,
            },
        )
        return extract_json(response.text)


class MockAIClient(BaseAIClient):
    """Deterministic mock client for offline tests without requiring an active API key."""

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        # Handle Skill 1 (text to semantic)
        if "text_to_semantic_json" in (system_instruction or "") or "SemanticJsonOutput" in prompt:
            return {
                "mode": "mode_a_ideas",
                "template": None,
                "clusters": [
                    {"id": "c-core", "label": "Core Systems", "theme": "core"}
                ],
                "concepts": [
                    {
                        "id": "node-1",
                        "label": "Speech Ingestion",
                        "type": "concept",
                        "cluster_id": "c-core",
                        "source_ids": ["s-1"],
                    },
                    {
                        "id": "node-2",
                        "label": "Canvas Manipulation",
                        "type": "concept",
                        "cluster_id": "c-core",
                        "source_ids": ["s-1"],
                    },
                ],
                "relationships": [
                    {
                        "id": "rel-1",
                        "source": "node-1",
                        "target": "node-2",
                        "relation_type": "leads_to",
                        "label": "streams to",
                        "directed": True,
                        "source_ids": ["s-1"],
                    }
                ],
                "direct_actions": [],
            }

        # Handle Skill 2 (semantic to canvas)
        return {
            "canvas_metadata": {
                "layout_style": "horizontal_flow",
                "canvas_width": 800,
                "canvas_height": 500,
            },
            "visual_clusters": [
                {
                    "id": "c-core",
                    "label": "Core Systems",
                    "bounds": {"x": 50, "y": 50, "width": 450, "height": 200},
                    "style": "swimlane;startSize=25;rounded=1;fillColor=#F5F5F5;strokeColor=#D5D5D5;",
                }
            ],
            "nodes": [
                {
                    "id": "node-1",
                    "label": "Speech Ingestion",
                    "type": "concept",
                    "cluster_id": "c-core",
                    "geometry": {"x": 80, "y": 100, "width": 160, "height": 60},
                    "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;",
                    "source_ids": ["s-1"],
                },
                {
                    "id": "node-2",
                    "label": "Canvas Manipulation",
                    "type": "concept",
                    "cluster_id": "c-core",
                    "geometry": {"x": 300, "y": 100, "width": 160, "height": 60},
                    "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;",
                    "source_ids": ["s-1"],
                },
            ],
            "edges": [
                {
                    "id": "rel-1",
                    "source": "node-1",
                    "target": "node-2",
                    "label": "streams to",
                    "directed": True,
                    "style": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;",
                    "source_ids": ["s-1"],
                }
            ],
        }


def get_ai_client(ai_cfg: Optional[AIConfig] = None) -> BaseAIClient:
    """Factory to instantiate the configured AI backend."""
    cfg = ai_cfg or config.ai
    backend = cfg.backend.lower()

    if backend in ("antigravity_cli", "antigravity", "agy"):
        return AntigravityCliClient(cfg)
    elif backend == "gemini_cli":
        return GeminiCliClient(cfg)
    elif backend in ("google_genai", "genai", "api"):
        return GoogleGenAIClient(cfg)
    elif backend == "mock":
        return MockAIClient()
    else:
        raise ValueError(
            f"Unknown AI backend: {cfg.backend}. Supported: antigravity_cli, gemini_cli, google_genai, mock"
        )
