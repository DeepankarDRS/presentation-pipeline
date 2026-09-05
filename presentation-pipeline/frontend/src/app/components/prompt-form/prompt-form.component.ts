import { Component, output, signal } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { GenerateRequest, CriticMode } from '../../models/api.models';
import { THEME_PALETTES } from '../../constants/theme.constants';

@Component({
  selector: 'app-prompt-form',
  standalone: true,
  imports: [ReactiveFormsModule, TitleCasePipe],
  template: `
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-1">Create a Presentation</h2>
      <p class="text-sm text-gray-500 mb-6">Describe what you want and we'll generate a polished deck.</p>

      <form [formGroup]="form" (ngSubmit)="onSubmit()">
        <div class="mb-5">
          <label for="prompt" class="block text-sm font-medium text-gray-700 mb-1.5">Prompt</label>
          <textarea
            id="prompt"
            formControlName="prompt"
            rows="4"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
            placeholder="e.g. Create a quarterly revenue report with KPI dashboard, trend charts, and executive summary..."
          ></textarea>
        </div>

        <div class="mb-5">
          <label for="theme" class="block text-sm font-medium text-gray-700 mb-1.5">Theme</label>
          <div class="flex items-center gap-3">
            <div
              class="w-6 h-6 rounded-full border border-gray-300 shrink-0"
              [style.backgroundColor]="'#' + selectedAccent()"
            ></div>
            <select
              id="theme"
              formControlName="theme"
              class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <optgroup label="Light Themes">
                @for (p of lightPalettes; track p.id) {
                  <option [value]="p.id">{{ p.label }} — {{ p.tone }}</option>
                }
              </optgroup>
              <optgroup label="Dark Themes">
                @for (p of darkPalettes; track p.id) {
                  <option [value]="p.id">{{ p.label }} — {{ p.tone }}</option>
                }
              </optgroup>
            </select>
          </div>
        </div>

        <div class="mb-6">
          <button
            type="button"
            (click)="advancedOpen.set(!advancedOpen())"
            class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
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
            <div class="mt-3 pl-5 space-y-4 border-l-2 border-gray-100">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Critic Mode</label>
                <div class="flex gap-4">
                  @for (mode of criticModes; track mode) {
                    <label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
                      <input
                        type="radio"
                        formControlName="criticMode"
                        [value]="mode"
                        class="text-blue-600 focus:ring-blue-500"
                      />
                      {{ mode | titlecase }}
                    </label>
                  }
                </div>
              </div>

              <div>
                <label for="minSlides" class="block text-sm font-medium text-gray-700 mb-1.5">
                  Minimum Slides: {{ form.value.minSlides }}
                </label>
                <input
                  id="minSlides"
                  type="range"
                  formControlName="minSlides"
                  min="1"
                  max="20"
                  class="w-full accent-blue-600"
                />
                <div class="flex justify-between text-xs text-gray-400 mt-0.5">
                  <span>1</span>
                  <span>20</span>
                </div>
              </div>
            </div>
          }
        </div>

        <button
          type="submit"
          [disabled]="form.invalid"
          class="w-full bg-blue-600 text-white font-medium py-2.5 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          Generate Presentation
        </button>
      </form>
    </div>
  `,
})
export class PromptFormComponent {
  readonly generate = output<GenerateRequest>();
  readonly advancedOpen = signal(false);

  readonly lightPalettes = THEME_PALETTES.filter(p => p.mode === 'light');
  readonly darkPalettes = THEME_PALETTES.filter(p => p.mode === 'dark');
  readonly criticModes: CriticMode[] = ['auto', 'manual', 'off'];

  private fb = new FormBuilder();
  form = this.fb.nonNullable.group({
    prompt: ['', Validators.required],
    theme: ['corporate-slate'],
    criticMode: ['auto' as CriticMode],
    minSlides: [3],
  });

  readonly selectedAccent = signal(THEME_PALETTES[0].accent);

  constructor() {
    this.form.controls.theme.valueChanges.subscribe(themeId => {
      const palette = THEME_PALETTES.find(p => p.id === themeId);
      if (palette) {
        this.selectedAccent.set(palette.accent);
      }
    });
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    const v = this.form.getRawValue();
    this.generate.emit({
      prompt: v.prompt.trim(),
      theme: v.theme,
      critic_mode: v.criticMode,
      deck_min_threshold: v.minSlides,
    });
  }
}
