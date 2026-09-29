import { Component, inject } from '@angular/core';
import { GenerationService } from './services/generation.service';
import { LayoutComponent } from './components/layout/layout.component';
import { PromptFormComponent } from './components/prompt-form/prompt-form.component';
import { ElicitationFormComponent } from './components/elicitation-form/elicitation-form.component';
import { PlanEditorComponent } from './components/plan-editor/plan-editor.component';
import { ProgressViewComponent } from './components/progress-view/progress-view.component';
import { ResultViewComponent } from './components/result-view/result-view.component';
import { SlideReviewComponent } from './components/slide-review/slide-review.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [LayoutComponent, PromptFormComponent, ElicitationFormComponent, PlanEditorComponent, ProgressViewComponent, ResultViewComponent, SlideReviewComponent],
  template: `
    <app-layout>
      @switch (generation.view()) {
        @case ('form') {
          @if (generation.error()) {
            <div class="mb-4 flex items-start gap-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3.5">
              <svg class="w-5 h-5 shrink-0 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
              <span>{{ generation.error() }}</span>
            </div>
          }
          <app-prompt-form (generate)="generation.requestOutline($event)" />
        }
        @case ('planning') {
          <div class="card flex flex-col items-center justify-center py-20">
            <div class="relative mb-5">
              <div class="absolute inset-0 rounded-full bg-brand-200 animate-ping opacity-40"></div>
              <div class="relative flex h-14 w-14 items-center justify-center rounded-full bg-brand-50">
                <div class="spinner h-8 w-8"></div>
              </div>
            </div>
            <p class="text-sm font-semibold text-slate-900">Planning your deck</p>
            <p class="text-xs text-slate-500 mt-1">Drafting the storyline and slide outline...</p>
          </div>
        }
        @case ('elicitation') {
          <app-elicitation-form />
        }
        @case ('plan-editor') {
          <app-plan-editor />
        }
        @case ('progress') {
          <app-progress-view (cancel)="generation.cancel()" />
        }
        @case ('result') {
          <app-result-view (resetEmit)="generation.reset()" />
        }
        @case ('review') {
          <app-slide-review />
        }
      }
    </app-layout>
  `,
})
export class AppComponent {
  readonly generation = inject(GenerationService);
}
