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
    <div class="card overflow-hidden">
      <div class="px-6 pt-6 pb-5 bg-gradient-to-br from-amber-50 via-white to-white border-b border-slate-100 flex items-start gap-4">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-semibold text-slate-900">A few quick questions</h2>
          <p class="text-sm text-slate-500 mt-1">
            Your prompt could use a bit more detail — answer what applies, skip the rest.
          </p>
        </div>
      </div>

      <div class="p-6">
        @if (generation.elicitationError()) {
          <p class="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3 mb-4">{{ generation.elicitationError() }}</p>
        }

        <div class="space-y-3">
          @for (q of generation.elicitationQuestions(); track q.key; let i = $index) {
            <div
              class="rounded-xl border p-4 transition-colors"
              [class.border-brand-200]="!!answers()[q.key]"
              [class.bg-brand-50]="!!answers()[q.key]"
              [class.border-slate-200]="!answers()[q.key]"
            >
              <div class="flex items-start gap-3">
                <span
                  class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
                  [class.bg-brand-600]="!!answers()[q.key]"
                  [class.text-white]="!!answers()[q.key]"
                  [class.bg-slate-100]="!answers()[q.key]"
                  [class.text-slate-500]="!answers()[q.key]"
                >{{ i + 1 }}</span>
                <div class="flex-1 min-w-0">
                  <label class="block text-sm font-medium text-slate-800 mb-2.5">{{ q.question }}</label>
                  @if (q.options.length > 0) {
                    <div class="flex flex-wrap gap-2">
                      @for (opt of q.options; track opt) {
                        <button
                          type="button"
                          (click)="setAnswer(q.key, opt)"
                          class="chip"
                          [class.chip-selected]="answers()[q.key] === opt"
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
                      class="input"
                      placeholder="Your answer..."
                    />
                  }
                </div>
              </div>
            </div>
          }
        </div>
      </div>

      <div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
        <button type="button" (click)="generation.reset()" class="btn-secondary">Back</button>
        <button type="button" (click)="onSubmit()" class="btn-primary min-w-[160px]">
          Continue
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>
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
