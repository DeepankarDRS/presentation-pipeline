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
    <div class="border-t border-gray-100 pt-5 mt-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-1">Presentation Settings</h3>
      <p class="text-xs text-gray-500 mb-4">Fine-tune how your deck is written, for whom, and how much text it carries.</p>

      @if (loading()) {
        <div class="text-sm text-gray-400 py-2">Loading settings...</div>
      } @else if (loadError()) {
        <div class="text-sm text-red-500 py-2">{{ loadError() }}</div>
      } @else {
        <!-- Content handling -->
        <div class="mb-5">
          <label class="block text-sm font-medium text-gray-700 mb-2">Content handling</label>
          <div class="grid grid-cols-3 gap-2">
            @for (opt of fieldOptions('text_mode'); track opt.value) {
              <button
                type="button"
                (click)="setSingle('text_mode', opt.value)"
                [class.border-blue-500]="values.text_mode === opt.value"
                [class.bg-blue-50]="values.text_mode === opt.value"
                [class.ring-1]="values.text_mode === opt.value"
                [class.ring-blue-500]="values.text_mode === opt.value"
                class="text-left border border-gray-200 rounded-lg p-2.5 hover:border-blue-300 transition-colors"
              >
                <div class="text-xs font-medium text-gray-900">{{ opt.label }}</div>
                @if (opt.description) {
                  <div class="text-[11px] text-gray-500 mt-0.5 leading-snug">{{ opt.description }}</div>
                }
              </button>
            }
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-5">
          <!-- Amount of text -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Amount of text</label>
            <div class="inline-flex w-full rounded-lg border border-gray-200 overflow-hidden">
              @for (opt of fieldOptions('amount_of_text'); track opt.value) {
                <button
                  type="button"
                  (click)="setSingle('amount_of_text', opt.value)"
                  [class.bg-blue-600]="values.amount_of_text === opt.value"
                  [class.text-white]="values.amount_of_text === opt.value"
                  [class.text-gray-600]="values.amount_of_text !== opt.value"
                  class="flex-1 px-2 py-1.5 text-xs font-medium hover:bg-gray-50 border-r border-gray-200 last:border-r-0 transition-colors"
                >
                  {{ opt.label }}
                </button>
              }
            </div>
          </div>

          <!-- Slide count -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Slide count</label>
            <div class="inline-flex w-full rounded-lg border border-gray-200 overflow-hidden">
              @for (opt of fieldOptions('slide_count'); track opt.value) {
                <button
                  type="button"
                  (click)="setSingle('slide_count', opt.value)"
                  [class.bg-blue-600]="values.slide_count === opt.value"
                  [class.text-white]="values.slide_count === opt.value"
                  [class.text-gray-600]="values.slide_count !== opt.value"
                  class="flex-1 px-2 py-1.5 text-xs font-medium hover:bg-gray-50 border-r border-gray-200 last:border-r-0 transition-colors"
                >
                  {{ opt.label }}
                </button>
              }
            </div>
          </div>
        </div>

        <!-- Write for -->
        <div class="mb-5">
          <label class="block text-sm font-medium text-gray-700 mb-2">Write for</label>
          <div class="flex flex-wrap gap-1.5">
            @for (opt of fieldOptionsRaw('write_for'); track opt) {
              <button
                type="button"
                (click)="toggleMulti('write_for', opt)"
                [class.bg-blue-600]="isSelected('write_for', opt)"
                [class.text-white]="isSelected('write_for', opt)"
                [class.border-blue-600]="isSelected('write_for', opt)"
                [class.text-gray-600]="!isSelected('write_for', opt)"
                [class.border-gray-200]="!isSelected('write_for', opt)"
                class="text-xs font-medium px-2.5 py-1 rounded-full border hover:border-blue-300 transition-colors"
              >
                {{ opt }}
              </button>
            }
          </div>
        </div>

        <!-- Tone -->
        <div class="mb-5">
          <label class="block text-sm font-medium text-gray-700 mb-2">Tone</label>
          <div class="flex flex-wrap gap-1.5">
            @for (opt of fieldOptionsRaw('tone'); track opt) {
              <button
                type="button"
                (click)="toggleMulti('tone', opt)"
                [class.bg-blue-600]="isSelected('tone', opt)"
                [class.text-white]="isSelected('tone', opt)"
                [class.border-blue-600]="isSelected('tone', opt)"
                [class.text-gray-600]="!isSelected('tone', opt)"
                [class.border-gray-200]="!isSelected('tone', opt)"
                class="text-xs font-medium px-2.5 py-1 rounded-full border hover:border-blue-300 transition-colors"
              >
                {{ opt }}
              </button>
            }
          </div>
        </div>

        <!-- Additional instructions -->
        <div>
          <label for="additionalInstructions" class="block text-sm font-medium text-gray-700 mb-1.5">
            Additional instructions
          </label>
          <textarea
            id="additionalInstructions"
            rows="2"
            [value]="values.additional_instructions"
            (input)="setFreeText('additional_instructions', $event)"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
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
    slide_count: '6-10',
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
