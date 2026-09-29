import { Component, OnInit, inject, output, signal } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { DeckSettings, DeckSettingsField, DeckSettingsFieldOption } from '../../models/api.models';

/**
 * Gamma-style "Deck Settings" form — Phase A of the elicitation pipeline.
 * Renders itself from GET /deck-settings-schema so the field set stays in
 * sync with the backend's DeckSettings model without a frontend redeploy.
 */
@Component({
  selector: 'app-deck-settings-form',
  standalone: true,
  imports: [],
  template: `
    <div>
      <h3 class="section-title">Presentation Settings</h3>
      <p class="section-hint mb-4">Fine-tune how your deck is written, for whom, and how much text it carries.</p>

      @if (loading()) {
        <div class="grid grid-cols-3 gap-3 animate-pulse">
          @for (i of [1, 2, 3]; track i) {
            <div class="h-16 rounded-xl bg-slate-100"></div>
          }
        </div>
      } @else if (loadError()) {
        <div class="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{{ loadError() }}</div>
      } @else {
        <!-- Content handling -->
        <div class="mb-5">
          <label class="field-label">Content handling</label>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            @for (opt of fieldOptions('text_mode'); track opt.value; let i = $index) {
              <button
                type="button"
                (click)="setSingle('text_mode', opt.value)"
                class="option-card flex items-start gap-3 p-3"
                [class.option-card-selected]="values.text_mode === opt.value"
              >
                <span
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors"
                  [class.bg-brand-600]="values.text_mode === opt.value"
                  [class.text-white]="values.text_mode === opt.value"
                  [class.bg-slate-100]="values.text_mode !== opt.value"
                  [class.text-slate-500]="values.text_mode !== opt.value"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" [attr.d]="textModeIcon(i)" />
                  </svg>
                </span>
                <span class="min-w-0">
                  <span class="block text-xs font-semibold text-slate-900">{{ opt.label }}</span>
                  @if (opt.description) {
                    <span class="block text-[11px] text-slate-500 mt-0.5 leading-snug">{{ opt.description }}</span>
                  }
                </span>
              </button>
            }
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
          <!-- Amount of text -->
          <div>
            <label class="field-label">Amount of text</label>
            <div class="segmented">
              @for (opt of fieldOptions('amount_of_text'); track opt.value) {
                <button
                  type="button"
                  (click)="setSingle('amount_of_text', opt.value)"
                  class="segmented-item"
                  [class.segmented-item-active]="values.amount_of_text === opt.value"
                >
                  {{ opt.label }}
                </button>
              }
            </div>
          </div>

          <!-- Slide count -->
          <div>
            <label class="field-label">Slide count</label>
            <div class="segmented">
              @for (opt of fieldOptions('slide_count'); track opt.value) {
                <button
                  type="button"
                  (click)="setSingle('slide_count', opt.value)"
                  class="segmented-item"
                  [class.segmented-item-active]="values.slide_count === opt.value"
                >
                  {{ opt.label }}
                </button>
              }
            </div>
          </div>
        </div>

        <!-- Write for -->
        <div class="mb-5">
          <label class="field-label">Write for</label>
          <div class="flex flex-wrap gap-2">
            @for (opt of fieldOptionsRaw('write_for'); track opt) {
              <button
                type="button"
                (click)="toggleMulti('write_for', opt)"
                class="chip"
                [class.chip-selected]="isSelected('write_for', opt)"
              >
                @if (isSelected('write_for', opt)) {
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                }
                {{ opt }}
              </button>
            }
          </div>
        </div>

        <!-- Tone -->
        <div class="mb-5">
          <label class="field-label">Tone</label>
          <div class="flex flex-wrap gap-2">
            @for (opt of fieldOptionsRaw('tone'); track opt) {
              <button
                type="button"
                (click)="toggleMulti('tone', opt)"
                class="chip"
                [class.chip-selected]="isSelected('tone', opt)"
              >
                @if (isSelected('tone', opt)) {
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                }
                {{ opt }}
              </button>
            }
          </div>
        </div>

        <!-- Additional instructions -->
        <div>
          <label for="additionalInstructions" class="field-label">Additional instructions</label>
          <textarea
            id="additionalInstructions"
            rows="2"
            [value]="values.additional_instructions"
            (input)="setFreeText('additional_instructions', $event)"
            class="input resize-y"
            placeholder="e.g. Include a competitor comparison slide, avoid jargon..."
          ></textarea>
        </div>
      }
    </div>
  `,
})
export class DeckSettingsFormComponent implements OnInit {
  private readonly api = inject(ApiService);
  readonly settingsChange = output<DeckSettings>();

  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  readonly fields = signal<DeckSettingsField[]>([]);

  values: DeckSettings = {
    text_mode: 'generate',
    amount_of_text: 'concise',
    write_for: [],
    tone: [],
    slide_count: '3-5',
    additional_instructions: '',
  };

  ngOnInit(): void {
    this.api.getDeckSettingsSchema().then(
      (schema) => {
        this.fields.set(schema.fields);
        this.loading.set(false);
        this.emit();
      },
      (err: Error) => {
        this.loadError.set(err.message || 'Failed to load presentation settings');
        this.loading.set(false);
      },
    );
  }

  private readonly textModeIcons = [
    'M13 10V3L4 14h7v7l9-11h-7z',
    'M4 6h16M4 12h10M4 18h7',
    'M15.232 5.232l3.536 3.536M9 13l6.232-6.232a2.5 2.5 0 013.536 3.536L12.536 16.536 8 18l1.464-4.536z',
  ];

  textModeIcon(index: number): string {
    return this.textModeIcons[index % this.textModeIcons.length];
  }

  fieldOptions(key: string): DeckSettingsFieldOption[] {
    const field = this.fields().find(f => f.key === key);
    if (!field?.options) return [];
    return field.options.map(o => (typeof o === 'string' ? { value: o, label: o } : o));
  }

  fieldOptionsRaw(key: string): string[] {
    const field = this.fields().find(f => f.key === key);
    if (!field?.options) return [];
    return field.options.map(o => (typeof o === 'string' ? o : o.value));
  }

  setSingle(key: 'text_mode' | 'amount_of_text' | 'slide_count', value: string): void {
    (this.values as any)[key] = value;
    this.emit();
  }

  toggleMulti(key: 'write_for' | 'tone', value: string): void {
    const arr = this.values[key] ?? [];
    this.values[key] = arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value];
    this.emit();
  }

  isSelected(key: 'write_for' | 'tone', value: string): boolean {
    return (this.values[key] ?? []).includes(value);
  }

  setFreeText(key: 'additional_instructions', event: Event): void {
    this.values[key] = (event.target as HTMLTextAreaElement).value;
    this.emit();
  }

  private emit(): void {
    this.settingsChange.emit({ ...this.values });
  }
}
