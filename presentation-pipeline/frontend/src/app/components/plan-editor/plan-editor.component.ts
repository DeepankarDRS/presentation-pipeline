import { Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GenerationService } from '../../services/generation.service';
import { ApiService } from '../../services/api.service';
import { OutlineSlide } from '../../models/api.models';


function emptyOutlineSlide(index: number): OutlineSlide {
  return {
    slide_index: index,
    slide_title: '',
    section: '',
    narrative_role: '',
    key_messages: [],
    visual_emphasis: '',
  };
}

/**
 * Narrative-only outline review — deck title, core hook, and per-slide
 * title + key messages. Deliberately hides section/narrative_role/
 * visual_emphasis: those still travel on each OutlineSlide and still reach
 * slide_component_planner untouched — they're implementation detail a
 * reviewer shouldn't have to read through to judge whether the outline
 * actually covers the core hook.
 */
@Component({
  selector: 'app-plan-editor',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="card">
      <div class="px-6 pt-6 pb-5 bg-gradient-to-br from-brand-50 via-white to-white border-b border-slate-100 rounded-t-2xl flex items-start justify-between gap-4">
        <div>
          <h2 class="text-xl font-semibold text-slate-900">Review Deck Outline</h2>
          <p class="text-sm text-slate-500 mt-1">Edit the narrative and slide structure, then generate.</p>
        </div>
        <span class="badge bg-brand-100 text-brand-700 shrink-0">
          {{ slides().length }} slide{{ slides().length === 1 ? '' : 's' }}
        </span>
      </div>

      <div class="p-6">
        @if (generation.outlineError()) {
          <p class="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3 mb-4">{{ generation.outlineError() }}</p>
        }

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <!-- Deck title -->
          <div>
            <label class="field-label">Deck Title</label>
            <input
              type="text"
              class="input font-medium"
              [ngModel]="deckTitle()"
              (ngModelChange)="deckTitle.set($event)"
            />
          </div>

          <!-- Core hook -->
          <div>
            <label class="field-label">Core Hook</label>
            <textarea
              rows="2"
              class="input resize-y"
              [ngModel]="coreHook()"
              (ngModelChange)="coreHook.set($event)"
            ></textarea>
          </div>
        </div>

        <!-- Slide cards -->
        <div class="space-y-3 mb-4">
          @for (slide of slides(); track $index; let i = $index) {
            <div
              class="group rounded-xl border bg-white p-4 transition-all hover:shadow-soft"
              [class.border-brand-300]="regeneratingIndex() === i"
              [class.ring-4]="regeneratingIndex() === i"
              [class.ring-brand-50]="regeneratingIndex() === i"
              [class.border-slate-200]="regeneratingIndex() !== i"
            >
              <div class="flex items-start gap-3 mb-3">
                <span class="flex h-7 min-w-[28px] items-center justify-center rounded-lg bg-slate-900 px-2 text-xs font-semibold text-white">
                  {{ i + 1 }}
                </span>
                <div class="flex-1 min-w-0">
                  <input
                    type="text"
                    class="w-full font-semibold text-slate-900 border-0 border-b border-transparent hover:border-slate-200 focus:border-brand-500 px-0 py-1 text-sm focus:outline-none focus:ring-0 bg-transparent"
                    [ngModel]="slide.slide_title"
                    (ngModelChange)="patchSlide(i, { slide_title: $event })"
                    placeholder="Slide title"
                  />
                </div>
                <div class="flex items-center gap-0.5 shrink-0 opacity-60 group-hover:opacity-100 transition-opacity">
                  <button type="button" (click)="toggleRegenerate(i)"
                    class="icon-btn hover:!text-brand-600 hover:!bg-brand-50" title="Regenerate this slide">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                  <button type="button" (click)="moveSlide(i, -1)" class="icon-btn" title="Move up" [disabled]="i === 0">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                    </svg>
                  </button>
                  <button type="button" (click)="moveSlide(i, 1)" class="icon-btn" title="Move down" [disabled]="i === slides().length - 1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  <button type="button" (click)="removeSlide(i)"
                    class="icon-btn hover:!text-red-600 hover:!bg-red-50"
                    [disabled]="slides().length <= 1"
                    title="Delete slide">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Key messages -->
              <div class="pl-10">
                <div class="space-y-1.5 mb-2.5">
                  @for (msg of slide.key_messages; track $index; let mi = $index) {
                    <div class="group/msg flex items-start gap-2.5 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
                      <span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500"></span>
                      <span class="flex-1">{{ msg }}</span>
                      <button type="button" (click)="removeListItem(i, mi)"
                        class="shrink-0 text-slate-300 hover:text-red-500 opacity-0 group-hover/msg:opacity-100 transition-opacity"
                        title="Remove message">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  }
                </div>
                <div class="flex gap-2">
                  <input type="text" class="input !py-2"
                    [(ngModel)]="newKeyMessage[i]" (keydown.enter)="$event.preventDefault(); commitKeyMessage(i)"
                    placeholder="Add a key message and press Enter..." />
                  <button type="button" (click)="commitKeyMessage(i)" class="btn-secondary !px-3 !py-2" title="Add key message">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                  </button>
                </div>

                <!-- Regenerate feedback box -->
                @if (regeneratingIndex() === i) {
                  <div class="mt-3 rounded-xl border border-brand-100 bg-brand-50/60 p-3">
                    <p class="text-xs font-semibold text-brand-800 mb-2">Regenerate this slide</p>
                    @if (regenerateError() && regeneratingIndex() === i) {
                      <p class="text-xs text-red-600 mb-1.5">{{ regenerateError() }}</p>
                    }
                    <textarea rows="2" class="input resize-y mb-2"
                      [(ngModel)]="regenerateFeedback[i]"
                      placeholder="Describe how this slide should change..."
                      [disabled]="regeneratingLoading() === i"
                    ></textarea>
                    <div class="flex justify-end gap-2">
                      <button type="button" (click)="toggleRegenerate(i)"
                        class="btn-ghost !py-1.5 !text-xs"
                        [disabled]="regeneratingLoading() === i"
                      >Cancel</button>
                      <button type="button" (click)="submitRegenerate(i)"
                        class="btn-primary !py-1.5 !text-xs"
                        [disabled]="regeneratingLoading() === i || !feedbackFor(i).trim()"
                      >
                        @if (regeneratingLoading() === i) {
                          <span class="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
                        }
                        {{ regeneratingLoading() === i ? 'Regenerating...' : 'Regenerate' }}
                      </button>
                    </div>
                  </div>
                }
              </div>
            </div>
          }
        </div>

        <!-- Add slide -->
        <button
          type="button"
          (click)="addSlide()"
          class="w-full flex items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl py-3 text-sm font-medium text-slate-500 hover:border-brand-400 hover:text-brand-600 hover:bg-brand-50/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          [disabled]="slides().length >= 20"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add Slide
        </button>
      </div>

      <!-- Actions -->
      <div class="sticky bottom-0 z-10 px-6 py-4 bg-white/90 backdrop-blur border-t border-slate-200 rounded-b-2xl flex justify-end gap-3">
        <button type="button" (click)="generation.reset()" class="btn-secondary">Back</button>
        <button type="button" (click)="onConfirm()" class="btn-primary min-w-[200px]" [disabled]="!isValid()">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Generate Presentation
        </button>
      </div>
    </div>
  `,
})
export class PlanEditorComponent {
  protected readonly generation = inject(GenerationService);
  private readonly api = inject(ApiService);

  readonly deckTitle = signal('');
  readonly coreHook = signal('');
  readonly slides = signal<OutlineSlide[]>([]);

  // Scratch input state for the key-message list editor, keyed by slide index.
  newKeyMessage: Record<number, string> = {};

  // Per-slide regenerate state.
  readonly regeneratingIndex = signal<number | null>(null);
  readonly regeneratingLoading = signal<number | null>(null);
  readonly regenerateError = signal<string | null>(null);
  regenerateFeedback: Record<number, string> = {};

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

  replaceSlide(index: number, updated: OutlineSlide): void {
    this.slides.update(slides =>
      slides.map((s, i) => i === index ? updated : s)
    );
  }

  feedbackFor(index: number): string {
    return this.regenerateFeedback[index] ?? '';
  }

  toggleRegenerate(index: number): void {
    this.regenerateError.set(null);
    this.regeneratingIndex.set(this.regeneratingIndex() === index ? null : index);
  }

  submitRegenerate(index: number): void {
    const feedback = (this.regenerateFeedback[index] ?? '').trim();
    if (!feedback) return;

    this.regenerateError.set(null);
    this.regeneratingLoading.set(index);

    this.api.regenerateOutlineSlide(
      this.coreHook(),
      this.slides()[index],
      feedback,
      this.generation.originalRequest()?.deck_settings,
    ).then(
      (updated) => {
        this.replaceSlide(index, updated);
        this.regeneratingLoading.set(null);
        this.regeneratingIndex.set(null);
        this.regenerateFeedback[index] = '';
      },
      (err: Error) => {
        this.regeneratingLoading.set(null);
        this.regenerateError.set(err.message || 'Regeneration failed');
      },
    );
  }

  onConfirm(): void {
    this.generation.confirmOutline({
      deck_title: this.deckTitle(),
      core_hook: this.coreHook(),
      slides: this.slides(),
    });
  }
}
