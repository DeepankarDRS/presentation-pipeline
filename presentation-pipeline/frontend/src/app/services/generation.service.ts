import { Injectable, signal, computed, inject } from '@angular/core';
import { Subscription } from 'rxjs';
import { ApiService, SSEEvent } from './api.service';
import {
  AppView,
  EventType,
  EvaluationSummary,
  GenerateRequest,
  ProgressEvent,
} from '../models/api.models';
import { STEP_LABELS, PROGRESS_RANGES } from '../constants/theme.constants';

@Injectable({ providedIn: 'root' })
export class GenerationService {
  private readonly api = inject(ApiService);

  readonly view = signal<AppView>('form');
  readonly runId = signal<string | null>(null);
  readonly progressPct = signal<number>(0);
  readonly currentStep = signal<EventType | null>(null);
  readonly stepLabel = signal<string>('');
  readonly slideIndex = signal<number | null>(null);
  readonly slideTotal = signal<number | null>(null);
  readonly passed = signal<boolean | null>(null);
  readonly pptxPath = signal<string | null>(null);
  readonly evaluationSummary = signal<EvaluationSummary | null>(null);
  readonly error = signal<string | null>(null);

  readonly isGenerating = computed(() => this.view() === 'progress');

  private subscription: Subscription | null = null;

  generate(request: GenerateRequest): void {
    this.view.set('progress');
    this.progressPct.set(0);
    this.currentStep.set(null);
    this.stepLabel.set('Starting...');
    this.error.set(null);
    this.passed.set(null);
    this.evaluationSummary.set(null);

    this.subscription = this.api.startGeneration(request).subscribe({
      next: (sseEvent: SSEEvent) => {
        this.runId.set(sseEvent.runId);
        this.handleEvent(sseEvent.event);
      },
      error: (err: Error) => {
        this.view.set('result');
        this.error.set(err.message || 'Connection lost');
      },
      complete: () => {
        if (this.view() === 'progress') {
          this.view.set('result');
        }
      },
    });
  }

  cancel(): void {
    this.subscription?.unsubscribe();
    this.subscription = null;
    this.reset();
  }

  reset(): void {
    this.subscription?.unsubscribe();
    this.subscription = null;
    this.view.set('form');
    this.runId.set(null);
    this.progressPct.set(0);
    this.currentStep.set(null);
    this.stepLabel.set('');
    this.slideIndex.set(null);
    this.slideTotal.set(null);
    this.passed.set(null);
    this.pptxPath.set(null);
    this.evaluationSummary.set(null);
    this.error.set(null);
  }

  private handleEvent(event: ProgressEvent): void {
    const eventType = event.event;
    this.currentStep.set(eventType);

    if (eventType === 'complete') {
      this.progressPct.set(100);
      this.stepLabel.set(STEP_LABELS['complete']);
      this.view.set('result');
      const data = (event.data?.['data'] as Record<string, unknown>) ?? event.data;
      this.passed.set((data['passed'] as boolean) ?? null);
      this.pptxPath.set((data['pptx_path'] as string) ?? null);
      if (data['evaluation']) {
        this.evaluationSummary.set(data['evaluation'] as EvaluationSummary);
      }
      return;
    }

    if (eventType === 'error') {
      this.view.set('result');
      const data = (event.data?.['data'] as Record<string, unknown>) ?? event.data;
      this.error.set((data['message'] as string) ?? 'Unknown error');
      return;
    }

    this.stepLabel.set(this.deriveStepLabel(event));
    this.progressPct.set(this.estimateProgress(event));
  }

  private deriveStepLabel(event: ProgressEvent): string {
    const data = (event.data?.['data'] as Record<string, unknown>) ?? event.data;
    if (event.event === 'generating_slide') {
      const idx = data['slide_index'] as number | undefined;
      const total = data['total'] as number | undefined;
      if (idx !== undefined && total !== undefined) {
        this.slideIndex.set(idx);
        this.slideTotal.set(total);
        return `Generating slide ${idx + 1} of ${total}...`;
      }
    }
    if (event.event === 'repairing') {
      const retry = data['retry_count'] as number | undefined;
      if (retry !== undefined) {
        return `Fixing issues (attempt ${retry})...`;
      }
    }
    return STEP_LABELS[event.event] ?? event.event;
  }

  private estimateProgress(event: ProgressEvent): number {
    const range = PROGRESS_RANGES[event.event];
    if (!range) return this.progressPct();
    const [min, max] = range;

    if (event.event === 'generating_slide') {
      const data = (event.data?.['data'] as Record<string, unknown>) ?? event.data;
      const idx = data['slide_index'] as number | undefined;
      const total = data['total'] as number | undefined;
      if (idx !== undefined && total !== undefined && total > 0) {
        return Math.round(min + ((idx + 1) / total) * (max - min));
      }
    }

    const current = this.progressPct();
    const mid = Math.round((min + max) / 2);
    return Math.max(current, mid);
  }
}
