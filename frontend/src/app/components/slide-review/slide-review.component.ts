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
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">Slide Review & Edit</h2>
          <p class="text-sm text-gray-500">{{ slideCount() }} slide(s) &mdash; click to select, type feedback to edit</p>
        </div>
        <div class="flex gap-2">
          <button
            (click)="gen.backToResult()"
            class="text-sm text-gray-600 font-medium py-2 px-4 rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
          >
            Back
          </button>
          <button
            (click)="finalize()"
            [disabled]="isEditing() || isFinalizing()"
            class="text-sm bg-green-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {{ isFinalizing() ? 'Finalizing...' : 'Finalize Deck' }}
          </button>
        </div>
      </div>

      <div class="flex" style="min-height: 500px">
        <!-- Sidebar: slide thumbnails -->
        <div class="w-48 border-r border-gray-200 bg-gray-50 overflow-y-auto p-3 space-y-2 shrink-0">
          @for (slide of slides(); track slide.slide_index) {
            <button
              (click)="selectSlide(slide.slide_index)"
              class="w-full rounded-lg overflow-hidden border-2 transition-colors"
              [class.border-indigo-500]="selectedIndex() === slide.slide_index"
              [class.border-gray-200]="selectedIndex() !== slide.slide_index"
              [class.hover:border-indigo-300]="selectedIndex() !== slide.slide_index"
            >
              @if (slide.screenshot_url) {
                <img
                  [src]="screenshotSrc(slide.slide_index)"
                  [alt]="'Slide ' + (slide.slide_index + 1)"
                  class="w-full aspect-video object-cover bg-gray-100"
                />
              } @else {
                <div class="w-full aspect-video bg-gray-200 flex items-center justify-center">
                  <span class="text-xs text-gray-400">No preview</span>
                </div>
              }
              <div class="px-2 py-1.5 text-left">
                <span class="text-xs font-medium text-gray-700">Slide {{ slide.slide_index + 1 }}</span>
                @if (slide.has_edits) {
                  <span class="ml-1 text-xs text-indigo-600">(v{{ slide.version }})</span>
                }
              </div>
            </button>
          }
        </div>

        <!-- Main content area -->
        <div class="flex-1 flex flex-col">
          <!-- Screenshot display -->
          <div class="flex-1 p-4 flex items-center justify-center bg-gray-100 relative">
            @if (isEditing()) {
              <div class="absolute inset-0 bg-white/70 flex items-center justify-center z-10">
                <div class="flex flex-col items-center gap-3">
                  <div class="animate-spin rounded-full h-8 w-8 border-2 border-indigo-600 border-t-transparent"></div>
                  <span class="text-sm text-gray-600">Applying edit...</span>
                </div>
              </div>
            }
            @if (selectedScreenshotUrl()) {
              <img
                [src]="selectedScreenshotUrl()"
                alt="Selected slide"
                class="max-w-full max-h-full rounded shadow-lg"
              />
            } @else {
              <div class="text-gray-400 text-sm text-center">
                <svg class="mx-auto w-12 h-12 text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <p>No screenshot available</p>
                <p class="text-xs mt-1">Screenshots require LibreOffice + ImageMagick</p>
              </div>
            }
          </div>

          <!-- Edit input -->
          <div class="px-4 py-3 border-t border-gray-200 bg-white">
            @if (editError()) {
              <div class="mb-2 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
                {{ editError() }}
              </div>
            }
            @if (lastEditResult() && lastEditResult()!.ok) {
              <div class="mb-2 text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2">
                Edit applied successfully
                @if (lastEditResult()!.repair_attempts > 0) {
                  <span class="text-green-600">({{ lastEditResult()!.repair_attempts }} repair(s))</span>
                }
              </div>
              @if (!lastEditResult()!.screenshot_updated) {
                <div class="mb-2 text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
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
                class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                [disabled]="isEditing()"
              />
              <button
                (click)="applyEdit()"
                [disabled]="isEditing() || !feedbackText.trim()"
                class="bg-indigo-600 text-white font-medium py-2 px-5 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm shrink-0"
              >
                Apply Edit
              </button>
            </div>
          </div>

          <!-- Edit history -->
          @if (editHistory().length > 0) {
            <div class="px-4 py-2 border-t border-gray-100 bg-gray-50 max-h-32 overflow-y-auto">
              <p class="text-xs font-medium text-gray-500 mb-1">Edit History</p>
              @for (entry of editHistory(); track $index) {
                <div class="flex items-center gap-2 text-xs py-0.5">
                  @if (entry.ok) {
                    <span class="w-4 h-4 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                      <svg class="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                  } @else {
                    <span class="w-4 h-4 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                      <svg class="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </span>
                  }
                  <span class="text-gray-700 truncate">{{ entry.feedback }}</span>
                  @if (entry.repair_attempts > 0) {
                    <span class="text-gray-400 shrink-0">({{ entry.repair_attempts }} repair(s))</span>
                  }
                </div>
              }
            </div>
          }
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
