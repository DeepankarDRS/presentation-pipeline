import { Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GenerationService } from '../../services/generation.service';
import { OutlineSlide } from '../../models/api.models';

const SLIDE_TYPE_COLORS: Record<string, string> = {
  cover: 'bg-purple-100 text-purple-700',
  content: 'bg-blue-100 text-blue-700',
  data: 'bg-green-100 text-green-700',
  section_break: 'bg-yellow-100 text-yellow-700',
  closing: 'bg-gray-100 text-gray-700',
};

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

/**
 * Narrative-only outline review — deck title, core hook, and per-slide
 * title + key messages. Deliberately hides section/narrative_role/
 * layout_intent/suggested_components/data_anchors: those still travel on
 * each OutlineSlide and still reach slide_component_planner untouched,
 * they're just implementation detail a reviewer shouldn't have to read
 * through to judge whether the outline actually covers the core hook.
 */
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
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-start gap-3 mb-3">
              <span class="text-sm font-medium text-gray-400 w-6 pt-1.5">{{ i + 1 }}</span>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1.5">
                  <span class="text-xs font-medium px-2 py-0.5 rounded-full {{ slideTypeColor(slide.slide_type) }}">
                    {{ slide.slide_type }}
                  </span>
                </div>
                <input
                  type="text"
                  class="w-full font-medium text-gray-900 border-0 border-b border-transparent hover:border-gray-200 focus:border-blue-400 px-0 py-1 text-sm focus:outline-none"
                  [ngModel]="slide.slide_title"
                  (ngModelChange)="patchSlide(i, { slide_title: $event })"
                  placeholder="Slide title"
                />
              </div>
              <div class="flex items-center gap-1 shrink-0">
                @if (i > 0) {
                  <button type="button" (click)="moveSlide(i, -1)"
                    class="p-1 text-gray-400 hover:text-gray-600" title="Move up">&#9650;</button>
                }
                @if (i < slides().length - 1) {
                  <button type="button" (click)="moveSlide(i, 1)"
                    class="p-1 text-gray-400 hover:text-gray-600" title="Move down">&#9660;</button>
                }
                <button type="button" (click)="removeSlide(i)"
                  class="p-1 text-red-400 hover:text-red-600"
                  [disabled]="slides().length <= 1"
                  title="Delete slide">&times;</button>
              </div>
            </div>

            <!-- Key messages -->
            <div class="pl-9">
              <div class="space-y-1.5 mb-2">
                @for (msg of slide.key_messages; track $index; let mi = $index) {
                  <div class="flex items-start gap-2 text-sm text-gray-700">
                    <span class="text-gray-300 mt-0.5">&bull;</span>
                    <span class="flex-1">{{ msg }}</span>
                    <button type="button" (click)="removeListItem(i, mi)" class="text-gray-300 hover:text-red-500 shrink-0">&times;</button>
                  </div>
                }
              </div>
              <div class="flex gap-1.5">
                <input type="text" class="flex-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm"
                  [(ngModel)]="newKeyMessage[i]" (keydown.enter)="$event.preventDefault(); commitKeyMessage(i)"
                  placeholder="Add a key message..." />
                <button type="button" (click)="commitKeyMessage(i)"
                  class="px-3 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-100">+</button>
              </div>
            </div>
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

  // Scratch input state for the key-message list editor, keyed by slide index.
  newKeyMessage: Record<number, string> = {};

  constructor() {
    effect(() => {
      const outline = this.generation.outlinePlan();
      if (outline) {
        this.deckTitle.set(outline.deck_title);
        this.coreHook.set(outline.core_hook);
        this.slides.set(structuredClone(outline.slides));
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

  patchSlide(index: number, patch: Partial<OutlineSlide>): void {
    this.slides.update(slides =>
      slides.map((s, i) => i === index ? { ...s, ...patch } : s)
    );
  }

  addListItem(index: number, value: string): void {
    const trimmed = value.trim();
    if (!trimmed) return;
    this.slides.update(slides =>
      slides.map((s, i) => i === index ? { ...s, key_messages: [...s.key_messages, trimmed] } : s)
    );
  }

  removeListItem(index: number, itemIndex: number): void {
    this.slides.update(slides =>
      slides.map((s, i) => i === index ? { ...s, key_messages: s.key_messages.filter((_, j) => j !== itemIndex) } : s)
    );
  }

  commitKeyMessage(index: number): void {
    this.addListItem(index, this.newKeyMessage[index] ?? '');
    this.newKeyMessage[index] = '';
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
