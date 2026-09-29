import { Component, inject, output } from '@angular/core';
import { GenerationService } from '../../services/generation.service';
import { PIPELINE_PHASES } from '../../constants/theme.constants';

@Component({
  selector: 'app-progress-view',
  standalone: true,
  template: `
    <div class="card overflow-hidden">
      <div class="px-6 pt-6 pb-6 bg-gradient-to-br from-brand-50 via-white to-white border-b border-slate-100">
        <div class="flex items-start justify-between gap-4 mb-5">
          <div>
            <h2 class="text-xl font-semibold text-slate-900">Generating your presentation</h2>
            <p class="text-sm text-slate-500 mt-1">{{ gen.stepLabel() }}</p>
          </div>
          <span class="text-2xl font-semibold text-brand-700 tabular-nums">{{ gen.progressPct().toFixed(0) }}%</span>
        </div>

        <!-- Progress bar -->
        <div class="relative w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
          <div
            class="h-full rounded-full bg-gradient-to-r from-brand-500 via-indigo-500 to-brand-600 transition-all duration-500 ease-out"
            [style.width.%]="gen.progressPct()"
          ></div>
          <div class="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.45),transparent)] animate-pulse"></div>
        </div>
      </div>

      <!-- Phase stepper -->
      <ol class="px-6 py-6">
        @for (phase of phases; track phase.label; let i = $index; let last = $last) {
          <li class="relative flex gap-4" [class.pb-5]="!last">
            @if (!last) {
              <span
                class="absolute left-[13px] top-7 bottom-0 w-0.5 rounded-full"
                [class.bg-emerald-300]="getPhaseStatus(i) === 'completed'"
                [class.bg-slate-200]="getPhaseStatus(i) !== 'completed'"
              ></span>
            }

            @if (getPhaseStatus(i) === 'completed') {
              <div class="relative z-10 w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center shrink-0 shadow-sm">
                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            } @else if (getPhaseStatus(i) === 'active') {
              <div class="relative z-10 w-7 h-7 rounded-full bg-brand-50 ring-4 ring-brand-100 flex items-center justify-center shrink-0">
                <div class="spinner h-4 w-4"></div>
              </div>
            } @else {
              <div class="relative z-10 w-7 h-7 rounded-full bg-white border-2 border-slate-200 flex items-center justify-center shrink-0">
                <span class="text-[10px] font-semibold text-slate-400">{{ i + 1 }}</span>
              </div>
            }

            <div class="pt-1 min-w-0">
              <p
                class="text-sm"
                [class.text-slate-700]="getPhaseStatus(i) === 'completed'"
                [class.text-slate-900]="getPhaseStatus(i) === 'active'"
                [class.font-semibold]="getPhaseStatus(i) === 'active'"
                [class.text-slate-400]="getPhaseStatus(i) === 'pending'"
              >
                {{ phase.label }}
              </p>
              @if (getPhaseStatus(i) === 'active' && gen.currentStep() === 'generating_slide' && gen.slideIndex() !== null) {
                <p class="text-xs text-brand-600 mt-0.5">
                  Slide {{ gen.slideIndex()! + 1 }} of {{ gen.slideTotal() }}
                </p>
              }
            </div>
          </li>
        }
      </ol>

      <div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end">
        <button (click)="cancel.emit()" class="btn-ghost">Cancel</button>
      </div>
    </div>
  `,
})
export class ProgressViewComponent {
  readonly gen = inject(GenerationService);
  readonly cancel = output<void>();
  readonly phases = PIPELINE_PHASES;

  private readonly phaseEventSet = PIPELINE_PHASES.map(p => new Set(p.events));

  getPhaseStatus(index: number): 'completed' | 'active' | 'pending' {
    const current = this.gen.currentStep();
    if (!current) {
      return index === 0 ? 'active' : 'pending';
    }

    const currentPhaseIndex = this.phaseEventSet.findIndex(s => s.has(current));

    if (index < currentPhaseIndex) return 'completed';
    if (index === currentPhaseIndex) return 'active';
    return 'pending';
  }
}
