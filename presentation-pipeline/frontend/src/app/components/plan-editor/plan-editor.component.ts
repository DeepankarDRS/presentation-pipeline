import { Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GenerationService } from '../../services/generation.service';
import { ComponentKind, OutlineSlide, SlideType } from '../../models/api.models';

const SLIDE_TYPE_COLORS: Record<string, string> = {
  cover: 'bg-purple-100 text-purple-700',
  content: 'bg-blue-100 text-blue-700',
  data: 'bg-green-100 text-green-700',
  section_break: 'bg-yellow-100 text-yellow-700',
  closing: 'bg-gray-100 text-gray-700',
};

const SLIDE_TYPES: SlideType[] = ['cover', 'content', 'data', 'section_break', 'closing'];

const COMPONENT_KINDS: ComponentKind[] = [
  'title', 'narrative', 'caption', 'kpi_row', 'bullet_list',
  'chart', 'table', 'timeline', 'flow', 'layer',
  'tree', 'matrix', 'process_arrow', 'pyramid',
];

function emptyOutlineSlide(index: number): OutlineSlide {
  return {
    slide_index: index,
    slide_title: '',
    slide_type: 'content',
    section: '',
    narrative_role: '',
    key_messages: [],
    data_anchors: [],
    layout_intent: '',
    suggested_components: ['title'],
  };
}

@Component({
  selector: 'app-plan-editor',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-900">Review Deck Outline</h2>
          <p class="text-sm text-gray-500">Edit the narrative and slide structure, then generate.</p>
        </div>
        <span class="text-sm text-gray-400">{{ slides().length }} slide{{ slides().length === 1 ? '' : 's' }}</span>
      </div>

      @if (generation.outlineError()) {
        <p class="text-sm text-red-600 bg-red-50 rounded-lg p-3 mb-4">{{ generation.outlineError() }}</p>
      }

      <!-- Deck title -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">Deck Title</label>
        <input
          type="text"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          [ngModel]="deckTitle()"
          (ngModelChange)="deckTitle.set($event)"
        />
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
        @for (slide of slides(); track $index; let i = $index) {
          <div class="border border-gray-200 rounded-lg overflow-hidden">
            <!-- Card header -->
            <div class="flex items-center gap-3 px-4 py-3 bg-white">
              <span class="text-sm font-medium text-gray-400 w-6">{{ i + 1 }}</span>
              <span class="text-xs font-medium px-2 py-0.5 rounded-full {{ slideTypeColor(slide.slide_type) }}">
                {{ slide.slide_type }}
              </span>
              <span class="flex-1 text-sm text-gray-700 truncate">{{ slide.slide_title || '(untitled slide)' }}</span>

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
              <div class="border-t border-gray-100 p-4 space-y-4 bg-gray-50">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-medium text-gray-600 mb-1">Slide title</label>
                    <input type="text" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm"
                      [ngModel]="slide.slide_title" (ngModelChange)="patchSlide(i, { slide_title: $event })" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-600 mb-1">Slide type</label>
                    <select class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm"
                      [ngModel]="slide.slide_type" (ngModelChange)="patchSlide(i, { slide_type: $event })">
                      @for (t of slideTypes; track t) {
                        <option [value]="t">{{ t }}</option>
                      }
                    </select>
                  </div>
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1">Section</label>
                  <input type="text" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm"
                    [ngModel]="slide.section" (ngModelChange)="patchSlide(i, { section: $event })"
                    placeholder="e.g. Problem, Deep Dive, Recommendation" />
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1">Narrative role</label>
                  <textarea rows="2" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm resize-y"
                    [ngModel]="slide.narrative_role" (ngModelChange)="patchSlide(i, { narrative_role: $event })"
                    placeholder="How does this slide advance the core hook?"></textarea>
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1">Key messages</label>
                  <div class="flex flex-wrap gap-1.5 mb-1.5">
                    @for (msg of slide.key_messages; track $index; let mi = $index) {
                      <span class="inline-flex items-center gap-1 text-xs bg-white border border-gray-200 text-gray-700 px-2 py-1 rounded-full">
                        {{ msg }}
                        <button type="button" (click)="removeListItem(i, 'key_messages', mi)" class="text-gray-400 hover:text-red-500">&times;</button>
                      </span>
                    }
                  </div>
                  <div class="flex gap-1.5">
                    <input type="text" class="flex-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm"
                      [(ngModel)]="newKeyMessage[i]" (keydown.enter)="$event.preventDefault(); commitKeyMessage(i)"
                      placeholder="e.g. Revenue grew 34% YoY to $2.1B" />
                    <button type="button" (click)="commitKeyMessage(i)"
                      class="px-3 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-100">+</button>
                  </div>
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1">Data anchors</label>
                  <div class="flex flex-wrap gap-1.5 mb-1.5">
                    @for (anchor of slide.data_anchors; track $index; let ai = $index) {
                      <span class="inline-flex items-center gap-1 text-xs bg-white border border-gray-200 text-gray-700 px-2 py-1 rounded-full">
                        {{ anchor }}
                        <button type="button" (click)="removeListItem(i, 'data_anchors', ai)" class="text-gray-400 hover:text-red-500">&times;</button>
                      </span>
                    }
                  </div>
                  <div class="flex gap-1.5">
                    <input type="text" class="flex-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm"
                      [(ngModel)]="newDataAnchor[i]" (keydown.enter)="$event.preventDefault(); commitDataAnchor(i)"
                      placeholder="e.g. ARR: $12M" />
                    <button type="button" (click)="commitDataAnchor(i)"
                      class="px-3 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-100">+</button>
                  </div>
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1">Layout intent</label>
                  <textarea rows="2" class="w-full rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm resize-y"
                    [ngModel]="slide.layout_intent" (ngModelChange)="patchSlide(i, { layout_intent: $event })"
                    placeholder="e.g. Three-column comparison grid with a verdict column"></textarea>
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1.5">Suggested components</label>
                  <div class="flex flex-wrap gap-1.5">
                    @for (kind of componentKinds; track kind) {
                      <button type="button" (click)="toggleComponent(i, kind)"
                        [class.bg-blue-600]="slide.suggested_components.includes(kind)"
                        [class.text-white]="slide.suggested_components.includes(kind)"
                        [class.border-blue-600]="slide.suggested_components.includes(kind)"
                        [class.text-gray-600]="!slide.suggested_components.includes(kind)"
                        [class.border-gray-200]="!slide.suggested_components.includes(kind)"
                        class="text-xs font-medium px-2.5 py-1 rounded-full border hover:border-blue-300 transition-colors"
                      >{{ kind }}</button>
                    }
                  </div>
                </div>
              </div>
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

      <!-- Actions -->
      <div class="flex gap-3">
        <button
          type="button"
          (click)="generation.reset()"
          class="flex-1 border border-gray-300 text-gray-700 font-medium py-2.5 px-4 rounded-lg hover:bg-gray-50"
        >Back</button>
        <button
          type="button"
          (click)="onConfirm()"
          class="flex-1 bg-blue-600 text-white font-medium py-2.5 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
          [disabled]="!isValid()"
        >Generate Presentation</button>
      </div>
    </div>
  `,
})
export class PlanEditorComponent {
  protected readonly generation = inject(GenerationService);

  readonly deckTitle = signal('');
  readonly coreHook = signal('');
  readonly slides = signal<OutlineSlide[]>([]);
  readonly expandedIndex = signal<number | null>(null);

  readonly slideTypes = SLIDE_TYPES;
  readonly componentKinds = COMPONENT_KINDS;

  // Scratch input state for the tag-list editors, keyed by slide index.
  newKeyMessage: Record<number, string> = {};
  newDataAnchor: Record<number, string> = {};

  constructor() {
    effect(() => {
      const outline = this.generation.outlinePlan();
      if (outline) {
        this.deckTitle.set(outline.deck_title);
        this.coreHook.set(outline.core_hook);
        this.slides.set(structuredClone(outline.slides));
        this.expandedIndex.set(null);
      }
    });
  }

  slideTypeColor(type: string): string {
    return SLIDE_TYPE_COLORS[type] ?? 'bg-gray-100 text-gray-700';
  }

  isValid(): boolean {
    const s = this.slides();
    return s.length >= 1 && s.length <= 20;
  }

  toggleExpand(index: number): void {
    this.expandedIndex.set(this.expandedIndex() === index ? null : index);
  }

  patchSlide(index: number, patch: Partial<OutlineSlide>): void {
    this.slides.update(slides =>
      slides.map((s, i) => i === index ? { ...s, ...patch } : s)
    );
  }

  addListItem(index: number, field: 'key_messages' | 'data_anchors', value: string): void {
    const trimmed = value.trim();
    if (!trimmed) return;
    this.slides.update(slides =>
      slides.map((s, i) => i === index ? { ...s, [field]: [...s[field], trimmed] } : s)
    );
  }

  commitKeyMessage(index: number): void {
    this.addListItem(index, 'key_messages', this.newKeyMessage[index] ?? '');
    this.newKeyMessage[index] = '';
  }

  commitDataAnchor(index: number): void {
    this.addListItem(index, 'data_anchors', this.newDataAnchor[index] ?? '');
    this.newDataAnchor[index] = '';
  }

  removeListItem(index: number, field: 'key_messages' | 'data_anchors', itemIndex: number): void {
    this.slides.update(slides =>
      slides.map((s, i) => i === index ? { ...s, [field]: s[field].filter((_, j) => j !== itemIndex) } : s)
    );
  }

  toggleComponent(index: number, kind: ComponentKind): void {
    this.slides.update(slides =>
      slides.map((s, i) => {
        if (i !== index) return s;
        const has = s.suggested_components.includes(kind);
        return {
          ...s,
          suggested_components: has
            ? s.suggested_components.filter(k => k !== kind)
            : [...s.suggested_components, kind],
        };
      })
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
    this.slides.update(slides => [...slides, emptyOutlineSlide(slides.length)]);
  }

  onConfirm(): void {
    this.generation.confirmOutline({
      deck_title: this.deckTitle(),
      core_hook: this.coreHook(),
      slides: this.slides(),
    });
  }
}
