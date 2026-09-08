"""FastAPI + SSE API layer for the presentation pipeline.

Endpoints:
  POST /generate             — start generation, return SSE stream
  GET  /runs/{run_id}/status — poll for run status
  GET  /runs/{run_id}/download — serve the generated PPTX
  GET  /health               — health check
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue as stdlib_queue
import re
import time
import uuid
from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agents.planner import planner_node
from src.agents.planner_schema import (
    ComponentKindLiteral,
    DensityLiteral,
    FontTierLiteral,
    LayoutPatternLiteral,
    SlideTypeLiteral,
)
from src.graph import compile_graph
from src.state import (
    ComponentPlan,
    DeckPlan,
    SlidePlan,
    initial_state,
)
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Presentation Pipeline API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Run-Id"],
)


# ── Pydantic models ────────────────────────────────────────────────────────

class CriticMode(str, Enum):
    auto = "auto"
    manual = "manual"
    off = "off"


class GenerateRequest(BaseModel):
    prompt: str
    theme: str = ""
    critic_mode: CriticMode = CriticMode.off
    deck_min_threshold: int = Field(
        default=1, ge=1, le=20,
        description="Target slide count (1 = single slide; higher = multi-slide deck)",
    )
    supplied_content: dict[str, Any] | None = None
    audience_context: dict[str, str] | None = None


class ComponentPlanPayload(BaseModel):
    kind: str
    count: int = 1
    chart_type: str = ""
    series_count: int = 0
    columns: int = 0
    rows: int = 0
    items: int = 0
    content_summary: str = ""


class SlidePlanPayload(BaseModel):
    slide_index: int = 0
    slide_type: str
    components: list[ComponentPlanPayload]
    density: str = "normal"
    font_tier: str = "standard"
    layout_pattern: str = "two_column"
    layout_hint: str = ""
    content_data: dict[str, Any] = Field(default_factory=dict)


class GenerateFromPlanRequest(BaseModel):
    prompt: str
    theme: str = ""
    critic_mode: CriticMode = CriticMode.off
    deck_min_threshold: int = Field(default=1, ge=1, le=20)
    supplied_content: dict[str, Any] | None = None
    audience_context: dict[str, str] | None = None
    run_id: str = ""
    core_hook: str = ""
    slides: list[SlidePlanPayload]


class RefinePlanRequest(GenerateFromPlanRequest):
    feedback: str


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

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent


def _cleanup_old_runs() -> None:
    cutoff = time.time() - _MAX_AGE
    stale = [rid for rid, r in _runs.items() if r.created_at < cutoff]
    for rid in stale:
        del _runs[rid]


def _get_run_record(run_id: str) -> RunRecord | None:
    """Look up a run, falling back to run-manifest.json on disk.

    _runs is in-memory only and is empty after a server restart (or once
    an entry ages out via _cleanup_old_runs). The manifest written by the
    evaluator survives restarts, so reconstruct a RunRecord from it when
    the in-memory entry is missing.
    """
    record = _runs.get(run_id)
    if record is not None:
        return record

    manifest_path = _PIPELINE_ROOT / "output" / "runs" / run_id / "run-manifest.json"
    if not manifest_path.exists():
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    record = RunRecord(
        run_id=run_id,
        status="complete",
        progress_pct=100,
        current_step="complete",
        passed=manifest.get("passed"),
        pptx_path=manifest.get("pptx_path"),
    )
    _runs[run_id] = record
    return record


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
    record = _get_run_record(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return RunStatus(
        run_id=record.run_id, status=record.status,
        progress_pct=record.progress_pct, current_step=record.current_step,
        passed=record.passed, pptx_path=record.pptx_path, error=record.error,
    )


@app.get("/runs/{run_id}/download")
async def download_pptx(run_id: str) -> FileResponse:
    record = _get_run_record(run_id)
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


_VALID_COMPONENT_KINDS = set(ComponentKindLiteral.__args__)
_VALID_SLIDE_TYPES = set(SlideTypeLiteral.__args__)
_VALID_DENSITIES = set(DensityLiteral.__args__)
_VALID_FONT_TIERS = set(FontTierLiteral.__args__)
_VALID_LAYOUT_PATTERNS = set(LayoutPatternLiteral.__args__)


def _validate_plan(slides: list[SlidePlanPayload]) -> list[str]:
    errors: list[str] = []
    if not slides or len(slides) > 20:
        errors.append(f"Slide count must be 1-20, got {len(slides)}")
        return errors
    for i, s in enumerate(slides):
        if s.slide_type not in _VALID_SLIDE_TYPES:
            errors.append(f"Slide {i}: invalid slide_type '{s.slide_type}'")
        if s.density not in _VALID_DENSITIES:
            errors.append(f"Slide {i}: invalid density '{s.density}'")
        if s.font_tier not in _VALID_FONT_TIERS:
            errors.append(f"Slide {i}: invalid font_tier '{s.font_tier}'")
        if s.layout_pattern not in _VALID_LAYOUT_PATTERNS:
            errors.append(f"Slide {i}: invalid layout_pattern '{s.layout_pattern}'")
        if not s.components:
            errors.append(f"Slide {i}: must have at least one component")
        for j, c in enumerate(s.components):
            if c.kind not in _VALID_COMPONENT_KINDS:
                errors.append(f"Slide {i}, component {j}: invalid kind '{c.kind}'")
            if c.kind == "chart" and not c.chart_type:
                errors.append(f"Slide {i}, component {j}: chart requires chart_type")
            if c.kind == "table" and (c.columns < 1 or c.rows < 1):
                errors.append(f"Slide {i}, component {j}: table requires columns/rows >= 1")
    return errors


def _payload_to_slide_plans(
    slides: list[SlidePlanPayload],
    supplied_content: dict[str, Any] | None,
) -> list[SlidePlan]:
    from src.agents.planner import _compute_provenance

    result: list[SlidePlan] = []
    for i, s in enumerate(slides):
        components: list[ComponentPlan] = []
        for c in s.components:
            comp = ComponentPlan(kind=c.kind, count=c.count, content_summary=c.content_summary)
            if c.chart_type:
                comp["chart_type"] = c.chart_type
            if c.series_count:
                comp["series_count"] = c.series_count
            if c.columns:
                comp["columns"] = c.columns
            if c.rows:
                comp["rows"] = c.rows
            if c.items:
                comp["items"] = c.items
            components.append(comp)

        result.append(SlidePlan(
            slide_index=i,
            slide_type=s.slide_type,
            components=components,
            density=s.density,
            font_tier=s.font_tier,
            layout_pattern=s.layout_pattern,
            layout_hint=s.layout_hint,
            content_data=s.content_data,
            data_provenance=_compute_provenance(s.content_data, supplied_content or {}),
        ))
    return result


@app.post("/plan")
async def create_plan(request: GenerateRequest) -> dict[str, Any]:
    run_id = uuid.uuid4().hex[:12]
    state = initial_state(
        run_id=run_id,
        raw_request=request.prompt,
        theme_name=request.theme,
        deck_min_threshold=request.deck_min_threshold,
        supplied_content=request.supplied_content,
        audience_context=request.audience_context,
    )
    result = await asyncio.to_thread(planner_node, state)
    return {
        "run_id": run_id,
        "core_hook": result["core_hook"],
        "slides": result["slide_plans"],
    }


@app.post("/plan/refine")
async def refine_plan(request: RefinePlanRequest) -> dict[str, Any]:
    if not request.feedback.strip():
        raise HTTPException(status_code=422, detail="feedback must not be empty")
    if not request.slides:
        raise HTTPException(status_code=422, detail="slides must not be empty")

    run_id = request.run_id or uuid.uuid4().hex[:12]
    state = initial_state(
        run_id=run_id,
        raw_request=request.prompt,
        theme_name=request.theme,
        deck_min_threshold=request.deck_min_threshold,
        supplied_content=request.supplied_content,
        audience_context=request.audience_context,
    )
    state["prior_plan"] = {
        "core_hook": request.core_hook,
        "slides": _payload_to_slide_plans(request.slides, request.supplied_content),
    }
    state["refine_feedback"] = request.feedback

    try:
        result = await asyncio.to_thread(planner_node, state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plan refinement failed: {exc}")

    return {
        "run_id": run_id,
        "core_hook": result["core_hook"],
        "slides": result["slide_plans"],
    }


def _run_pipeline_from_plan_sync(
    run_id: str, request: GenerateFromPlanRequest,
) -> Generator[tuple[str, dict[str, Any]], None, None]:
    slide_plans = _payload_to_slide_plans(request.slides, request.supplied_content)
    state = initial_state(
        run_id=run_id,
        raw_request=request.prompt,
        theme_name=request.theme,
        critic_mode=request.critic_mode.value,
        deck_min_threshold=request.deck_min_threshold,
        supplied_content=request.supplied_content,
        audience_context=request.audience_context,
    )
    state["core_hook"] = request.core_hook
    state["slide_plans"] = slide_plans
    state["mode"] = "deck" if len(slide_plans) > 1 else "single"
    if len(slide_plans) > 1:
        state["deck_plan"] = DeckPlan(
            core_hook=request.core_hook,
            slide_count=len(slide_plans),
            theme=request.theme,
            slides=slide_plans,
        )

    graph = compile_graph()
    config = {
        "run_name": f"api-from-plan-{run_id}",
        "tags": ["presentation-pipeline", "api", "from-plan"],
        "metadata": {"run_id": run_id},
    }
    for chunk in graph.stream(state, config=config):
        for node_name, state_update in chunk.items():
            yield node_name, state_update


@app.post("/generate-from-plan")
async def generate_from_plan(request: GenerateFromPlanRequest) -> StreamingResponse:
    errors = _validate_plan(request.slides)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    _cleanup_old_runs()
    run_id = request.run_id or uuid.uuid4().hex[:12]
    _runs[run_id] = RunRecord(run_id=run_id, status="running")

    async def event_stream() -> AsyncGenerator[str, None]:
        record = _runs[run_id]
        accumulated: dict[str, Any] = {}
        completed_nodes: list[str] = []
        q: stdlib_queue.Queue[tuple[str, dict[str, Any]] | None] = stdlib_queue.Queue()

        def _producer() -> None:
            try:
                for node_name, state_update in _run_pipeline_from_plan_sync(run_id, request):
                    q.put((node_name, state_update))
            except Exception as exc:
                q.put(("__error__", {"__message__": str(exc)}))
            finally:
                q.put(None)

        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _producer)

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


# ── Edit session state ────────────────────────────────────────────────────

@dataclass
class EditRecord:
    version: int
    feedback: str
    xml_before: str
    xml_after: str
    screenshot_path: str | None
    compile_ok: bool
    repair_attempts: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class EditSlideState:
    slide_index: int
    current_xml: str
    original_xml: str
    screenshot_path: str | None = None
    edit_history: list[EditRecord] = field(default_factory=list)
    version: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    slide_plan: dict[str, Any] = field(default_factory=dict)


@dataclass
class EditSession:
    run_id: str
    slides: list[EditSlideState] = field(default_factory=list)
    theme_element: str = ""
    theme_info: dict[str, Any] = field(default_factory=dict)
    original_pptx_path: str | None = None
    final_pptx_path: str | None = None


_edit_sessions: dict[str, EditSession] = {}


class SlideEditRequest(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=2000)


class SlideInfoResponse(BaseModel):
    slide_index: int
    version: int
    screenshot_url: str | None
    has_edits: bool
    edit_count: int


class EditSessionResponse(BaseModel):
    run_id: str
    slide_count: int
    slides: list[SlideInfoResponse]


class SlideEditResponse(BaseModel):
    ok: bool
    slide_index: int
    version: int
    screenshot_url: str | None
    xml: str | None = None
    compile_ok: bool = False
    repair_attempts: int = 0
    issues: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class FinalizeResponse(BaseModel):
    ok: bool
    pptx_path: str | None = None
    download_url: str | None = None
    error: str | None = None


def _screenshot_url(run_id: str, slide_index: int, version: int = 0) -> str | None:
    return f"/runs/{run_id}/slides/{slide_index}/screenshot?v={version}"


def _load_edit_session(run_id: str) -> EditSession | None:
    """Load edit session from slides.json on disk."""
    slides_path = _PIPELINE_ROOT / "output" / "runs" / run_id / "slides.json"
    if not slides_path.exists():
        return None

    manifest_path = _PIPELINE_ROOT / "output" / "runs" / run_id / "run-manifest.json"
    theme_element = ""
    theme_info: dict[str, Any] = {}
    pptx_path: str | None = None

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        theme_element = manifest.get("theme_element", "")
        theme_info = manifest.get("resolved_theme") or {}
        pptx_path = manifest.get("pptx_path")

    slides_data = json.loads(slides_path.read_text(encoding="utf-8"))
    slides: list[EditSlideState] = []
    for s in slides_data:
        slides.append(EditSlideState(
            slide_index=s["slide_index"],
            current_xml=s["xml"],
            original_xml=s["xml"],
            screenshot_path=s.get("screenshot_path"),
            slide_plan=s.get("slide_plan", {}),
        ))

    return EditSession(
        run_id=run_id,
        slides=slides,
        theme_element=theme_element,
        theme_info=theme_info,
        original_pptx_path=pptx_path,
    )


def _persist_slides_json(session: EditSession) -> None:
    """Update slides.json on disk after an edit."""
    slides_path = _PIPELINE_ROOT / "output" / "runs" / session.run_id / "slides.json"
    data = []
    for s in session.slides:
        data.append({
            "slide_index": s.slide_index,
            "xml": s.current_xml,
            "speaker_notes": "",
            "screenshot_path": s.screenshot_path,
            "slide_plan": s.slide_plan,
        })
    slides_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@app.post("/runs/{run_id}/edit-session")
async def create_edit_session(run_id: str) -> EditSessionResponse:
    """Create an edit session from a completed pipeline run."""
    if run_id in _edit_sessions:
        session = _edit_sessions[run_id]
    else:
        session = _load_edit_session(run_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"No slides data for run {run_id}")
        _edit_sessions[run_id] = session

    slide_infos = []
    for s in session.slides:
        slide_infos.append(SlideInfoResponse(
            slide_index=s.slide_index,
            version=s.version,
            screenshot_url=_screenshot_url(run_id, s.slide_index, s.version)
                if s.screenshot_path else None,
            has_edits=len(s.edit_history) > 0,
            edit_count=len(s.edit_history),
        ))

    return EditSessionResponse(
        run_id=run_id,
        slide_count=len(session.slides),
        slides=slide_infos,
    )


@app.post("/runs/{run_id}/slides/{slide_index}/edit")
async def edit_slide(
    run_id: str, slide_index: int, request: SlideEditRequest,
) -> SlideEditResponse:
    """Apply an NL edit to a slide."""
    session = _edit_sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Edit session not found. Create one first.")

    if slide_index < 0 or slide_index >= len(session.slides):
        raise HTTPException(status_code=404, detail=f"Slide {slide_index} not found")

    slide = session.slides[slide_index]

    try:
        async with asyncio.timeout(120):
            await slide.lock.acquire()
    except TimeoutError:
        raise HTTPException(status_code=409, detail="Edit already in progress for this slide")

    try:
        from src.agents.slide_edit_service import edit_slide_xml
        from src.agents.slide_replanner import resolve_slide_plan

        try:
            updated_plan, contract = resolve_slide_plan(
                slide.slide_plan, request.feedback, session.theme_info, run_id,
            )
        except Exception as e:
            logger.warning(f"edit_slide: resolve_slide_plan failed, falling back to {{}}: {e}")
            updated_plan, contract = slide.slide_plan, {}

        result = await asyncio.to_thread(
            edit_slide_xml,
            current_xml=slide.current_xml,
            feedback=request.feedback,
            theme_element=session.theme_element,
            contract=contract,
            slide_plan=updated_plan,
            run_id=run_id,
            slide_index=slide_index,
            version=slide.version + 1,
        )

        if result.ok:
            xml_before = slide.current_xml
            slide.current_xml = result.xml
            slide.version += 1
            slide.slide_plan = updated_plan
            if result.screenshot_path:
                slide.screenshot_path = result.screenshot_path
            slide.edit_history.append(EditRecord(
                version=slide.version,
                feedback=request.feedback,
                xml_before=xml_before,
                xml_after=result.xml,
                screenshot_path=result.screenshot_path,
                compile_ok=result.compile_ok,
                repair_attempts=result.repair_attempts,
            ))
            _persist_slides_json(session)

        return SlideEditResponse(
            ok=result.ok,
            slide_index=slide_index,
            version=slide.version,
            screenshot_url=_screenshot_url(run_id, slide_index, slide.version)
                if slide.screenshot_path else None,
            xml=result.xml if result.ok else None,
            compile_ok=result.compile_ok,
            repair_attempts=result.repair_attempts,
            issues=result.issues,
            error=result.error,
        )
    finally:
        slide.lock.release()


@app.get("/runs/{run_id}/slides/{slide_index}/screenshot")
async def get_slide_screenshot(run_id: str, slide_index: int) -> FileResponse:
    """Serve a slide's screenshot PNG."""
    session = _edit_sessions.get(run_id)
    if session is None:
        session = _load_edit_session(run_id)
        if session:
            _edit_sessions[run_id] = session

    if session and 0 <= slide_index < len(session.slides):
        png_path = session.slides[slide_index].screenshot_path
        if png_path and Path(png_path).exists():
            return FileResponse(
                path=png_path,
                media_type="image/png",
                filename=f"slide-{slide_index}.png",
            )

    # Fallback: check screenshots directory directly
    screenshots_dir = _PIPELINE_ROOT / "output" / "runs" / run_id / "screenshots"
    fallback = screenshots_dir / f"slide-{slide_index}.png"
    if fallback.exists():
        return FileResponse(
            path=str(fallback),
            media_type="image/png",
            filename=f"slide-{slide_index}.png",
        )

    raise HTTPException(status_code=404, detail="Screenshot not found")


@app.get("/runs/{run_id}/slides/{slide_index}/xml")
async def get_slide_xml(run_id: str, slide_index: int) -> dict[str, Any]:
    """Return current XML for a slide (debugging)."""
    session = _edit_sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Edit session not found")
    if slide_index < 0 or slide_index >= len(session.slides):
        raise HTTPException(status_code=404, detail=f"Slide {slide_index} not found")

    slide = session.slides[slide_index]
    return {
        "slide_index": slide_index,
        "version": slide.version,
        "xml": slide.current_xml,
    }


@app.post("/runs/{run_id}/finalize")
async def finalize_deck(run_id: str) -> FinalizeResponse:
    """Reassemble all edited slides into a final PPTX."""
    session = _edit_sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Edit session not found")

    from src.compiler.compiler_client import CompilerError, compile_xml
    from src.compiler.normalizer import strip_theme

    def _extract_slide_block(xml: str) -> str:
        m = re.search(r'(<Slide\b[^>]*>.*?</Slide>)', xml, re.DOTALL)
        return m.group(1) if m else ""

    def _extract_theme(xml: str) -> str:
        m = re.search(r'<Theme\s[^>]*/>', xml)
        return m.group(0) if m else ""

    def _do_finalize() -> FinalizeResponse:
        theme = session.theme_element
        if not theme:
            for s in session.slides:
                theme = _extract_theme(s.current_xml)
                if theme:
                    break

        slide_blocks: list[str] = []
        for s in sorted(session.slides, key=lambda x: x.slide_index):
            block = _extract_slide_block(s.current_xml)
            if block:
                slide_blocks.append(strip_theme(block))

        if not slide_blocks:
            return FinalizeResponse(ok=False, error="No valid slide blocks found")

        if len(slide_blocks) == 1 and not theme:
            combined_xml = session.slides[0].current_xml
        else:
            combined_xml = theme.strip() + "\n" + "\n".join(slide_blocks)

        output_dir = _PIPELINE_ROOT / "output" / "runs" / run_id / "finalized"

        try:
            cr = compile_xml(combined_xml, output_dir)
        except CompilerError as e:
            return FinalizeResponse(ok=False, error=f"Compile failed: {e}")

        if not cr.get("ok", False):
            diags = cr.get("diagnostics", [])
            msg = diags[0]["message"] if diags else "Unknown compile error"
            return FinalizeResponse(ok=False, error=f"Compile failed: {msg}")

        pptx_path = cr.get("pptx_path")
        session.final_pptx_path = pptx_path

        record = _get_run_record(run_id)
        if record is None:
            record = RunRecord(run_id=run_id, status="complete", progress_pct=100, current_step="complete")
            _runs[run_id] = record
        record.pptx_path = pptx_path
        record.status = "complete"

        manifest_path = _PIPELINE_ROOT / "output" / "runs" / run_id / "run-manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["pptx_path"] = pptx_path
                manifest_path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
                )
            except (OSError, json.JSONDecodeError):
                pass

        return FinalizeResponse(
            ok=True,
            pptx_path=pptx_path,
            download_url=f"/runs/{run_id}/download" if pptx_path else None,
        )

    return await asyncio.to_thread(_do_finalize)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "active_runs": sum(1 for r in _runs.values() if r.status == "running"),
    }


# ── Static frontend (production) ──────────────────────────────────────────

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "frontend" / "browser"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")


# ── Server entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    setup_logging()
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
