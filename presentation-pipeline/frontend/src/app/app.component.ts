import { Component, inject } from '@angular/core';
import { GenerationService } from './services/generation.service';
import { LayoutComponent } from './components/layout/layout.component';
import { PromptFormComponent } from './components/prompt-form/prompt-form.component';
import { PlanEditorComponent } from './components/plan-editor/plan-editor.component';
import { ProgressViewComponent } from './components/progress-view/progress-view.component';
import { ResultViewComponent } from './components/result-view/result-view.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [LayoutComponent, PromptFormComponent, PlanEditorComponent, ProgressViewComponent, ResultViewComponent],
  template: `
    <app-layout>
      @switch (generation.view()) {
        @case ('form') {
          <app-prompt-form (generate)="generation.requestPlan($event)" />
        }
        @case ('planning') {
          <div class="flex flex-col items-center justify-center py-20">
            <div class="animate-spin rounded-full h-10 w-10 border-2 border-blue-600 border-t-transparent mb-4"></div>
            <p class="text-sm text-gray-500">Creating slide plan...</p>
          </div>
        }
        @case ('plan-editor') {
          <app-plan-editor
            (confirm)="generation.generateFromPlan($event.core_hook, $event.slides)"
            (back)="generation.reset()"
          />
        }
        @case ('progress') {
          <app-progress-view (cancel)="generation.cancel()" />
        }
        @case ('result') {
          <app-result-view (resetEmit)="generation.reset()" />
        }
      }
    </app-layout>
  `,
})
export class AppComponent {
  readonly generation = inject(GenerationService);
}
