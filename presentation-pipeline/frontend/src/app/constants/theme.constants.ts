import { ThemePalette } from '../models/api.models';

export const THEME_PALETTES: ThemePalette[] = [
  { id: 'corporate-slate',  label: 'Corporate Slate',  tone: 'Corporate / cool blue',           mode: 'light', accent: '2563EB' },
  { id: 'sky-minimal',      label: 'Sky Minimal',      tone: 'Airy / high-key blue',            mode: 'light', accent: '0284C7' },
  { id: 'teal-slate',       label: 'Teal Slate',       tone: 'Cool grey with teal accent',      mode: 'light', accent: '0F766E' },
  { id: 'emerald-clean',    label: 'Emerald Clean',    tone: 'Fresh / green',                   mode: 'light', accent: '047857' },
  { id: 'forest-editorial', label: 'Forest Editorial', tone: 'Deep forest green on warm paper', mode: 'light', accent: '3F6212' },
  { id: 'warm-editorial',   label: 'Warm Editorial',   tone: 'Warm / terracotta on cream',      mode: 'light', accent: 'C2410C' },
  { id: 'amber-mono',       label: 'Amber Mono',       tone: 'Near-monochrome warm, amber',     mode: 'light', accent: 'B45309' },
  { id: 'rose-report',      label: 'Rose Report',      tone: 'Warm neutral with rose accent',   mode: 'light', accent: 'BE123C' },
  { id: 'violet-modern',    label: 'Violet Modern',    tone: 'Modern / purple',                 mode: 'light', accent: '6D28D9' },
  { id: 'graphite-mono',    label: 'Graphite Mono',    tone: 'Monochrome grey, blue pop',       mode: 'light', accent: '1D4ED8' },
  { id: 'graphite-dark',    label: 'Graphite Dark',    tone: 'Neutral blue-dark executive',     mode: 'dark',  accent: '60A5FA' },
  { id: 'midnight-indigo',  label: 'Midnight Indigo',  tone: 'Deep indigo dark',                mode: 'dark',  accent: '818CF8' },
  { id: 'forest-dark',      label: 'Forest Dark',      tone: 'Dark green',                      mode: 'dark',  accent: '4ADE80' },
  { id: 'carbon-dark',      label: 'Carbon Dark',      tone: 'Charcoal neutral, warm orange',   mode: 'dark',  accent: 'FB923C' },
];

export const STEP_LABELS: Record<string, string> = {
  planning:         'Planning your deck...',
  styling:          'Resolving theme...',
  generating_slide: 'Generating slides...',
  validating:       'Validating output...',
  repairing:        'Fixing issues...',
  reviewing:        'Reviewing quality...',
  assembling:       'Assembling deck...',
  complete:         'Done!',
  error:            'Error',
};

export const PROGRESS_RANGES: Record<string, [number, number]> = {
  planning:         [5, 15],
  styling:          [15, 20],
  generating_slide: [20, 70],
  validating:       [70, 80],
  repairing:        [70, 80],
  reviewing:        [80, 90],
  assembling:       [90, 95],
  complete:         [100, 100],
};

export interface PipelinePhase {
  label: string;
  events: string[];
}

export const PIPELINE_PHASES: PipelinePhase[] = [
  { label: 'Planning your deck',    events: ['planning'] },
  { label: 'Resolving theme',       events: ['styling'] },
  { label: 'Generating slides',     events: ['generating_slide'] },
  { label: 'Validating and fixing', events: ['validating', 'repairing'] },
  { label: 'Reviewing quality',     events: ['reviewing'] },
  { label: 'Assembling deck',       events: ['assembling'] },
];
