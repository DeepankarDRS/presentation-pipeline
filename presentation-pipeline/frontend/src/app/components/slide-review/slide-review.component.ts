import { Component, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GenerationService } from '../../services/generation.service';
import { ApiService } from '../../services/api.service';
import { SlideInfoReview, SlideEditResponse } from '../../models/api.models';

interface EditHistoryEntry {
  feedback: string;
  ok: boolean;
  error: string | null;
  repair_attempts: number;
}

@Component({
  selector: 'app-slide-review',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="card overflow-hidden">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-6 py-4 border-b border-slate-200 bg-gradient-to-br from-brand-50 via-white to-white">
        <div>
          <h2 class="text-lg font-semibold text-slate-900">Slide Review & Edit</h2>
          <p class="text-sm text-slate-500">{{ slideCount() }} slide(s) &mdash; select a slide, then describe what to change</p>
        </div>
        <div class="flex gap-2">
          <button (click)="gen.backToResult()" class="btn-secondary !py-2">Back</button>
          <button (click)="finalize()" [disabled]="isEditing() || isFinalizing()" class="btn-success !py-2">
            @if (isFinalizing()) {
              <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
            } @else {
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            }
            {{ isFinalizing() ? 'Finalizing...' : 'Finalize Deck' }}
          </button>
        </div>
      </div>

      <div class="flex" style="min-height: 540px">
        <!-- Sidebar: slide thumbnails -->
        <div class="w-52 border-r border-slate-200 bg-slate-50 overflow-y-auto p-3 space-y-3 shrink-0">
          @for (slide of slides(); track slide.slide_index) {
            <button
              (click)="selectSlide(slide.slide_index)"
              class="group w-full rounded-xl overflow-hidden border bg-white text-left transition-all"
              [class.border-brand-600]="selectedIndex() === slide.slide_index"
              [class.ring-4]="selectedIndex() === slide.slide_index"
              [class.ring-brand-100]="selectedIndex() === slide.slide_index"
              [class.border-slate-200]="selectedIndex() !== slide.slide_index"
              [class.hover:border-brand-300]="selectedIndex() !== slide.slide_index"
            >
              <div class="relative">
                @if (slide.screenshot_url) {
                  <img
                    [src]="screenshotSrc(slide.slide_index)"
                    [alt]="'Slide ' + (slide.slide_index + 1)"
                    class="w-full aspect-video object-cover bg-slate-100"
                  />
                } @else {
                  <div class="w-full aspect-video bg-slate-100 flex items-center justify-center">
                    <span class="text-xs text-slate-400">No preview</span>
                  </div>
                }
                <span class="absolute top-1.5 left-1.5 rounded-md bg-slate-900/75 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                  {{ slide.slide_index + 1 }}
                </span>
                @if (slide.has_edits) {
                  <span class="absolute top-1.5 right-1.5 rounded-md bg-brand-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                    v{{ slide.version }}
                  </span>
                }
              </div>
              <div class="px-2.5 py-1.5">
                <span class="text-xs font-medium"
                  [class.text-brand-700]="selectedIndex() === slide.slide_index"
                  [class.text-slate-600]="selectedIndex() !== slide.slide_index"
                >Slide {{ slide.slide_index + 1 }}</span>
              </div>
            </button>
          }
        </div>

        <!-- Main content area -->
        <div class="flex-1 flex flex-col min-w-0">
          <!-- Screenshot display -->
          <div class="flex-1 p-6 flex items-center justify-center bg-[radial-gradient(circle_at_center,_#f1f5f9,_#e2e8f0)] relative">
            @if (isEditing()) {
              <div class="absolute inset-0 bg-white/70 backdrop-blur-sm flex items-center justify-center z-10">
                <div class="flex flex-col items-center gap-3">
                  <div class="spinner h-9 w-9"></div>
                  <span class="text-sm font-medium text-slate-700">Applying edit...</span>
                </div>
              </div>
            }
            @if (selectedScreenshotUrl()) {
              <img
                [src]="selectedScreenshotUrl()"
                alt="Selected slide"
                class="max-w-full max-h-full rounded-lg shadow-lift ring-1 ring-black/5"
              />
            } @else {
              <div class="text-slate-400 text-sm text-center">
                <svg class="mx-auto w-12 h-12 text-slate-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <p>No screenshot available</p>
                <p class="text-xs mt-1">Screenshots require PowerPoint + comtypes</p>
              </div>
            }
          </div>

          <!-- Edit history (chat style) -->
          @if (editHistory().length > 0) {
            <div class="px-5 py-3 border-t border-slate-200 bg-slate-50/70 max-h-44 overflow-y-auto space-y-2">
              <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Edit History</p>
              @for (entry of editHistory(); track $index) {
                <div class="flex justify-end">
                  <div class="max-w-[85%] rounded-2xl rounded-br-md bg-brand-600 px-3 py-2 text-xs text-white shadow-sm">
                    {{ entry.feedback }}
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  @if (entry.ok) {
                    <span class="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                      <svg class="w-3 h-3 text-emerald-600" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                    <span class="rounded-2xl rounded-bl-md bg-white border border-slate-200 px-3 py-1.5 text-xs text-slate-600">
                      Applied
                      @if (entry.repair_attempts > 0) {
                        <span class="text-slate-400">&middot; {{ entry.repair_attempts }} repair(s)</span>
                      }
                    </span>
                  } @else {
                    <span class="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                      <svg class="w-3 h-3 text-red-600" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </span>
                    <span class="rounded-2xl rounded-bl-md bg-white border border-red-200 px-3 py-1.5 text-xs text-red-600">
                      {{ entry.error ?? 'Edit failed' }}
                    </span>
                  }
                </div>
              }
            </div>
          }

          <!-- Lines the pipeline wrote (not in the brief) -->
          @if (selectedWrittenLines().length > 0) {
            <div class="px-5 py-3 border-t border-amber-200 bg-amber-50">
              <p class="text-[11px] font-semibold uppercase tracking-wide text-amber-700">Written by the pipeline — not in your brief</p>
              <ul class="mt-1.5 space-y-1 text-xs text-amber-900 list-disc pl-4">
                @for (line of selectedWrittenLines(); track $index) {
                  <li>{{ line }}</li>
                }
              </ul>
              <div class="mt-2 flex gap-2">
                <button class="btn-secondary text-xs" (click)="keepWrittenLines()" [disabled]="isEditing()">Keep</button>
                <button class="btn-secondary text-xs" (click)="removeWrittenLines()" [disabled]="isEditing()">Remove these lines</button>
              </div>
            </div>
          }

          <!-- Edit input -->
          <div class="px-5 py-4 border-t border-slate-200 bg-white">
            @if (editError()) {
              <div class="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
                {{ editError() }}
              </div>
            }
            @if (lastEditResult() && lastEditResult()!.ok) {
              <div class="mb-3 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-xl px-3 py-2">
                Edit applied successfully
                @if (lastEditResult()!.repair_attempts > 0) {
                  <span class="text-emerald-600">({{ lastEditResult()!.repair_attempts }} repair(s))</span>
                }
              </div>
              @if (!lastEditResult()!.screenshot_updated) {
                <div class="mb-3 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
                  The change was applied, but the preview couldn't be refreshed — it's still
                  included in your download. Try the edit again to retry the preview.
                </div>
              }
            }
            <div class="flex gap-2">
              <input
                type="text"
                [(ngModel)]="feedbackText"
                (keydown.enter)="applyEdit()"
                placeholder="Describe what to change... (e.g., 'make the title larger', 'move chart to the left')"
                class="input"
                [disabled]="isEditing()"
              />
              <button
                (click)="applyEdit()"
                [disabled]="isEditing() || !feedbackText.trim()"
                class="btn-primary shrink-0"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                Apply Edit
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class SlideReviewComponent {
  readonly gen = inject(GenerationService);
  private readonly api = inject(ApiService);

  readonly selectedIndex = signal<number>(0);
  readonly isEditing = signal<boolean>(false);
  readonly isFinalizing = signal<boolean>(false);
  readonly editError = signal<string | null>(null);
  readonly lastEditResult = signal<SlideEditResponse | null>(null);
  readonly editHistoryMap = signal<Map<number, EditHistoryEntry[]>>(new Map());
  readonly slideVersions = signal<Map<number, number>>(new Map());
  readonly screenshotVersions = signal<Map<number, number>>(new Map());
  /** Slides whose written lines the user already kept or removed. */
  readonly writtenReviewed = signal<Set<number>>(new Set());

  feedbackText = '';

  readonly slides = computed<SlideInfoReview[]>(() => {
    const session = this.gen.editSession();
    if (!session) return [];
    return session.slides.map(s => {
      const ver = this.slideVersions().get(s.slide_index) ?? s.version;
      return { ...s, version: ver, has_edits: ver > 0, edit_count: ver };
    });
  });

  readonly slideCount = computed(() => this.slides().length);

  readonly selectedScreenshotUrl = computed<string | null>(() => {
    const runId = this.gen.runId();
    if (!runId) return null;
    const idx = this.selectedIndex();
    const ver = this.screenshotVersions().get(idx) ?? 0;
    return this.api.getScreenshotUrl(runId, idx, ver);
  });

  readonly selectedWrittenLines = computed<string[]>(() => {
    const idx = this.selectedIndex();
    if (this.writtenReviewed().has(idx)) return [];
    return this.slides().find(s => s.slide_index === idx)?.written_lines ?? [];
  });

  private markWrittenReviewed(idx: number): void {
    this.writtenReviewed.set(new Set(this.writtenReviewed()).add(idx));
  }

  keepWrittenLines(): void {
    this.markWrittenReviewed(this.selectedIndex());
  }

  async removeWrittenLines(): Promise<void> {
    const idx = this.selectedIndex();
    const lines = this.selectedWrittenLines();
    this.feedbackText = 'Remove these description lines from their cards and keep everything else unchanged: '
      + lines.map(l => `"${l}"`).join('; ');
    await this.applyEdit();
    if (this.lastEditResult()?.ok) this.markWrittenReviewed(idx);
  }

  readonly editHistory = computed<EditHistoryEntry[]>(() => {
    return this.editHistoryMap().get(this.selectedIndex()) ?? [];
  });

  screenshotSrc(slideIndex: number): string {
    const runId = this.gen.runId();
    if (!runId) return '';
    const ver = this.screenshotVersions().get(slideIndex) ?? 0;
    return this.api.getScreenshotUrl(runId, slideIndex, ver);
  }

  selectSlide(index: number): void {
    this.selectedIndex.set(index);
    this.editError.set(null);
    this.lastEditResult.set(null);
  }

  async applyEdit(): Promise<void> {
    const feedback = this.feedbackText.trim();
    if (!feedback) return;

    const runId = this.gen.runId();
    if (!runId) return;

    const idx = this.selectedIndex();
    this.isEditing.set(true);
    this.editError.set(null);
    this.lastEditResult.set(null);

    try {
      const result = await this.api.editSlide(runId, idx, feedback);
      this.lastEditResult.set(result);

      const entry: EditHistoryEntry = {
        feedback,
        ok: result.ok,
        error: result.error,
        repair_attempts: result.repair_attempts,
      };

      const histMap = new Map(this.editHistoryMap());
      const existing = histMap.get(idx) ?? [];
      histMap.set(idx, [...existing, entry]);
      this.editHistoryMap.set(histMap);

      if (result.ok) {
        const verMap = new Map(this.slideVersions());
        verMap.set(idx, result.version);
        this.slideVersions.set(verMap);

        if (result.screenshot_updated) {
          const screenshotMap = new Map(this.screenshotVersions());
          screenshotMap.set(idx, (screenshotMap.get(idx) ?? 0) + 1);
          this.screenshotVersions.set(screenshotMap);
        }

        this.feedbackText = '';
      } else {
        this.editError.set(result.error ?? 'Edit failed');
      }
    } catch (err) {
      this.editError.set(err instanceof Error ? err.message : 'Edit request failed');
    } finally {
      this.isEditing.set(false);
    }
  }

  async finalize(): Promise<void> {
    const runId = this.gen.runId();
    if (!runId) return;

    this.isFinalizing.set(true);
    this.editError.set(null);

    try {
      const result = await this.api.finalizeDeck(runId);
      if (result.ok && result.download_url) {
        this.gen.backToResult();
      } else {
        this.editError.set(result.error ?? 'Finalize failed');
      }
    } catch (err) {
      this.editError.set(err instanceof Error ? err.message : 'Finalize request failed');
    } finally {
      this.isFinalizing.set(false);
    }
  }
}
