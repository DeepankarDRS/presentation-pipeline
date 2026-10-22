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
  { id: 'boardroom-orange', label: 'Boardroom Orange', tone: 'Boardroom white, orange + purple', mode: 'light', accent: 'F4541E' },
  { id: 'paper-clay',       label: 'Paper Clay',       tone: 'Warm paper, clay + deep teal',     mode: 'light', accent: 'C0472A' },
  { id: 'bone-copper',      label: 'Bone Copper',      tone: 'Editorial bone, copper hero',      mode: 'light', accent: 'C46A3F' },
  { id: 'ocean-light',      label: 'Ocean Light',      tone: 'Ocean blues on white',             mode: 'light', accent: '0077B6' },
  { id: 'terracotta-light', label: 'Terracotta Light', tone: 'Verdigris + burnt peach',          mode: 'light', accent: '2A9D8F' },
  { id: 'ink-copper',       label: 'Ink Copper',       tone: 'Deep slate, copper hero',          mode: 'dark',  accent: 'C46A3F' },
  { id: 'lime-ink',         label: 'Lime Ink',         tone: 'Near-black, electric lime + rust', mode: 'dark',  accent: 'C9F24D' },
  { id: 'ocean-dark',       label: 'Ocean Dark',       tone: 'Deep twilight, aqua accents',      mode: 'dark',  accent: '48CAE4' },
  { id: 'tropic-dark',      label: 'Tropic Dark',      tone: 'Dark teal, emerald / pink / gold', mode: 'dark',  accent: '06D6A0' },
  { id: 'terracotta-dark',  label: 'Terracotta Dark',  tone: 'Charcoal blue, tuscan sun',        mode: 'dark',  accent: 'E9C46A' },
];

export const STEP_LABELS: Record<string, string> = {
  planning:          'Planning your deck...',
  elicitation_needed: 'Waiting for clarification...',
  reviewing_plan:    'Reviewing plan quality...',
  styling:           'Resolving theme...',
  generating_slide:  'Generating slides...',
  validating:        'Validating output...',
  repairing:         'Fixing issues...',
  reviewing:         'Reviewing quality...',
  assembling:        'Assembling deck...',
  complete:          'Done!',
  error:             'Error',
};

export const PROGRESS_RANGES: Record<string, [number, number]> = {
  planning:         [5, 15],
  reviewing_plan:   [15, 18],
  styling:          [18, 20],
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
  { label: 'Reviewing plan',        events: ['reviewing_plan'] },
  { label: 'Resolving theme',       events: ['styling'] },
  { label: 'Generating slides',     events: ['generating_slide'] },
  { label: 'Validating and fixing', events: ['validating', 'repairing'] },
  { label: 'Reviewing quality',     events: ['reviewing'] },
  { label: 'Assembling deck',       events: ['assembling'] },
];

// Mirrors SLIDE_COUNT_TO_THRESHOLD in src/agents/settings_mapper.py
export const SLIDE_COUNT_TO_THRESHOLD: Record<string, number> = {
  '1': 1, '3-5': 4, '6-10': 8, '10-15': 12, '15+': 16,
};
