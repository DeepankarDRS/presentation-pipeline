import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GenerationService } from '../../services/generation.service';

/**
 * Phase B follow-up questions — shown only when the elicitor decides the
 * user's prompt is still too vague to outline confidently. Answers feed
 * back into a second POST /plan/outline call alongside the original prompt.
 */
@Component({
  selector: 'app-elicitation-form',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-1">A few quick questions</h2>
      <p class="text-sm text-gray-500 mb-6">
        Your prompt could use a bit more detail — answer what applies, skip the rest.
      </p>

      @if (generation.elicitationError()) {
        <p class="text-sm text-red-600 bg-red-50 rounded-lg p-3 mb-4">{{ generation.elicitationError() }}</p>
      }

      <div class="space-y-5 mb-6">
        @for (q of generation.elicitationQuestions(); track q.key) {
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">{{ q.question }}</label>
            @if (q.options.length > 0) {
              <div class="flex flex-wrap gap-1.5">
                @for (opt of q.options; track opt) {
                  <button
                    type="button"
                    (click)="setAnswer(q.key, opt)"
                    [class.bg-blue-600]="answers()[q.key] === opt"
                    [class.text-white]="answers()[q.key] === opt"
                    [class.border-blue-600]="answers()[q.key] === opt"
                    [class.text-gray-600]="answers()[q.key] !== opt"
                    [class.border-gray-200]="answers()[q.key] !== opt"
                    class="text-xs font-medium px-2.5 py-1 rounded-full border hover:border-blue-300 transition-colors"
                  >
                    {{ opt }}
                  </button>
                }
              </div>
            } @else {
              <input
                type="text"
                [ngModel]="answerFor(q.key)"
                (ngModelChange)="setAnswer(q.key, $event)"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Your answer..."
              />
            }
          </div>
        }
      </div>

      <div class="flex gap-3">
        <button
          type="button"
          (click)="generation.reset()"
          class="flex-1 border border-gray-300 text-gray-700 font-medium py-2.5 px-4 rounded-lg hover:bg-gray-50"
        >Back</button>
        <button
          type="button"
          (click)="onSubmit()"
          class="flex-1 bg-blue-600 text-white font-medium py-2.5 px-4 rounded-lg hover:bg-blue-700"
        >Continue</button>
      </div>
    </div>
  `,
})
export class ElicitationFormComponent {
  protected readonly generation = inject(GenerationService);
  readonly answers = signal<Record<string, string>>({});

  setAnswer(key: string, value: string): void {
    this.answers.update(a => ({ ...a, [key]: value }));
  }

  answerFor(key: string): string {
    return this.answers()[key] ?? '';
  }

  onSubmit(): void {
    this.generation.submitElicitationAnswers(this.answers());
  }
}
