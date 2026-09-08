export type CriticMode = 'auto' | 'manual' | 'off';

export interface GenerateRequest {
  prompt: string;
  theme: string;
  critic_mode: CriticMode;
  deck_min_threshold: number; // target slide count (1 = single slide)
  supplied_content?: Record<string, unknown> | null;
  audience_context?: Record<string, string> | null;
}

export type EventType =
  | 'planning'
  | 'styling'
  | 'generating_slide'
  | 'validating'
  | 'repairing'
  | 'reviewing'
  | 'assembling'
  | 'complete'
  | 'error';

export interface ProgressEvent {
  event: EventType;
  data: Record<string, unknown>;
  timestamp: number;
  run_id: string;
}

export type RunStatusValue = 'pending' | 'running' | 'complete' | 'error';

export interface RunStatus {
  run_id: string;
  status: RunStatusValue;
  progress_pct: number;
  current_step: string;
  passed: boolean | null;
  pptx_path: string | null;
  error: string | null;
}

export interface EvaluationSummary {
  passed: boolean;
  compile_ok: boolean;
  tokens?: { total_in: number; total_out: number; total: number };
  cost?: { total_usd: number; models_used: string[] };
}

export type AppView = 'form' | 'planning' | 'plan-editor' | 'progress' | 'result' | 'review';

// Planner enum types — mirror backend Literals
export type ComponentKind =
  | 'title' | 'narrative' | 'caption' | 'kpi_row' | 'bullet_list'
  | 'chart' | 'table' | 'timeline' | 'flow' | 'layer'
  | 'tree' | 'matrix' | 'process_arrow' | 'pyramid';

export type SlideType = 'cover' | 'content' | 'data' | 'section_break' | 'closing';
export type Density = 'sparse' | 'normal' | 'dense' | 'tight_fit';
export type FontTier = 'display' | 'standard' | 'compact' | 'micro';
export type LayoutPattern =
  | 'hero_statement' | 'hero_big_number' | 'two_column'
  | 'three_column_cards' | 'full_width_chart' | 'chart_table_split'
  | 'stacked_sections' | 'dashboard_grid';

export interface ComponentPlan {
  kind: ComponentKind;
  count: number;
  chart_type: string;
  series_count: number;
  columns: number;
  rows: number;
  items: number;
  content_summary: string;
}

export interface SlidePlan {
  slide_index: number;
  slide_type: SlideType;
  components: ComponentPlan[];
  density: Density;
  font_tier: FontTier;
  layout_pattern: LayoutPattern;
  layout_hint: string;
  content_data: Record<string, unknown>;
  data_provenance?: Record<string, string>;
}

export interface PlanResponse {
  run_id: string;
  core_hook: string;
  slides: SlidePlan[];
}

export interface GenerateFromPlanRequest {
  prompt: string;
  theme: string;
  critic_mode: CriticMode;
  deck_min_threshold: number;
  supplied_content?: Record<string, unknown> | null;
  audience_context?: Record<string, string> | null;
  run_id: string;
  core_hook: string;
  slides: SlidePlan[];
}

export interface RefinePlanRequest extends GenerateFromPlanRequest {
  feedback: string;
}

export interface ThemePalette {
  id: string;
  label: string;
  tone: string;
  mode: 'light' | 'dark';
  accent: string;
}

// ── Edit session types ───────────────────────────────────────────────────

export interface SlideInfoReview {
  slide_index: number;
  version: number;
  screenshot_url: string | null;
  has_edits: boolean;
  edit_count: number;
}

export interface EditSessionStatus {
  run_id: string;
  slide_count: number;
  slides: SlideInfoReview[];
}

export interface SlideEditResponse {
  ok: boolean;
  slide_index: number;
  version: number;
  screenshot_url: string | null;
  screenshot_updated: boolean;
  xml: string | null;
  compile_ok: boolean;
  repair_attempts: number;
  issues: Record<string, unknown>[];
  error: string | null;
}

export interface FinalizeResponse {
  ok: boolean;
  pptx_path: string | null;
  download_url: string | null;
  error: string | null;
}
