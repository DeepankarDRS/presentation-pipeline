import { Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  ComponentKind,
  ComponentPlan,
  Density,
  FontTier,
  LayoutPattern,
  SlidePlan,
  SlideType,
} from '../../models/api.models';

const SLIDE_TYPES: SlideType[] = ['cover', 'content', 'data', 'section_break', 'closing'];
const DENSITIES: Density[] = ['sparse', 'normal', 'dense', 'tight_fit'];
const FONT_TIERS: FontTier[] = ['display', 'standard', 'compact', 'micro'];
const LAYOUT_PATTERNS: LayoutPattern[] = [
  'hero_statement', 'hero_big_number', 'two_column', 'three_column_cards',
  'full_width_chart', 'chart_table_split', 'stacked_sections', 'dashboard_grid',
];
const COMPONENT_KINDS: { label: string; value: ComponentKind }[] = [
  { label: 'Title', value: 'title' },
  { label: 'Narrative', value: 'narrative' },
  { label: 'Caption', value: 'caption' },
  { label: 'KPI Row', value: 'kpi_row' },
  { label: 'Bullet List', value: 'bullet_list' },
  { label: 'Chart', value: 'chart' },
  { label: 'Table', value: 'table' },
  { label: 'Timeline', value: 'timeline' },
  { label: 'Flowchart', value: 'flow' },
  { label: 'Layer/Diagram', value: 'layer' },
  { label: 'Tree', value: 'tree' },
  { label: 'Matrix', value: 'matrix' },
  { label: 'Process Arrow', value: 'process_arrow' },
  { label: 'Pyramid', value: 'pyramid' },
];
const CHART_TYPES = ['bar', 'line', 'pie', 'donut', 'area', 'doughnut', 'radar'];

@Component({
  selector: 'app-slide-editor',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="space-y-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
      <!-- Slide properties -->
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Slide Type</label>
          <select
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            [ngModel]="slide().slide_type"
            (ngModelChange)="updateField('slide_type', $event)"
          >
            @for (t of slideTypes; track t) {
              <option [value]="t">{{ t }}</option>
            }
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Layout Pattern</label>
          <select
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            [ngModel]="slide().layout_pattern"
            (ngModelChange)="updateField('layout_pattern', $event)"
          >
            @for (lp of layoutPatterns; track lp) {
              <option [value]="lp">{{ formatLabel(lp) }}</option>
            }
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Density</label>
          <select
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            [ngModel]="slide().density"
            (ngModelChange)="updateField('density', $event)"
          >
            @for (d of densities; track d) {
              <option [value]="d">{{ formatLabel(d) }}</option>
            }
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Font Tier</label>
          <select
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            [ngModel]="slide().font_tier"
            (ngModelChange)="updateField('font_tier', $event)"
          >
            @for (ft of fontTiers; track ft) {
              <option [value]="ft">{{ ft }}</option>
            }
          </select>
        </div>
      </div>

      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">Layout Hint</label>
        <input
          type="text"
          class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          [ngModel]="slide().layout_hint"
          (ngModelChange)="updateField('layout_hint', $event)"
        />
      </div>

      <!-- Components -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-medium text-gray-600">Components</span>
          <div class="flex items-center gap-2">
            <select #kindSelect class="rounded border border-gray-300 px-2 py-1 text-xs">
              @for (ck of componentKinds; track ck.value) {
                <option [value]="ck.value">{{ ck.label }}</option>
              }
            </select>
            <button
              type="button"
              (click)="addComponent(kindSelect.value)"
              class="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700"
            >Add</button>
          </div>
        </div>

        @for (comp of slide().components; track $index; let i = $index) {
          <div class="flex items-start gap-2 mb-2 p-2 bg-white rounded border border-gray-200">
            <div class="flex-1 grid grid-cols-2 gap-2">
              <div>
                <label class="block text-xs text-gray-500">Kind</label>
                <select
                  class="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                  [ngModel]="comp.kind"
                  (ngModelChange)="updateComponent(i, 'kind', $event)"
                >
                  @for (ck of componentKinds; track ck.value) {
                    <option [value]="ck.value">{{ ck.label }}</option>
                  }
                </select>
              </div>

              @if (comp.kind === 'chart') {
                <div>
                  <label class="block text-xs text-gray-500">Chart Type</label>
                  <select
                    class="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                    [ngModel]="comp.chart_type"
                    (ngModelChange)="updateComponent(i, 'chart_type', $event)"
                  >
                    @for (ct of chartTypes; track ct) {
                      <option [value]="ct">{{ ct }}</option>
                    }
                  </select>
                </div>
              }

              @if (comp.kind === 'table') {
                <div class="flex gap-2">
                  <div class="flex-1">
                    <label class="block text-xs text-gray-500">Cols</label>
                    <input type="number" min="1" max="10"
                      class="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                      [ngModel]="comp.columns"
                      (ngModelChange)="updateComponent(i, 'columns', $event)"
                    />
                  </div>
                  <div class="flex-1">
                    <label class="block text-xs text-gray-500">Rows</label>
                    <input type="number" min="1" max="20"
                      class="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                      [ngModel]="comp.rows"
                      (ngModelChange)="updateComponent(i, 'rows', $event)"
                    />
                  </div>
                </div>
              }

              @if (comp.kind === 'kpi_row') {
                <div>
                  <label class="block text-xs text-gray-500">Count</label>
                  <input type="number" min="1" max="20"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                    [ngModel]="comp.count"
                    (ngModelChange)="updateComponent(i, 'count', $event)"
                  />
                </div>
              }

              @if (['timeline', 'flow', 'process_arrow', 'pyramid', 'bullet_list'].includes(comp.kind)) {
                <div>
                  <label class="block text-xs text-gray-500">Items</label>
                  <input type="number" min="1" max="20"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                    [ngModel]="comp.items"
                    (ngModelChange)="updateComponent(i, 'items', $event)"
                  />
                </div>
              }

              <div class="col-span-2">
                <label class="block text-xs text-gray-500">Summary</label>
                <input type="text"
                  class="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                  [ngModel]="comp.content_summary"
                  (ngModelChange)="updateComponent(i, 'content_summary', $event)"
                />
              </div>
            </div>

            <div class="flex flex-col gap-1 pt-3">
              @if (i > 0) {
                <button type="button" (click)="moveComponent(i, -1)"
                  class="text-gray-400 hover:text-gray-600 text-xs" title="Move up">&#9650;</button>
              }
              @if (i < slide().components.length - 1) {
                <button type="button" (click)="moveComponent(i, 1)"
                  class="text-gray-400 hover:text-gray-600 text-xs" title="Move down">&#9660;</button>
              }
              <button type="button" (click)="removeComponent(i)"
                class="text-red-400 hover:text-red-600 text-xs" title="Remove">&times;</button>
            </div>
          </div>
        }
      </div>
    </div>
  `,
})
export class SlideEditorComponent {
  readonly slide = input.required<SlidePlan>();
  readonly changed = output<SlidePlan>();

  readonly slideTypes = SLIDE_TYPES;
  readonly densities = DENSITIES;
  readonly fontTiers = FONT_TIERS;
  readonly layoutPatterns = LAYOUT_PATTERNS;
  readonly componentKinds = COMPONENT_KINDS;
  readonly chartTypes = CHART_TYPES;

  formatLabel(s: string): string {
    return s.replace(/_/g, ' ');
  }

  updateField(field: string, value: unknown): void {
    this.changed.emit({ ...this.slide(), [field]: value });
  }

  updateComponent(index: number, field: string, value: unknown): void {
    const components = this.slide().components.map((c, i) =>
      i === index ? { ...c, [field]: value } : c
    );
    this.changed.emit({ ...this.slide(), components });
  }

  addComponent(kind: string): void {
    const comp: ComponentPlan = {
      kind: kind as ComponentKind,
      count: 1,
      chart_type: kind === 'chart' ? 'bar' : '',
      series_count: 0,
      columns: kind === 'table' ? 3 : 0,
      rows: kind === 'table' ? 3 : 0,
      items: ['timeline', 'flow', 'process_arrow', 'pyramid', 'bullet_list'].includes(kind) ? 3 : 0,
      content_summary: '',
    };
    this.changed.emit({
      ...this.slide(),
      components: [...this.slide().components, comp],
    });
  }

  removeComponent(index: number): void {
    this.changed.emit({
      ...this.slide(),
      components: this.slide().components.filter((_, i) => i !== index),
    });
  }

  moveComponent(index: number, direction: number): void {
    const components = [...this.slide().components];
    const target = index + direction;
    [components[index], components[target]] = [components[target], components[index]];
    this.changed.emit({ ...this.slide(), components });
  }
}
