export type CriticMode = 'auto' | 'manual' | 'off';

export interface GenerateRequest {
  prompt: string;
  theme: string;
  critic_mode: CriticMode;
  deck_min_threshold: number;
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

export type AppView = 'form' | 'progress' | 'result';

export interface ThemePalette {
  id: string;
  label: string;
  tone: string;
  mode: 'light' | 'dark';
  accent: string;
}
