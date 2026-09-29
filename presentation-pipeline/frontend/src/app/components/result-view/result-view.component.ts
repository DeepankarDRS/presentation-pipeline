import { Component, inject, output } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { GenerationService } from '../../services/generation.service';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-result-view',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    @if (gen.error()) {
      <!-- Error state -->
      <div class="card overflow-hidden">
        <div class="px-6 py-8 bg-gradient-to-br from-red-50 via-white to-white flex flex-col items-center text-center">
          <div class="w-14 h-14 rounded-full bg-red-100 ring-8 ring-red-50 flex items-center justify-center mb-4">
            <svg class="w-7 h-7 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 class="text-xl font-semibold text-slate-900">Generation Failed</h2>
          <p class="text-sm text-slate-500 mt-1">Something went wrong while building your deck.</p>
        </div>
        <div class="px-6 pb-6">
          <p class="text-xs text-red-700 bg-red-50 border border-red-200 rounded-xl p-3 mb-5 font-mono break-words">{{ gen.error() }}</p>
          <button (click)="resetEmit.emit()" class="btn-primary w-full">Try Again</button>
        </div>
      </div>
    } @else {
      <!-- Success state -->
      <div class="card overflow-hidden">
        <div class="px-6 py-8 bg-gradient-to-br from-emerald-50 via-white to-brand-50/40 flex flex-col items-center text-center border-b border-slate-100">
          <div class="w-16 h-16 rounded-full bg-emerald-500 ring-8 ring-emerald-100 flex items-center justify-center mb-4 shadow-lg shadow-emerald-500/20">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 class="text-2xl font-semibold text-slate-900">Presentation Ready</h2>
          <div class="flex flex-wrap items-center justify-center gap-2 mt-3">
            @if (gen.passed()) {
              <span class="badge bg-emerald-100 text-emerald-800">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Quality Check Passed
              </span>
            } @else {
              <span class="badge bg-amber-100 text-amber-800">
                <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                Quality Check: Review Recommended
              </span>
            }
            @if (gen.evaluationSummary()?.excluded_slides?.length) {
              <span class="badge bg-orange-100 text-orange-800">
                {{ gen.evaluationSummary()!.excluded_slides!.length }} slide(s) excluded
              </span>
            }
          </div>
        </div>

        <div class="p-6 space-y-4">
          @if (gen.planReview(); as review) {
            <div class="rounded-xl border p-4" [class]="review.approved ? 'bg-emerald-50/50 border-emerald-200' : 'bg-amber-50/50 border-amber-200'">
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-semibold text-slate-900">Plan Quality</span>
                <span class="text-sm font-semibold tabular-nums" [class]="review.approved ? 'text-emerald-700' : 'text-amber-700'">
                  {{ (review.confidence_score * 100).toFixed(0) }}% confidence
                </span>
              </div>
              <div class="h-2 w-full rounded-full bg-white border border-slate-200 overflow-hidden mb-2">
                <div
                  class="h-full rounded-full transition-all duration-700"
                  [class]="review.approved ? 'bg-emerald-500' : 'bg-amber-500'"
                  [style.width.%]="review.confidence_score * 100"
                ></div>
              </div>
              @if (review.summary) {
                <p class="text-xs text-slate-600">{{ review.summary }}</p>
              }
              @if (review.issues.length > 0) {
                <ul class="mt-2 space-y-1">
                  @for (issue of review.issues; track $index) {
                    <li class="flex items-start gap-2 text-xs text-slate-600">
                      <span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400"></span>
                      {{ issue.description }}
                    </li>
                  }
                </ul>
              }
            </div>
          }

          @if (gen.evaluationSummary(); as summary) {
            @if (summary.tokens || summary.cost) {
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                @if (summary.tokens) {
                  <div class="stat-tile">
                    <p class="text-[11px] font-medium uppercase tracking-wide text-slate-500">Tokens In</p>
                    <p class="text-lg font-semibold text-slate-900 tabular-nums mt-0.5">{{ summary.tokens.total_in | number }}</p>
                  </div>
                  <div class="stat-tile">
                    <p class="text-[11px] font-medium uppercase tracking-wide text-slate-500">Tokens Out</p>
                    <p class="text-lg font-semibold text-slate-900 tabular-nums mt-0.5">{{ summary.tokens.total_out | number }}</p>
                  </div>
                }
                @if (summary.cost) {
                  <div class="stat-tile">
                    <p class="text-[11px] font-medium uppercase tracking-wide text-slate-500">Cost</p>
                    <p class="text-lg font-semibold text-slate-900 tabular-nums mt-0.5">{{'$'}}{{ summary.cost.total_usd.toFixed(4) }}</p>
                  </div>
                  <div class="stat-tile">
                    <p class="text-[11px] font-medium uppercase tracking-wide text-slate-500">Models</p>
                    <p class="text-sm font-semibold text-slate-900 mt-1 truncate" [title]="summary.cost.models_used.join(', ')">
                      {{ summary.cost.models_used.join(', ') }}
                    </p>
                  </div>
                }
              </div>
            }
          }
        </div>

        <div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row gap-3">
          @if (gen.runId()) {
            <a [href]="api.getDownloadUrl(gen.runId()!)" download class="btn-primary flex-1">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4" />
              </svg>
              Download PPTX
            </a>
            <button (click)="gen.startReview()" class="btn-secondary flex-1">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Review & Edit Slides
            </button>
          }
          <button (click)="resetEmit.emit()" class="btn-ghost flex-1">New Presentation</button>
        </div>
      </div>
    }
  `,
})
export class ResultViewComponent {
  readonly gen = inject(GenerationService);
  readonly api = inject(ApiService);
  readonly resetEmit = output<void>();
}
