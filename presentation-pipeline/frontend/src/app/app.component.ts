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
            <div class="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
              {{ generation.error() }}
            </div>
          }
          <app-prompt-form (generate)="generation.requestOutline($event)" />
        }
        @case ('planning') {
          <div class="flex flex-col items-center justify-center py-20">
            <div class="animate-spin rounded-full h-10 w-10 border-2 border-blue-600 border-t-transparent mb-4"></div>
            <p class="text-sm text-gray-500">Planning your deck...</p>
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
