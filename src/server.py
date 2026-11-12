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
from src.canvas import canvas_json_to_mxgraph_xml, compute_deterministic_canvas_layout
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


@app.on_event("startup")
async def startup_event():
    # Pre-warm AI daemon in background thread to eliminate first-turn cold start
    print("[Server] Triggering proactive background AI daemon pre-warming...")
    loop = asyncio.get_event_loop()

    def _prewarm_task():
        skill_runner.ai_client.warm_up()
        model_name = getattr(skill_runner.ai_client, "model", config.ai.model or "gemini-3.8-flash-low")
        print(f"[Server] Resident AI daemon pre-warmed and ready (model: {model_name})")
        asyncio.run_coroutine_threadsafe(
            broadcast_log(f"Resident AI instance pre-warmed & active with system context (model: {model_name})"),
            loop,
        )

    loop.run_in_executor(None, _prewarm_task)


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


def process_pipeline_sync(segments, status_callback=None, log_callback=None, event_callback=None):
    """Processes speech segments through Skill 1 and deterministic visual type mapping, reconciling persistent state."""
    if status_callback:
        status_callback("semantic", "active", f"Analyzing {len(segments)} segments...")

    def on_skill_log(msg: str, level: str = "INFO"):
        if log_callback:
            log_callback(f"[AI] {msg}", level)

    def on_semantic_json(raw_json: dict, error_msg: Optional[str] = None):
        if event_callback:
            event_callback({
                "type": "semantic_json_update",
                "semantic_json": raw_json,
                "has_error": bool(error_msg),
                "error": error_msg,
            })

    def on_canvas_json(raw_json: dict, error_msg: Optional[str] = None):
        if event_callback:
            event_callback({
                "type": "canvas_json_update",
                "canvas_json": raw_json,
                "has_error": bool(error_msg),
                "error": error_msg,
            })

    print(f"\n[Server] Running Skill 1 (Semantic Extraction)...")
    semantic_json = skill_runner.run_text_to_semantic(
        segments,
        on_log=on_skill_log,
        on_semantic_json=on_semantic_json,
    )

    # Reconcile persistent session state with semantic updates & direct deletions
    session_state.sync_from_semantic(semantic_json)

    if status_callback:
        status_callback("layout", "active", "Applying deterministic layout & visual type mapping (< 5ms)...")

    print(f"[Server] Computing Deterministic Layout & Visual Type Mapping...")
    # Compute visual layout deterministically in Python in 2ms without secondary LLM call
    canvas_json = compute_deterministic_canvas_layout(semantic_json)

    # Sync computed geometry, style and typed role into persistent session state
    for node in canvas_json.get("nodes", []):
        nid = node.get("id")
        if nid in session_state.nodes:
            session_state.nodes[nid]["geometry"] = node.get("geometry", session_state.nodes[nid]["geometry"])
            session_state.nodes[nid]["style"] = node.get("style", session_state.nodes[nid]["style"])
            session_state.nodes[nid]["type"] = node.get("type", session_state.nodes[nid].get("type"))

    for cluster in canvas_json.get("visual_clusters", []):
        cid = cluster.get("id")
        if cid in session_state.clusters:
            session_state.clusters[cid]["bounds"] = cluster.get("bounds", session_state.clusters[cid]["bounds"])
            session_state.clusters[cid]["style"] = cluster.get("style", session_state.clusters[cid]["style"])

    on_canvas_json(canvas_json, None)
    if log_callback:
        n_count = len(canvas_json.get("nodes", []))
        c_count = len(canvas_json.get("visual_clusters", []))
        log_callback(f"[LAYOUT] Deterministic layout computed: {n_count} nodes, {c_count} clusters in < 5ms", "INFO")

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

    # Broadcast AI backend status and resident daemon readiness to Dev Tab
    model_name = getattr(skill_runner.ai_client, "model", config.ai.model or "gemini-3.8-flash-low")
    is_ready = getattr(skill_runner.ai_client, "is_ready", False)
    ai_status = "active & pre-warmed" if is_ready else "resident daemon initialized"
    await broadcast_log(f"AI backend initialized ({config.ai.backend}) | Model: {model_name} | Resident daemon: {ai_status}")

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
    pipeline_busy = False
    pending_coalesce = False

    async def run_coalesced_pipeline():
        nonlocal pipeline_busy, pending_coalesce
        if pipeline_busy:
            pending_coalesce = True
            await broadcast_log("Pipeline busy; buffering incoming segment for consolidated turn...", level="INFO")
            return

        pipeline_busy = True
        try:
            while True:
                pending_coalesce = False
                snapshot_segments = list(accumulated_segments)
                if not snapshot_segments:
                    break

                last_segment = snapshot_segments[-1]

                def sync_status_emitter(stage, status, msg):
                    asyncio.run_coroutine_threadsafe(
                        broadcast_event({"type": "stage_update", "stage": stage, "status": status, "details": msg}),
                        loop,
                    )
                    asyncio.run_coroutine_threadsafe(
                        broadcast_log(f"[{stage.upper()}] {msg}"),
                        loop,
                    )

                def sync_log_emitter(msg, level="INFO"):
                    asyncio.run_coroutine_threadsafe(
                        broadcast_log(msg, level=level),
                        loop,
                    )

                def sync_event_emitter(event_dict):
                    asyncio.run_coroutine_threadsafe(
                        broadcast_event(event_dict),
                        loop,
                    )

                try:
                    result = await loop.run_in_executor(
                        None,
                        process_pipeline_sync,
                        snapshot_segments,
                        sync_status_emitter,
                        sync_log_emitter,
                        sync_event_emitter,
                    )

                    await broadcast_event({
                        "type": "pipeline_success",
                        "xml": result["xml"],
                        "semantic_json": result["semantic_json"],
                        "canvas_json": result["canvas_json"],
                        "actions": result.get("actions", []),
                        "message": f"Processed up to {last_segment.id}: '{last_segment.text[:32]}...'",
                    })

                    # Persist session state and segments to local disk
                    session_state.last_xml = result["xml"]
                    session_state.saved_segments = [s.to_dict() for s in snapshot_segments]
                    session_state.save_to_disk(SAVE_FILE)

                    # Reset stages back to ready
                    for stage in ("audio", "semantic", "layout", "canvas"):
                        await broadcast_event({
                            "type": "stage_update",
                            "stage": stage,
                            "status": "ready",
                            "details": "Ready / Idle",
                        })

                    await broadcast_log(f"Pipeline completed & synced up to segment {last_segment.id}")

                except Exception as err:
                    print(f"[Server] Pipeline execution error: {err}")
                    raw_json = getattr(err, "raw_json", None)
                    await broadcast_event({
                        "type": "pipeline_error",
                        "stage": "semantic",
                        "status": "error",
                        "error": str(err),
                        "details": str(err)[:120],
                        "semantic_json": raw_json,
                    })
                    await broadcast_log(f"Pipeline error: {err}", level="ERROR")

                # If no new segments arrived while processing, break loop
                if not pending_coalesce and len(snapshot_segments) == len(accumulated_segments):
                    break
        finally:
            pipeline_busy = False

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                continue

            msg_type = data.get("type")

            if msg_type == "client_log":
                c_level = data.get("level", "INFO")
                c_msg = data.get("message", "")
                print(f"[Client Browser] [{c_level}] {c_msg}")
                await broadcast_log(f"[Browser] {c_msg}", level=c_level)
                continue

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

                asyncio.create_task(run_coalesced_pipeline())

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
