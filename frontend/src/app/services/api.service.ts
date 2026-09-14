import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  GenerateRequest,
  ProgressEvent,
  EventType,
  RunStatus,
  EditSessionStatus,
  SlideEditResponse,
  FinalizeResponse,
  DeckSettings,
  DeckSettingsSchema,
  ElicitResponse,
  OutlineRequest,
  OutlineResponse,
  OutlinePlan,
  OutlineSlide,
} from '../models/api.models';

const API_BASE = 'http://localhost:8000';

export interface SSEEvent {
  runId: string;
  event: ProgressEvent;
}

@Injectable({ providedIn: 'root' })
export class ApiService {

  startGeneration(request: GenerateRequest): Observable<SSEEvent> {
    return new Observable<SSEEvent>(subscriber => {
      const controller = new AbortController();

      fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal,
      })
        .then(async response => {
          if (!response.ok) {
            throw new Error(`Generation failed: ${response.status} ${response.statusText}`);
          }

          const runId = response.headers.get('X-Run-Id') ?? '';
          const reader = response.body!.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let currentEventType = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                currentEventType = line.slice(7).trim();
              } else if (line.startsWith('data: ')) {
                try {
                  const parsed = JSON.parse(line.slice(6)) as ProgressEvent;
                  if (currentEventType) {
                    parsed.event = currentEventType as EventType;
                  }
                  subscriber.next({ runId, event: parsed });
                } catch {
                  // skip malformed JSON
                }
                currentEventType = '';
              }
            }
          }
          subscriber.complete();
        })
        .catch(err => {
          if (err.name !== 'AbortError') {
            subscriber.error(err);
          }
        });

      return () => controller.abort();
    });
  }

  async fetchRunStatus(runId: string): Promise<RunStatus> {
    const res = await fetch(`${API_BASE}/runs/${runId}/status`);
    if (!res.ok) throw new Error(`Status fetch failed: ${res.status}`);
    return res.json();
  }

  getDownloadUrl(runId: string): string {
    return `${API_BASE}/runs/${runId}/download`;
  }

  async checkHealth(): Promise<{ status: string; active_runs: number }> {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  }

  async createEditSession(runId: string): Promise<EditSessionStatus> {
    const res = await fetch(`${API_BASE}/runs/${runId}/edit-session`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to create edit session: ${res.status}`);
    return res.json();
  }

  async editSlide(runId: string, slideIndex: number, feedback: string): Promise<SlideEditResponse> {
    const res = await fetch(`${API_BASE}/runs/${runId}/slides/${slideIndex}/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback }),
    });
    if (!res.ok) throw new Error(`Edit failed: ${res.status}`);
    return res.json();
  }

  async finalizeDeck(runId: string): Promise<FinalizeResponse> {
    const res = await fetch(`${API_BASE}/runs/${runId}/finalize`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Finalize failed: ${res.status}`);
    return res.json();
  }

  getScreenshotUrl(runId: string, slideIndex: number, version: number = 0): string {
    return `${API_BASE}/runs/${runId}/slides/${slideIndex}/screenshot?v=${version}`;
  }

  // ── Hierarchical planning: Gamma-style settings, elicitation, outline ────

  async getDeckSettingsSchema(): Promise<DeckSettingsSchema> {
    const res = await fetch(`${API_BASE}/deck-settings-schema`);
    if (!res.ok) throw new Error(`Failed to load deck settings schema: ${res.status}`);
    return res.json();
  }

  async elicit(
    prompt: string,
    deckSettings?: DeckSettings | null,
    suppliedContent?: Record<string, unknown> | null,
    domainHint = '',
  ): Promise<ElicitResponse> {
    const res = await fetch(`${API_BASE}/elicit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        deck_settings: deckSettings ?? null,
        supplied_content: suppliedContent ?? null,
        domain_hint: domainHint,
      }),
    });
    if (!res.ok) throw new Error(`Elicitation failed: ${res.status} ${res.statusText}`);
    return res.json();
  }

  async createOutline(request: OutlineRequest): Promise<OutlineResponse> {
    const res = await fetch(`${API_BASE}/plan/outline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!res.ok) throw new Error(`Outline planning failed: ${res.status} ${res.statusText}`);
    return res.json();
  }

  async updateOutline(
    runId: string,
    outline: OutlinePlan,
  ): Promise<{ run_id: string; accepted: boolean; slide_count: number }> {
    const res = await fetch(`${API_BASE}/plan/${runId}/outline`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(outline),
    });
    if (!res.ok) throw new Error(`Outline update failed: ${res.status} ${res.statusText}`);
    return res.json();
  }

  async regenerateOutlineSlide(
    coreHook: string,
    slide: OutlineSlide,
    feedback: string,
    deckSettings?: DeckSettings | null,
  ): Promise<OutlineSlide> {
    const res = await fetch(`${API_BASE}/plan/outline/regenerate-slide`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        core_hook: coreHook,
        outline_slide: slide,
        feedback,
        deck_settings: deckSettings ?? null,
      }),
    });
    if (!res.ok) throw new Error(`Slide regeneration failed: ${res.status} ${res.statusText}`);
    return res.json();
  }
}
