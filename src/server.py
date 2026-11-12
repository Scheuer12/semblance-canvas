"""Local Web & WebSocket Bridge Server for Semblance Canvas.

Serves preview.html and provides real-time WebSocket communication between the
Speech-to-Canvas pipeline and the embedded diagrams.net iframe.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.ai import SkillRunner, get_ai_client
from src.audio import RealtimeVoiceTranscriber, SourceSegment
from src.canvas import canvas_json_to_mxgraph_xml
from src.canvas.session_state import CanvasSessionState
from src.config import config

app = FastAPI(title="Semblance Canvas Bridge")
preview_file = Path(__file__).resolve().parent.parent / "preview.html"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAVE_FILE = DATA_DIR / "session_state.json"

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

# Initialize AI & Skills & Persistent State
skill_runner = SkillRunner()
session_state = CanvasSessionState()
accumulated_segments: List[SourceSegment] = []

# Restore persistent state from disk if present
if session_state.load_from_disk(SAVE_FILE):
    try:
        accumulated_segments = [SourceSegment(**s) for s in session_state.saved_segments]
        print(f"[Server] Restored persistent state from {SAVE_FILE} ({len(accumulated_segments)} segments, {len(session_state.nodes)} nodes)")
    except Exception as e:
        print(f"[Server] Error restoring segments: {e}")


@app.get("/", response_class=HTMLResponse)
async def get_index():
    if preview_file.is_file():
        return HTMLResponse(content=preview_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>preview.html not found</h1>", status_code=404)


import datetime

async def broadcast_event(data: dict):
    """Broadcasts a structured JSON event to all connected browser tabs."""
    payload = json.dumps(data)
    disconnected = set()
    for ws in list(active_connections):
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        active_connections.discard(ws)


async def broadcast_log(message: str, level: str = "INFO"):
    """Broadcasts a timestamped log entry to the Dev Tab."""
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    await broadcast_event({
        "type": "log",
        "time": now_str,
        "level": level,
        "message": message,
    })


def process_pipeline_sync(segments, status_callback=None):
    """Processes speech segments through Skill 1 and Skill 2, reconciling persistent state."""
    if status_callback:
        status_callback("semantic", "active", f"Analyzing {len(segments)} segments...")

    print(f"\n[Server] Running Skill 1 (Semantic Extraction)...")
    semantic_json = skill_runner.run_text_to_semantic(segments)

    # Reconcile persistent session state with semantic updates & direct deletions
    session_state.sync_from_semantic(semantic_json)

    if status_callback:
        status_callback("layout", "active", "Computing geometries and visual clusters...")

    print(f"[Server] Running Skill 2 (Canvas Geometry)...")
    # If active concepts remain, run Skill 2; if everything was deleted, produce empty/cleaned canvas
    if semantic_json.get("concepts"):
        canvas_json = skill_runner.run_semantic_to_canvas(semantic_json)
        # Update node geometries into persistent session
        for node in canvas_json.get("nodes", []):
            nid = node.get("id")
            if nid in session_state.nodes:
                session_state.nodes[nid]["geometry"] = node.get("geometry", session_state.nodes[nid]["geometry"])
                session_state.nodes[nid]["style"] = node.get("style", session_state.nodes[nid]["style"])
    else:
        canvas_json = session_state.to_canvas_json()

    if status_callback:
        status_callback("canvas", "active", "Formatting mxGraph XML...")

    xml = canvas_json_to_mxgraph_xml(canvas_json)
    return {
        "xml": xml,
        "semantic_json": semantic_json,
        "canvas_json": canvas_json,
        "actions": list(session_state.action_history),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    print(f"[Server] Client connected ({len(active_connections)} active)")
    await broadcast_log(f"Browser client connected ({len(active_connections)} active tab)")

    # Send initial stage readiness
    for stage_name in ("audio", "semantic", "layout", "canvas"):
        await broadcast_event({
            "type": "stage_update",
            "stage": stage_name,
            "status": "ready",
            "details": "Ready / Standby",
        })

    # If there is a restored persistent diagram state, push it to the freshly connected tab
    if session_state.last_xml:
        await websocket.send_text(json.dumps({
            "type": "pipeline_success",
            "xml": session_state.last_xml,
            "canvas_json": session_state.to_canvas_json(),
            "message": "Restored persistent diagram from disk",
        }))
        await broadcast_log("Restored persistent canvas state to client tab.")

    loop = asyncio.get_event_loop()

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                continue

            msg_type = data.get("type")

            if msg_type == "clear_canvas":
                accumulated_segments.clear()
                session_state.reset()
                session_state.clear_disk(SAVE_FILE)
                empty_xml = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
                await broadcast_log("Canvas and persistent session state reset by user.")
                await broadcast_event({
                    "type": "pipeline_success",
                    "xml": empty_xml,
                    "semantic_json": {"mode": "mode_b_direction", "concepts": [], "relationships": [], "direct_actions": []},
                    "canvas_json": session_state.to_canvas_json(),
                    "message": "Canvas cleared",
                })
                continue

            if msg_type == "speech_input":
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue

                counter = len(accumulated_segments) + 1
                segment = SourceSegment(
                    id=f"s-{counter}",
                    text=user_text,
                    timestamp_start=0.0,
                    timestamp_end=1.0,
                )
                accumulated_segments.append(segment)

                input_source = data.get("source", "manual")
                log_prefix = "🎙️ [VOICE]" if input_source == "microphone" else "[TEXT]"
                await broadcast_log(f"{log_prefix} Received segment [{segment.id}]: '{user_text}'")
                
                audio_detail = f"Voice captured [{segment.id}]" if input_source == "microphone" else f"Text segment [{segment.id}] ready"
                await broadcast_event({
                    "type": "stage_update",
                    "stage": "audio",
                    "status": "ready",
                    "details": audio_detail,
                })

                def sync_status_emitter(stage, status, msg):
                    asyncio.run_coroutine_threadsafe(
                        broadcast_event({"type": "stage_update", "stage": stage, "status": status, "details": msg}),
                        loop,
                    )
                    asyncio.run_coroutine_threadsafe(
                        broadcast_log(f"[{stage.upper()}] {msg}"),
                        loop,
                    )

                try:
                    result = await loop.run_in_executor(
                        None, process_pipeline_sync, accumulated_segments, sync_status_emitter
                    )

                    await broadcast_event({
                        "type": "pipeline_success",
                        "xml": result["xml"],
                        "semantic_json": result["semantic_json"],
                        "canvas_json": result["canvas_json"],
                        "actions": result.get("actions", []),
                        "message": f"Processed '{user_text}'",
                    })

                    # Persist session state and segments to local disk
                    session_state.last_xml = result["xml"]
                    session_state.saved_segments = [s.to_dict() for s in accumulated_segments]
                    session_state.save_to_disk(SAVE_FILE)

                    # Reset stages back to ready
                    for stage in ("audio", "semantic", "layout", "canvas"):
                        await broadcast_event({
                            "type": "stage_update",
                            "stage": stage,
                            "status": "ready",
                            "details": "Ready / Idle",
                        })

                    await broadcast_log(f"Pipeline completed & persisted state to disk for segment {segment.id}")

                except Exception as err:
                    print(f"[Server] Pipeline execution error: {err}")
                    await broadcast_event({
                        "type": "pipeline_error",
                        "stage": "semantic",
                        "status": "error",
                        "error": str(err),
                        "details": str(err)[:120],
                    })
                    await broadcast_log(f"Pipeline error: {err}", level="ERROR")

    except WebSocketDisconnect:
        active_connections.discard(websocket)
        print(f"[Server] Client disconnected ({len(active_connections)} remaining)")


def main():
    parser = argparse.ArgumentParser(description="Semblance Canvas Bridge Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--backend", default=None, help="AI backend override (gemini_cli, mock, etc.)")
    args = parser.parse_args()

    if args.backend:
        config.ai.backend = args.backend
        global skill_runner
        skill_runner = SkillRunner(ai_client=get_ai_client(config.ai))

    print(f"\n=======================================================")
    print(f"  Semblance Canvas Live Bridge Server")
    print(f"  Open in your browser: http://{args.host}:{args.port}")
    print(f"  AI Backend: {config.ai.backend}")
    print(f"=======================================================\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
