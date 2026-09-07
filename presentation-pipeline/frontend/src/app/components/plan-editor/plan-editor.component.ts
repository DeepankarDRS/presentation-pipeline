import { Component, effect, inject, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GenerationService } from '../../services/generation.service';
import { SlideEditorComponent } from '../slide-editor/slide-editor.component';
import { SlidePlan, ComponentPlan } from '../../models/api.models';

const SLIDE_TYPE_COLORS: Record<string, string> = {
  cover: 'bg-purple-100 text-purple-700',
  content: 'bg-blue-100 text-blue-700',
  data: 'bg-green-100 text-green-700',
  section_break: 'bg-yellow-100 text-yellow-700',
  closing: 'bg-gray-100 text-gray-700',
};

function componentLabel(c: ComponentPlan): string {
  if (c.kind === 'chart') return `chart: ${c.chart_type || '?'}`;
  if (c.kind === 'table') return `table ${c.columns}×${c.rows}`;
  if (c.kind === 'kpi_row') return `kpi_row ×${c.count}`;
  if (['timeline', 'flow', 'process_arrow', 'pyramid', 'bullet_list'].includes(c.kind) && c.items > 0) {
    return `${c.kind} ×${c.items}`;
  }
  return c.kind;
}

@Component({
  selector: 'app-plan-editor',
  standalone: true,
  imports: [FormsModule, SlideEditorComponent],
  template: `
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-900">Review Slide Plan</h2>
          <p class="text-sm text-gray-500">Edit structure, reorder slides, then generate.</p>
        </div>
        <span class="text-sm text-gray-400">{{ slides().length }} slide{{ slides().length === 1 ? '' : 's' }}</span>
      </div>

      <!-- Core hook -->
      <div class="mb-5">
        <label class="block text-sm font-medium text-gray-700 mb-1">Core Hook</label>
        <textarea
          rows="2"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-y"
          [ngModel]="coreHook()"
          (ngModelChange)="coreHook.set($event)"
        ></textarea>
      </div>

      <!-- Slide cards -->
      <div class="space-y-3 mb-5">
        @for (slide of slides(); track slide.slide_index; let i = $index) {
          <div class="border border-gray-200 rounded-lg overflow-hidden">
            <!-- Card header -->
            <div class="flex items-center gap-3 px-4 py-3 bg-white">
              <span class="text-sm font-medium text-gray-400 w-6">{{ i + 1 }}</span>
              <span class="text-xs font-medium px-2 py-0.5 rounded-full {{ slideTypeColor(slide.slide_type) }}">
                {{ slide.slide_type }}
              </span>
              <span class="text-xs text-gray-400">{{ formatLabel(slide.layout_pattern) }}</span>
              <span class="text-xs text-gray-400">{{ slide.density }}</span>

              <!-- Component pills -->
              <div class="flex-1 flex flex-wrap gap-1">
                @for (comp of slide.components; track $index) {
                  <span class="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                    {{ compLabel(comp) }}
                  </span>
                }
              </div>

              <!-- Actions -->
              <div class="flex items-center gap-1 shrink-0">
                @if (i > 0) {
                  <button type="button" (click)="moveSlide(i, -1)"
                    class="p-1 text-gray-400 hover:text-gray-600" title="Move up">&#9650;</button>
                }
                @if (i < slides().length - 1) {
                  <button type="button" (click)="moveSlide(i, 1)"
                    class="p-1 text-gray-400 hover:text-gray-600" title="Move down">&#9660;</button>
                }
                <button type="button" (click)="toggleExpand(i)"
                  class="p-1 text-gray-400 hover:text-gray-600 text-sm"
                  [class.text-blue-600]="expandedIndex() === i"
                >{{ expandedIndex() === i ? 'Close' : 'Edit' }}</button>
                <button type="button" (click)="removeSlide(i)"
                  class="p-1 text-red-400 hover:text-red-600"
                  [disabled]="slides().length <= 1"
                  title="Delete slide">&times;</button>
              </div>
            </div>

            <!-- Expanded editor -->
            @if (expandedIndex() === i) {
              <app-slide-editor
                [slide]="slide"
                (changed)="updateSlide(i, $event)"
              />
            }
          </div>
        }
      </div>

      <!-- Add slide -->
      <button
        type="button"
        (click)="addSlide()"
        class="w-full border-2 border-dashed border-gray-300 rounded-lg py-2 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 mb-5"
        [disabled]="slides().length >= 20"
      >+ Add Slide</button>

      <!-- Natural-language refinement -->
      <div class="mb-5 border-t border-gray-100 pt-5">
        <label class="block text-sm font-medium text-gray-700 mb-1">Refine with feedback</label>
        <p class="text-xs text-gray-500 mb-2">
          Describe changes in plain language — the planner revises the plan above, keeping what you don't mention.
        </p>
        <textarea
          rows="2"
          placeholder="e.g. add a section-break before the closing, and make slide 2 a KPI + chart dashboard"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-y"
          [ngModel]="feedbackText()"
          (ngModelChange)="feedbackText.set($event)"
          [disabled]="generation.refining()"
        ></textarea>
        @if (generation.refineError()) {
          <p class="text-xs text-red-600 mt-1">{{ generation.refineError() }}</p>
        }
        <button
          type="button"
          (click)="onRefine()"
          class="mt-2 inline-flex items-center gap-2 border border-blue-300 text-blue-700 text-sm font-medium py-2 px-4 rounded-lg hover:bg-blue-50 disabled:opacity-50"
          [disabled]="generation.refining() || !feedbackText().trim()"
        >
          @if (generation.refining()) {
            <span class="animate-spin rounded-full h-3.5 w-3.5 border-2 border-blue-600 border-t-transparent"></span>
            Refining...
          } @else {
            Refine plan
          }
        </button>
      </div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button
          type="button"
          (click)="back.emit()"
          class="flex-1 border border-gray-300 text-gray-700 font-medium py-2.5 px-4 rounded-lg hover:bg-gray-50"
        >Back</button>
        <button
          type="button"
          (click)="onConfirm()"
          class="flex-1 bg-blue-600 text-white font-medium py-2.5 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
          [disabled]="!isValid() || generation.refining()"
        >Generate Presentation</button>
      </div>
    </div>
  `,
})
export class PlanEditorComponent {
  protected readonly generation = inject(GenerationService);

  readonly confirm = output<{ core_hook: string; slides: SlidePlan[] }>();
  readonly back = output<void>();

  readonly coreHook = signal('');
  readonly slides = signal<SlidePlan[]>([]);
  readonly expandedIndex = signal<number | null>(null);
  readonly feedbackText = signal('');

  constructor() {
    // Load the plan into the editor, and reload it whenever a refinement
    // returns a new plan object.
    effect(() => {
      const plan = this.generation.deckPlan();
      if (plan) {
        this.coreHook.set(plan.core_hook);
        this.slides.set(structuredClone(plan.slides));
        this.expandedIndex.set(null);
      }
    });
  }

  onRefine(): void {
    this.generation.refinePlan(this.coreHook(), this.slides(), this.feedbackText());
    this.feedbackText.set('');
  }

  slideTypeColor(type: string): string {
    return SLIDE_TYPE_COLORS[type] ?? 'bg-gray-100 text-gray-700';
  }

  formatLabel(s: string): string {
    return s.replace(/_/g, ' ');
  }

  compLabel(c: ComponentPlan): string {
    return componentLabel(c);
  }

  isValid(): boolean {
    const s = this.slides();
    return s.length >= 1 && s.length <= 20 && s.every(sl => sl.components.length > 0);
  }

  toggleExpand(index: number): void {
    this.expandedIndex.set(this.expandedIndex() === index ? null : index);
  }

  updateSlide(index: number, updated: SlidePlan): void {
    this.slides.update(slides =>
      slides.map((s, i) => i === index ? { ...updated, slide_index: i } : s)
    );
  }

  moveSlide(index: number, direction: number): void {
    this.slides.update(slides => {
      const arr = [...slides];
      const target = index + direction;
      [arr[index], arr[target]] = [arr[target], arr[index]];
      return arr.map((s, i) => ({ ...s, slide_index: i }));
    });
  }

  removeSlide(index: number): void {
    this.slides.update(slides =>
      slides.filter((_, i) => i !== index).map((s, i) => ({ ...s, slide_index: i }))
    );
    if (this.expandedIndex() === index) this.expandedIndex.set(null);
  }

  addSlide(): void {
    const defaultSlide: SlidePlan = {
      slide_index: this.slides().length,
      slide_type: 'content',
      components: [{ kind: 'title', count: 1, chart_type: '', series_count: 0, columns: 0, rows: 0, items: 0, content_summary: '' }],
      density: 'normal',
      font_tier: 'standard',
      layout_pattern: 'two_column',
      layout_hint: '',
      content_data: {},
    };
    this.slides.update(slides => [...slides, defaultSlide]);
  }

  onConfirm(): void {
    this.confirm.emit({ core_hook: this.coreHook(), slides: this.slides() });
  }
}
