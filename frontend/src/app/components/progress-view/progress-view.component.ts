import { Component, inject, output } from '@angular/core';
import { GenerationService } from '../../services/generation.service';
import { PIPELINE_PHASES } from '../../constants/theme.constants';

@Component({
  selector: 'app-progress-view',
  standalone: true,
  template: `
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-1">Generating your presentation</h2>
      <p class="text-sm text-gray-500 mb-6">{{ gen.stepLabel() }}</p>

      <!-- Progress bar -->
      <div class="w-full bg-gray-100 rounded-full h-2.5 mb-8">
        <div
          class="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
          [style.width.%]="gen.progressPct()"
        ></div>
      </div>

      <!-- Phase timeline -->
      <div class="space-y-3">
        @for (phase of phases; track phase.label; let i = $index) {
          <div class="flex items-center gap-3">
            <!-- Status icon -->
            @if (getPhaseStatus(i) === 'completed') {
              <div class="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            } @else if (getPhaseStatus(i) === 'active') {
              <div class="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                <div class="w-2.5 h-2.5 rounded-full bg-blue-600 animate-pulse"></div>
              </div>
            } @else {
              <div class="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center shrink-0">
                <div class="w-2 h-2 rounded-full bg-gray-300"></div>
              </div>
            }

            <span
              class="text-sm"
              [class.text-gray-900]="getPhaseStatus(i) !== 'pending'"
              [class.font-medium]="getPhaseStatus(i) === 'active'"
              [class.text-gray-400]="getPhaseStatus(i) === 'pending'"
            >
              {{ phase.label }}
              @if (getPhaseStatus(i) === 'active' && gen.currentStep() === 'generating_slide' && gen.slideIndex() !== null) {
                <span class="text-gray-500 font-normal">
                  (slide {{ gen.slideIndex()! + 1 }} of {{ gen.slideTotal() }})
                </span>
              }
            </span>
          </div>
        }
      </div>

      <div class="mt-8 flex justify-end">
        <button
          (click)="cancel.emit()"
          class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
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
