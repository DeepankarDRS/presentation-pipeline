import { Component, inject } from '@angular/core';
import { GenerationService } from './services/generation.service';
import { LayoutComponent } from './components/layout/layout.component';
import { PromptFormComponent } from './components/prompt-form/prompt-form.component';
import { ProgressViewComponent } from './components/progress-view/progress-view.component';
import { ResultViewComponent } from './components/result-view/result-view.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [LayoutComponent, PromptFormComponent, ProgressViewComponent, ResultViewComponent],
  template: `
    <app-layout>
      @switch (generation.view()) {
        @case ('form') {
          <app-prompt-form (generate)="generation.generate($event)" />
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
