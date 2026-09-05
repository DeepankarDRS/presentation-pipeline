"""FastAPI + SSE API layer for the presentation pipeline.

Endpoints:
  POST /generate             — start generation, return SSE stream
  GET  /runs/{run_id}/status — poll for run status
  GET  /runs/{run_id}/download — serve the generated PPTX
  GET  /health               — health check
"""

from __future__ import annotations

import asyncio
import logging
import queue as stdlib_queue
import time
import uuid
from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.graph import compile_graph
from src.state import initial_state
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Presentation Pipeline API", version="0.1.0")


# ── Pydantic models ────────────────────────────────────────────────────────

class CriticMode(str, Enum):
    auto = "auto"
    manual = "manual"
    off = "off"


class GenerateRequest(BaseModel):
    prompt: str
    theme: str = ""
    critic_mode: CriticMode = CriticMode.auto
    deck_min_threshold: int = Field(default=3, ge=1, le=20)
    supplied_content: dict[str, Any] | None = None
    audience_context: dict[str, str] | None = None


class ProgressEvent(BaseModel):
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float
    run_id: str


class RunStatus(BaseModel):
    run_id: str
    status: str
    progress_pct: int = 0
    current_step: str = ""
    passed: bool | None = None
    pptx_path: str | None = None
    error: str | None = None


# ── Run tracking ───────────────────────────────────────────────────────────

@dataclass
class RunRecord:
    run_id: str
    status: str = "pending"
    progress_pct: int = 0
    current_step: str = ""
    passed: bool | None = None
    pptx_path: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


_runs: dict[str, RunRecord] = {}
_MAX_AGE = 3600


def _cleanup_old_runs() -> None:
    cutoff = time.time() - _MAX_AGE
    stale = [rid for rid, r in _runs.items() if r.created_at < cutoff]
    for rid in stale:
        del _runs[rid]


# ── Node-to-event mapping ─────────────────────────────────────────────────

NODE_EVENT_MAP: dict[str, str] = {
    "questionnaire": "planning",
    "planner": "planning",
    "style_resolver": "styling",
    "context_builder": "generating_slide",
    "generator": "generating_slide",
    "validator": "validating",
    "repairer": "repairing",
    "critic": "reviewing",
    "slide_router": "generating_slide",
    "deck_assembler": "assembling",
    "evaluator": "complete",
}

_NODE_WEIGHTS: dict[str, int] = {
    "questionnaire": 2, "planner": 8, "style_resolver": 3,
    "context_builder": 5, "generator": 25, "validator": 10,
    "repairer": 15, "critic": 10, "slide_router": 2,
    "deck_assembler": 10, "evaluator": 5,
}


def _estimate_progress(completed_nodes: list[str], total_slides: int) -> int:
    total_weight = sum(_NODE_WEIGHTS.get(n, 5) for n in completed_nodes)
    expected = 68
    if total_slides > 1:
        per_slide = 52
        expected = 13 + (per_slide * total_slides) + 15
    return min(int((total_weight / max(expected, 1)) * 100), 99)


# ── Event building ─────────────────────────────────────────────────────────

def _build_event(
    node_name: str,
    run_id: str,
    accumulated: dict[str, Any],
) -> ProgressEvent:
    event_type = NODE_EVENT_MAP.get(node_name, node_name)
    data: dict[str, Any] = {"node": node_name}

    if event_type == "generating_slide":
        data["slide_index"] = accumulated.get("current_slide_index", 0)
        data["total"] = max(len(accumulated.get("slide_plans", [])), 1)

    elif event_type == "repairing":
        data["retry_count"] = accumulated.get("retry_count", 0)
        data["tier"] = accumulated.get("retry_tier", 0)

    elif event_type == "complete":
        data["passed"] = accumulated.get("passed", False)
        data["pptx_path"] = accumulated.get("pptx_path")
        evaluation = accumulated.get("evaluation") or {}
        data["evaluation_summary"] = {
            k: evaluation[k]
            for k in ("passed", "compile_ok", "tokens", "cost")
            if k in evaluation
        }

    return ProgressEvent(
        event=event_type, data=data,
        timestamp=time.time(), run_id=run_id,
    )


def _merge_state(accumulated: dict[str, Any], update: dict[str, Any]) -> None:
    for key, value in update.items():
        if key in ("completed_slides", "generation_history") and isinstance(value, list):
            accumulated.setdefault(key, []).extend(value)
        else:
            accumulated[key] = value


# ── Pipeline execution ─────────────────────────────────────────────────────

def _run_pipeline_sync(
    run_id: str, request: GenerateRequest,
) -> Generator[tuple[str, dict[str, Any]], None, None]:
    state = initial_state(
        run_id=run_id,
        raw_request=request.prompt,
        theme_name=request.theme,
        critic_mode=request.critic_mode.value,
        deck_min_threshold=request.deck_min_threshold,
        supplied_content=request.supplied_content,
        audience_context=request.audience_context,
    )
    graph = compile_graph()
    config = {
        "run_name": f"api-{run_id}",
        "tags": ["presentation-pipeline", "api"],
        "metadata": {"run_id": run_id},
    }
    for chunk in graph.stream(state, config=config):
        for node_name, state_update in chunk.items():
            yield node_name, state_update


def _format_sse(event: ProgressEvent) -> str:
    return f"event: {event.event}\ndata: {event.model_dump_json()}\n\n"


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.post("/generate")
async def generate(request: GenerateRequest) -> StreamingResponse:
    _cleanup_old_runs()
    run_id = uuid.uuid4().hex[:12]
    _runs[run_id] = RunRecord(run_id=run_id, status="running")

    async def event_stream() -> AsyncGenerator[str, None]:
        record = _runs[run_id]
        accumulated: dict[str, Any] = {}
        completed_nodes: list[str] = []
        q: stdlib_queue.Queue[tuple[str, dict[str, Any]] | None] = stdlib_queue.Queue()

        def _producer() -> None:
            try:
                for node_name, state_update in _run_pipeline_sync(run_id, request):
                    q.put((node_name, state_update))
            except Exception as exc:
                q.put(("__error__", {"__message__": str(exc)}))
            finally:
                q.put(None)

        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, _producer)

        try:
            while True:
                item = await asyncio.to_thread(q.get)
                if item is None:
                    break

                node_name, state_update = item
                if node_name == "__error__":
                    record.status = "error"
                    record.error = state_update["__message__"]
                    yield _format_sse(ProgressEvent(
                        event="error",
                        data={"message": record.error},
                        timestamp=time.time(), run_id=run_id,
                    ))
                    break

                _merge_state(accumulated, state_update)
                completed_nodes.append(node_name)

                total_slides = len(accumulated.get("slide_plans", []))
                record.current_step = node_name
                record.progress_pct = _estimate_progress(completed_nodes, total_slides)

                event = _build_event(node_name, run_id, accumulated)
                yield _format_sse(event)

            await fut

            if record.status != "error":
                record.status = "complete"
                record.progress_pct = 100
                record.passed = accumulated.get("passed", False)
                record.pptx_path = accumulated.get("pptx_path")

        except Exception as exc:
            record.status = "error"
            record.error = str(exc)
            yield _format_sse(ProgressEvent(
                event="error",
                data={"message": str(exc)},
                timestamp=time.time(), run_id=run_id,
            ))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Run-Id": run_id},
    )


@app.get("/runs/{run_id}/status")
async def get_run_status(run_id: str) -> RunStatus:
    record = _runs.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return RunStatus(
        run_id=record.run_id, status=record.status,
        progress_pct=record.progress_pct, current_step=record.current_step,
        passed=record.passed, pptx_path=record.pptx_path, error=record.error,
    )


@app.get("/runs/{run_id}/download")
async def download_pptx(run_id: str) -> FileResponse:
    record = _runs.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if record.status != "complete" or not record.pptx_path:
        raise HTTPException(status_code=409, detail="Run not complete or no file produced")
    path = Path(record.pptx_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PPTX file not found on disk")
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{run_id}.pptx",
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "active_runs": sum(1 for r in _runs.values() if r.status == "running"),
    }


# ── Server entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    setup_logging()
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
