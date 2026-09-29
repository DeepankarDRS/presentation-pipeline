import { Component, computed, inject } from '@angular/core';
import { GenerationService } from '../../services/generation.service';

interface FlowStep {
  label: string;
  views: string[];
}

const FLOW_STEPS: FlowStep[] = [
  { label: 'Prompt',   views: ['form', 'planning', 'elicitation'] },
  { label: 'Outline',  views: ['plan-editor'] },
  { label: 'Generate', views: ['progress'] },
  { label: 'Review',   views: ['result', 'review'] },
];

@Component({
  selector: 'app-layout',
  standalone: true,
  template: `
    <div class="min-h-screen bg-slate-50 bg-[radial-gradient(ellipse_at_top,_rgba(30,111,232,0.08),_transparent_60%)]">
      <header class="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/80">
        <div class="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-indigo-600 flex items-center justify-center shadow-md shadow-brand-600/20">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 5a1 1 0 011-1h14a1 1 0 011 1v10a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM8 20h8M12 16v4M8 12V9m4 3V7m4 5v-2" />
              </svg>
            </div>
            <div>
              <h1 class="text-base font-semibold text-slate-900 leading-tight">Presentation Pipeline</h1>
              <p class="text-[11px] text-slate-500 leading-tight">AI-generated, editable decks</p>
            </div>
          </div>

          <nav aria-label="Progress" class="hidden md:flex items-center gap-1">
            @for (step of steps; track step.label; let i = $index; let last = $last) {
              <div class="flex items-center gap-1">
                <div
                  class="flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
                  [class.bg-brand-50]="i === activeIndex()"
                  [class.text-brand-700]="i === activeIndex()"
                  [class.text-slate-700]="i < activeIndex()"
                  [class.text-slate-400]="i > activeIndex()"
                >
                  <span
                    class="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold"
                    [class.bg-brand-600]="i === activeIndex()"
                    [class.text-white]="i <= activeIndex()"
                    [class.bg-emerald-500]="i < activeIndex()"
                    [class.bg-slate-200]="i > activeIndex()"
                    [class.text-slate-500]="i > activeIndex()"
                  >
                    @if (i < activeIndex()) {
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    } @else {
                      {{ i + 1 }}
                    }
                  </span>
                  {{ step.label }}
                </div>
                @if (!last) {
                  <div class="h-px w-5" [class.bg-emerald-400]="i < activeIndex()" [class.bg-slate-200]="i >= activeIndex()"></div>
                }
              </div>
            }
          </nav>
        </div>
      </header>
      <main class="max-w-5xl mx-auto px-6 py-8">
        <ng-content />
      </main>
    </div>
  `,
})
export class LayoutComponent {
  private readonly generation = inject(GenerationService);
  readonly steps = FLOW_STEPS;
  readonly activeIndex = computed(() => {
    const view = this.generation.view();
    const idx = FLOW_STEPS.findIndex(s => s.views.includes(view));
    return idx === -1 ? 0 : idx;
  });
}
