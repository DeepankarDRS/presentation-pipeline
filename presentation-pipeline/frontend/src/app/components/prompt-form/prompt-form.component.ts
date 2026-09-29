import { Component, computed, output, signal } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { GenerateRequest, CriticMode, DeckSettings } from '../../models/api.models';
import { THEME_PALETTES, SLIDE_COUNT_TO_THRESHOLD } from '../../constants/theme.constants';
import { DeckSettingsFormComponent } from '../deck-settings-form/deck-settings-form.component';
import { ThemePickerComponent } from '../theme-picker/theme-picker.component';

@Component({
  selector: 'app-prompt-form',
  standalone: true,
  imports: [ReactiveFormsModule, TitleCasePipe, DeckSettingsFormComponent, ThemePickerComponent],
  template: `
    <div class="card overflow-hidden">
      <div class="px-6 pt-6 pb-5 bg-gradient-to-br from-brand-50 via-white to-white border-b border-slate-100">
        <h2 class="text-xl font-semibold text-slate-900">Create a Presentation</h2>
        <p class="text-sm text-slate-500 mt-1">Describe what you want, choose a look, and we'll generate a polished deck.</p>
      </div>

      <form [formGroup]="form" (ngSubmit)="onSubmit()">
        <!-- Prompt -->
        <section class="px-6 py-5">
          <div class="flex items-end justify-between mb-2">
            <div>
              <label for="prompt" class="section-title">Prompt</label>
              <p class="section-hint">The topic, audience, and any data you want on the slides.</p>
            </div>
            <span class="text-[11px] text-slate-400 tabular-nums">{{ promptLength() }} characters</span>
          </div>
          <textarea
            id="prompt"
            formControlName="prompt"
            rows="5"
            class="input resize-y leading-relaxed"
            placeholder="e.g. Create a quarterly revenue report with KPI dashboard, trend charts, and executive summary..."
          ></textarea>
        </section>

        <div class="divider mx-6"></div>

        <!-- Presentation style -->
        <section class="px-6 py-5">
          <h3 class="section-title">Presentation Style</h3>
          <p class="section-hint mb-4">Choose the overall look and feel of your presentation.</p>
          <app-theme-picker formControlName="theme" />
        </section>

        <div class="divider mx-6"></div>

        <!-- Deck settings -->
        <section class="px-6 py-5">
          <app-deck-settings-form (settingsChange)="onDeckSettingsChange($event)" />
        </section>

        <div class="divider mx-6"></div>

        <!-- Advanced -->
        <section class="px-6 py-4">
          <button
            type="button"
            (click)="advancedOpen.set(!advancedOpen())"
            class="flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
          >
            <svg
              class="w-4 h-4 transition-transform"
              [class.rotate-90]="advancedOpen()"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
            Advanced Options
          </button>

          @if (advancedOpen()) {
            <div class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              @for (mode of criticModes; track mode) {
                <label
                  class="option-card flex items-start gap-3 p-3 cursor-pointer"
                  [class.option-card-selected]="form.controls.criticMode.value === mode"
                >
                  <input
                    type="radio"
                    formControlName="criticMode"
                    [value]="mode"
                    class="mt-0.5 text-brand-600 focus:ring-brand-500"
                  />
                  <span>
                    <span class="block text-sm font-medium text-slate-900">Critic: {{ mode | titlecase }}</span>
                    <span class="block text-xs text-slate-500 mt-0.5">
                      {{ mode === 'auto' ? 'An AI reviewer checks each slide and requests fixes.' : 'Skip the visual review step for faster results.' }}
                    </span>
                  </span>
                </label>
              }
            </div>
          }
        </section>

        <!-- Summary + submit -->
        <div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center gap-3">
          <div class="flex-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
            @if (selectedPalette(); as p) {
              <span class="inline-flex items-center gap-1.5">
                <span class="w-2.5 h-2.5 rounded-full" [style.backgroundColor]="'#' + p.accent"></span>
                Theme <span class="font-semibold text-slate-800">{{ p.label }}</span>
              </span>
            }
            @if (deckSettings(); as ds) {
              <span class="text-slate-300">|</span>
              <span>Slides <span class="font-semibold text-slate-800">{{ ds.slide_count }}</span></span>
              <span class="text-slate-300">|</span>
              <span>Text <span class="font-semibold text-slate-800">{{ ds.amount_of_text | titlecase }}</span></span>
              @if (ds.tone?.length) {
                <span class="text-slate-300">|</span>
                <span>Tone <span class="font-semibold text-slate-800">{{ ds.tone!.join(', ') }}</span></span>
              }
            }
            <span class="text-slate-300">|</span>
            <span>Critic <span class="font-semibold text-slate-800">{{ form.controls.criticMode.value | titlecase }}</span></span>
          </div>
          <button type="submit" [disabled]="form.invalid" class="btn-primary sm:min-w-[220px]">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Generate Presentation
          </button>
        </div>
      </form>
    </div>
  `,
})
export class PromptFormComponent {
  readonly generate = output<GenerateRequest>();
  readonly advancedOpen = signal(false);

  readonly criticModes: CriticMode[] = ['auto', 'off'];

  private fb = new FormBuilder();
  form = this.fb.nonNullable.group({
    prompt: ['', Validators.required],
    theme: ['corporate-slate'],
    criticMode: ['off' as CriticMode],
  });

  private readonly themeId = signal(this.form.controls.theme.value);
  readonly selectedPalette = computed(() => THEME_PALETTES.find(p => p.id === this.themeId()));
  readonly promptLength = signal(0);
  readonly deckSettings = signal<DeckSettings | null>(null);

  constructor() {
    this.form.controls.theme.valueChanges.subscribe(themeId => this.themeId.set(themeId));
    this.form.controls.prompt.valueChanges.subscribe(v => this.promptLength.set(v.length));
  }

  onDeckSettingsChange(settings: DeckSettings): void {
    this.deckSettings.set(settings);
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    const v = this.form.getRawValue();
    const ds = this.deckSettings();
    const threshold = SLIDE_COUNT_TO_THRESHOLD[ds?.slide_count ?? '6-10'] ?? 8;

    this.generate.emit({
      prompt: v.prompt.trim(),
      theme: v.theme,
      critic_mode: v.criticMode,
      deck_min_threshold: threshold,
      deck_settings: ds ? { ...ds, theme: v.theme, user_prompt: v.prompt.trim() } : null,
    });
  }
}
