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
      <div class="bg-white rounded-xl shadow-sm border border-red-200 p-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
            <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 class="text-xl font-semibold text-gray-900">Generation Failed</h2>
        </div>
        <p class="text-sm text-red-600 bg-red-50 rounded-lg p-3 mb-6 font-mono">{{ gen.error() }}</p>
        <button
          (click)="resetEmit.emit()"
          class="w-full bg-gray-900 text-white font-medium py-2.5 px-4 rounded-lg hover:bg-gray-800 transition-colors"
        >
          Try Again
        </button>
      </div>
    } @else {
      <!-- Success state -->
      <div class="bg-white rounded-xl shadow-sm border border-green-200 p-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center shrink-0">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <h2 class="text-xl font-semibold text-gray-900">Presentation Ready</h2>
            <div class="flex items-center gap-2 mt-0.5">
              @if (gen.passed()) {
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  Quality Check Passed
                </span>
              } @else {
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                  Quality Check: Review Recommended
                </span>
              }
            </div>
          </div>
        </div>

        @if (gen.planReview(); as review) {
          <div class="rounded-lg p-4 mb-4 border" [class]="review.approved ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium text-gray-900">Plan Quality</span>
              <span class="text-xs font-medium px-2 py-0.5 rounded-full"
                [class]="review.approved ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'">
                {{ (review.confidence_score * 100).toFixed(0) }}% confidence
              </span>
            </div>
            @if (review.summary) {
              <p class="text-xs text-gray-600 mb-1">{{ review.summary }}</p>
            }
            @if (review.issues.length > 0) {
              <ul class="text-xs text-gray-600 list-disc list-inside mt-1 space-y-0.5">
                @for (issue of review.issues; track $index) {
                  <li>{{ issue.description }}</li>
                }
              </ul>
            }
          </div>
        }

        @if (gen.evaluationSummary()) {
          <div class="bg-gray-50 rounded-lg p-4 mb-6 grid grid-cols-2 gap-3 text-sm">
            @if (gen.evaluationSummary()!.tokens) {
              <div>
                <span class="text-gray-500">Tokens In</span>
                <p class="font-medium text-gray-900">{{ gen.evaluationSummary()!.tokens!.total_in | number }}</p>
              </div>
              <div>
                <span class="text-gray-500">Tokens Out</span>
                <p class="font-medium text-gray-900">{{ gen.evaluationSummary()!.tokens!.total_out | number }}</p>
              </div>
            }
            @if (gen.evaluationSummary()!.cost) {
              <div>
                <span class="text-gray-500">Cost</span>
                <p class="font-medium text-gray-900">{{'$'}}{{ gen.evaluationSummary()!.cost!.total_usd.toFixed(4) }}</p>
              </div>
              <div>
                <span class="text-gray-500">Models</span>
                <p class="font-medium text-gray-900">{{ gen.evaluationSummary()!.cost!.models_used.join(', ') }}</p>
              </div>
            }
          </div>
        }

        <div class="flex gap-3">
          @if (gen.runId()) {
            <a
              [href]="api.getDownloadUrl(gen.runId()!)"
              download
              class="flex-1 bg-blue-600 text-white font-medium py-2.5 px-4 rounded-lg hover:bg-blue-700 transition-colors text-center"
            >
              Download PPTX
            </a>
            <button
              (click)="gen.startReview()"
              class="flex-1 bg-indigo-600 text-white font-medium py-2.5 px-4 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Review & Edit Slides
            </button>
          }
          <button
            (click)="resetEmit.emit()"
            class="flex-1 bg-white text-gray-700 font-medium py-2.5 px-4 rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
          >
            New Presentation
          </button>
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
