import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { GenerateRequest, ProgressEvent, EventType, RunStatus } from '../models/api.models';

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
}
