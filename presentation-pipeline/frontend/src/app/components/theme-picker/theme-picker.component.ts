import { Component, computed, forwardRef, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { ThemeMood, ThemePalette } from '../../models/api.models';
import { THEME_MOODS, THEME_PALETTES } from '../../constants/theme.constants';

type ThemeFilter = 'all' | ThemeMood | 'dark';

/**
 * Compact theme picker: palettes as small chips inside a fixed-height scroll box
 * (so it scales to any catalog size), narrowed by search and mood tabs, with the
 * selected theme previewed as a cover slide and a data slide.
 * Works as a form control (value = palette id).
 */
@Component({
  selector: 'app-theme-picker',
  standalone: true,
  providers: [
    { provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => ThemePickerComponent), multi: true },
  ],
  template: `
    <div class="relative mb-3">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z" />
      </svg>
      <input
        type="search"
        class="input pl-9"
        placeholder="Search themes (e.g. navy, warm, green)..."
        aria-label="Search themes"
        [value]="query()"
        (input)="query.set($any($event.target).value)"
      />
    </div>

    <div class="flex flex-wrap gap-x-5 gap-y-2 border-b border-slate-100 mb-3" role="tablist" aria-label="Theme mood">
      @for (f of filters; track f.id) {
        <button
          type="button"
          role="tab"
          [attr.aria-selected]="filter() === f.id"
          (click)="filter.set(f.id)"
          class="-mb-px pb-2 text-xs font-medium border-b-2 transition-colors"
          [class]="filter() === f.id ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800'"
        >
          {{ f.label }} <span class="text-slate-400">{{ counts()[f.id] }}</span>
        </button>
      }
    </div>

    <div
      role="radiogroup"
      aria-label="Presentation theme"
      class="max-h-[132px] overflow-y-auto pr-1 flex flex-wrap content-start gap-2"
    >
      @for (p of visible(); track p.id) {
        @let on = value() === p.id;
        <button
          type="button"
          role="radio"
          [attr.aria-checked]="on"
          [title]="p.tone"
          [disabled]="disabled()"
          (click)="select(p.id)"
          class="inline-flex items-center gap-2 rounded-full border py-1 pl-1 pr-3 text-xs font-medium transition disabled:opacity-60"
          [class]="on ? '' : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'"
          [style.borderColor]="on ? '#' + p.accent : null"
          [style.backgroundColor]="on ? '#' + p.accent + '12' : null"
          [style.color]="on ? '#' + inkOn(p) : null"
          [style.boxShadow]="on ? '0 0 0 3px #' + p.accent + '22' : null"
        >
          <span
            class="relative h-6 w-6 shrink-0 overflow-hidden rounded-full"
            [style.backgroundColor]="'#' + p.surface"
            [style.boxShadow]="'inset 0 0 0 1px #' + p.border"
          >
            <span class="absolute inset-y-0 left-0 w-1/2" [style.backgroundColor]="'#' + cover(p)"></span>
            <span class="absolute right-[3px] top-1/2 -translate-y-1/2 h-2 w-2 rounded-full" [style.backgroundColor]="'#' + p.accent"></span>
          </span>
          <span class="whitespace-nowrap">{{ p.label }}</span>
          @if (on) {
            <svg class="w-3.5 h-3.5" [style.color]="'#' + p.accent" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          }
        </button>
      } @empty {
        <div class="w-full py-6 text-center text-sm text-slate-500">No themes match "{{ query() }}".</div>
      }
    </div>
    <div class="mt-1.5 text-[11px] text-slate-400">
      {{ visible().length }} of {{ palettes.length }} themes
    </div>

    @if (selected(); as s) {
      <div
        class="mt-4 rounded-2xl border p-4 transition-colors"
        [style.borderColor]="'#' + s.accent + '55'"
        [style.background]="'linear-gradient(135deg, #' + s.accent + '0D, #FFFFFF 55%)'"
      >
        <div class="flex items-center justify-between gap-3 mb-3">
          <div class="flex items-center gap-2 min-w-0">
            <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white" [style.backgroundColor]="'#' + s.accent">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </span>
            <div class="min-w-0">
              <div class="text-sm font-semibold text-slate-900 truncate">
                {{ s.label }} <span class="font-normal text-slate-400">— how your slides will look</span>
              </div>
              <div class="text-[11px] text-slate-500 truncate">{{ s.tone }}</div>
            </div>
          </div>
          <span class="flex shrink-0 overflow-hidden rounded-full ring-1 ring-black/5">
            @for (c of swatches(s); track $index) {
              <span class="h-4 w-4" [style.backgroundColor]="'#' + c"></span>
            }
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
          <!-- Cover slide -->
          <div class="md:col-span-2 [container-type:inline-size]">
            <div class="relative aspect-video w-full overflow-hidden rounded-lg shadow-sm" [style.backgroundColor]="'#' + s.surface">
              <div class="absolute inset-y-0 left-0 w-[58%] p-[7%] flex flex-col justify-between" [style.backgroundColor]="'#' + cover(s)">
                <div class="text-[2.6cqw] font-semibold uppercase tracking-[.14em]" [style.color]="'#' + s.accent">Quarterly review</div>
                <div>
                  <div class="text-[6.5cqw] font-extrabold leading-[1.05]" [style.color]="'#' + onCover(s)">Q3 Revenue<br />Review</div>
                  <div class="mt-[3%] h-[1cqw] w-[10cqw] rounded-full" [style.backgroundColor]="'#' + s.accent"></div>
                </div>
                <div class="text-[2.2cqw] opacity-70" [style.color]="'#' + onCover(s)">Board update · Oct 2026</div>
              </div>
              <div class="absolute inset-y-0 right-0 w-[42%] p-[6%] flex flex-col justify-center gap-[3%]">
                <div class="text-[2.4cqw] font-medium" [style.color]="'#' + s.textMuted">Revenue</div>
                <div class="text-[5.5cqw] font-extrabold leading-none" [style.color]="'#' + s.accent">$4.2M</div>
                <div class="text-[2.4cqw] font-semibold" [style.color]="'#' + s.accentAlt">▲ 12% QoQ</div>
                <div class="mt-[4%] flex items-end gap-[6%] h-[28%]">
                  @for (b of bars; track $index) {
                    <div class="flex-1 rounded-t-sm" [style.height.%]="b" [style.backgroundColor]="'#' + chart(s, $index)"></div>
                  }
                </div>
              </div>
              <div class="absolute -right-[6%] -top-[10%] w-[18%] aspect-square rounded-full opacity-20" [style.backgroundColor]="'#' + s.accentAlt"></div>
            </div>
            <div class="mt-1.5 text-[11px] text-center text-slate-500">Cover</div>
          </div>

          <!-- Data slide -->
          <div class="md:col-span-2 [container-type:inline-size]">
            <div
              class="relative aspect-video w-full overflow-hidden rounded-lg p-[6%] shadow-sm"
              [style.backgroundColor]="'#' + s.surface"
              [style.boxShadow]="'inset 0 0 0 1px #' + s.border"
            >
              <div class="text-[4.2cqw] font-bold leading-tight" [style.color]="'#' + s.textMain">Revenue grew 12% on retail</div>
              <div class="text-[2.4cqw] mt-[1%]" [style.color]="'#' + s.textMuted">Q3 2026 · all regions</div>
              <div class="mt-[2%] h-[0.7cqw] w-[8cqw] rounded-full" [style.backgroundColor]="'#' + s.accent"></div>
              <div class="absolute left-[6%] right-[6%] bottom-[8%] top-[44%] flex gap-[4%]">
                <div
                  class="w-[34%] rounded-md p-[5%] flex flex-col justify-center"
                  [style.backgroundColor]="'#' + s.surfaceAlt"
                  [style.boxShadow]="'inset 0 0 0 1px #' + s.border + ', inset 0 3px 0 0 #' + s.accent"
                >
                  <div class="text-[5.5cqw] font-extrabold leading-none" [style.color]="'#' + s.accent">$4.2M</div>
                  <div class="text-[2.2cqw] mt-[6%]" [style.color]="'#' + s.textMuted">Net revenue</div>
                </div>
                <div
                  class="flex-1 rounded-md px-[5%] pt-[4%] pb-[3%] flex flex-col"
                  [style.backgroundColor]="'#' + s.surfaceAlt"
                  [style.boxShadow]="'inset 0 0 0 1px #' + s.border"
                >
                  <div class="flex-1 flex items-end gap-[8%]">
                    @for (b of bars; track $index) {
                      <div class="flex-1 rounded-t-sm" [style.height.%]="b" [style.backgroundColor]="'#' + chart(s, $index)"></div>
                    }
                  </div>
                  <div class="flex justify-between text-[1.9cqw] mt-[2%]" [style.color]="'#' + s.textMuted">
                    <span>Q1</span><span>Q2</span><span>Q3</span><span>Q4</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="mt-1.5 text-[11px] text-center text-slate-500">Data slide</div>
          </div>

          <!-- Color roles -->
          <div class="md:col-span-1 grid grid-cols-2 md:grid-cols-1 gap-2">
            @for (r of roles(s); track r.label) {
              <div class="flex items-center gap-2 text-[11px] text-slate-600">
                <span class="h-4 w-4 shrink-0 rounded-md ring-1 ring-black/10" [style.backgroundColor]="'#' + r.color"></span>
                {{ r.label }}
              </div>
            }
          </div>
        </div>
      </div>
    }
  `,
})
export class ThemePickerComponent implements ControlValueAccessor {
  readonly palettes = THEME_PALETTES;
  readonly filters: { id: ThemeFilter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'cool', label: 'Cool' },
    { id: 'warm', label: 'Warm' },
    { id: 'bold', label: 'Bold' },
    { id: 'brand', label: 'Brand' },
    { id: 'dark', label: 'Dark' },
  ];
  readonly bars = [48, 72, 58, 92];

  readonly value = signal<string>(THEME_PALETTES[0].id);
  readonly query = signal('');
  readonly filter = signal<ThemeFilter>('all');
  readonly disabled = signal(false);

  private readonly matches = computed(() => {
    const q = this.query().trim().toLowerCase();
    if (!q) return this.palettes;
    return this.palettes.filter(p => `${p.label} ${p.tone} ${this.groupOf(p)}`.toLowerCase().includes(q));
  });

  readonly counts = computed(() => {
    const counts = Object.fromEntries(this.filters.map(f => [f.id, 0])) as Record<ThemeFilter, number>;
    for (const p of this.matches()) {
      counts.all++;
      counts[this.groupOf(p)]++;
    }
    return counts;
  });

  readonly visible = computed(() => {
    const f = this.filter();
    return f === 'all' ? this.matches() : this.matches().filter(p => this.groupOf(p) === f);
  });

  readonly selected = computed(() => this.palettes.find(p => p.id === this.value()));

  private onChange: (v: string) => void = () => {};
  private onTouched: () => void = () => {};

  groupOf(p: ThemePalette): Exclude<ThemeFilter, 'all'> {
    return p.mode === 'dark' ? 'dark' : THEME_MOODS[p.id] ?? 'cool';
  }

  /** Bold block color for the cover: ink on light themes, the surface on dark ones. */
  cover(p: ThemePalette): string {
    return p.mode === 'dark' ? p.surface : p.textMain;
  }

  onCover(p: ThemePalette): string {
    return p.mode === 'dark' ? p.textMain : p.surface;
  }

  /** Readable label color on the light, accent-tinted selected chip. */
  inkOn(p: ThemePalette): string {
    return p.mode === 'dark' ? '0F172A' : p.textMain;
  }

  chart(p: ThemePalette, i: number): string {
    return p.chartColors[i % p.chartColors.length];
  }

  swatches(p: ThemePalette): string[] {
    return [p.surface, p.textMain, ...p.chartColors.slice(0, 3)];
  }

  roles(p: ThemePalette): { label: string; color: string }[] {
    return [
      { label: 'Background', color: p.surface },
      { label: 'Cards', color: p.surfaceAlt },
      { label: 'Headings', color: p.textMain },
      { label: 'Accent', color: p.accent },
      { label: 'Second accent', color: p.accentAlt },
    ];
  }

  select(id: string): void {
    this.value.set(id);
    this.onChange(id);
    this.onTouched();
  }

  writeValue(id: string | null): void {
    if (id) this.value.set(id);
  }

  registerOnChange(fn: (v: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled.set(isDisabled);
  }
}
