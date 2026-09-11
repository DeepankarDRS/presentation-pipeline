export type CriticMode = 'auto' | 'manual' | 'off';

// ── Gamma-style deck settings (Phase A elicitation) ────────────────────────

export type TextMode = 'generate' | 'condense' | 'preserve';
export type AmountOfText = 'minimal' | 'concise' | 'detailed' | 'extensive';
export type SlideCountOption = '1' | '3-5' | '6-10' | '10-15' | '15+';

export interface DeckSettings {
  text_mode?: TextMode;
  amount_of_text?: AmountOfText;
  write_for?: string[];
  tone?: string[];
  theme?: string;
  user_prompt?: string;
  additional_instructions?: string;
  slide_count?: SlideCountOption;
}

export interface DeckSettingsFieldOption {
  value: string;
  label: string;
  description?: string;
}

export interface DeckSettingsField {
  key: string;
  label: string;
  type: 'single_choice' | 'multi_choice' | 'free_text';
  options?: (string | DeckSettingsFieldOption)[];
  default: unknown;
}

export interface DeckSettingsSchema {
  fields: DeckSettingsField[];
}

export interface GenerateRequest {
  prompt: string;
  theme: string;
  critic_mode: CriticMode;
  deck_min_threshold: number; // target slide count (1 = single slide)
  supplied_content?: Record<string, unknown> | null;
  audience_context?: Record<string, string> | null;
  deck_settings?: DeckSettings | null;
  outline_run_id?: string | null;
}

export type EventType =
  | 'planning'
  | 'elicitation_needed'
  | 'reviewing_plan'
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
  excluded_slides?: number[];
  tokens?: { total_in: number; total_out: number; total: number };
  cost?: { total_usd: number; models_used: string[] };
}

export type AppView = 'form' | 'planning' | 'elicitation' | 'plan-editor' | 'progress' | 'result' | 'review';

// Planner enum types — mirror backend Literals
export type ComponentKind =
  | 'title' | 'narrative' | 'caption' | 'kpi_row' | 'bullet_list'
  | 'chart' | 'table' | 'timeline' | 'flow' | 'layer'
  | 'tree' | 'matrix' | 'process_arrow' | 'pyramid';

export type SlideType = 'cover' | 'content' | 'data' | 'section_break' | 'closing';

// ── Hierarchical planning: elicitor / outline / plan review ────────────────

export interface ElicitationQuestion {
  key: string;
  question: string;
  options: string[];
}

export interface ElicitResponse {
  run_id: string;
  is_sufficient: boolean;
  reasoning: string;
  questions: ElicitationQuestion[];
}

export interface OutlineSlide {
  slide_index: number;
  slide_title: string;
  slide_type: SlideType;
  section: string;
  narrative_role: string;
  key_messages: string[];
  data_anchors: string[];
  layout_intent: string;
  suggested_components: string[];
}

export interface OutlinePlan {
  deck_title: string;
  core_hook: string;
  slides: OutlineSlide[];
}

export interface OutlineRequest {
  prompt: string;
  theme?: string;
  deck_min_threshold?: number;
  supplied_content?: Record<string, unknown> | null;
  deck_settings?: DeckSettings | null;
  elicitation_answers?: Record<string, string> | null;
}

export interface OutlineResponse {
  run_id: string;
  elicitation_needed: boolean;
  questions: ElicitationQuestion[];
  outline: OutlinePlan | null;
}

export interface PlanReviewIssue {
  severity: 'high' | 'medium' | 'low';
  slide_index: number | null;
  type: string;
  description: string;
  suggestion: string;
}

export interface PlanReview {
  confidence_score: number;
  approved: boolean;
  summary: string;
  issues: PlanReviewIssue[];
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
