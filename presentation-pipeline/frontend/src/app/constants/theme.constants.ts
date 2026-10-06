import { ThemeMood, ThemePalette } from '../models/api.models';

// Colors mirror src/knowledge/theme/palettes.yaml
export const THEME_PALETTES: ThemePalette[] = [
  { id: 'corporate-slate',  label: 'Corporate Slate',  tone: 'Corporate / cool blue',                  mode: 'light', accent: '2563EB', accentAlt: '0EA5E9', surface: 'F7F9FC', surfaceAlt: 'FFFFFF', textMain: '16202E', textMuted: '55627A', border: 'E2E8F0', chartColors: ['2563EB', '0EA5E9', '14B8A6', '6366F1', 'F59E0B'] },
  { id: 'sky-minimal',      label: 'Sky Minimal',      tone: 'Ocean blues on a pale sky wash',         mode: 'light', accent: '0077B6', accentAlt: '00B4D8', surface: 'EAF6FB', surfaceAlt: 'FFFFFF', textMain: '03045E', textMuted: '3E5C76', border: 'CFE6F2', chartColors: ['0077B6', '00B4D8', '03045E', '48CAE4', 'F59E0B'] },
  { id: 'teal-slate',       label: 'Teal Slate',       tone: 'Warm sand with deep teal and copper',    mode: 'light', accent: '0E7C7B', accentAlt: 'C8702A', surface: 'F3EFE7', surfaceAlt: 'FFFFFF', textMain: '12302F', textMuted: '5B6461', border: 'E2DCCF', chartColors: ['0E7C7B', 'C8702A', '5FA8A0', '12302F', 'E0B15A'] },
  { id: 'emerald-clean',    label: 'Emerald Clean',    tone: 'Crisp mint with emerald and lime',       mode: 'light', accent: '059669', accentAlt: '65A30D', surface: 'ECF8F2', surfaceAlt: 'FFFFFF', textMain: '053B2B', textMuted: '4B6B5E', border: 'CDEBDD', chartColors: ['059669', '65A30D', '0EA5E9', '065F46', 'FBBF24'] },
  { id: 'forest-editorial', label: 'Forest Editorial', tone: 'Forest green and amber on cream paper',  mode: 'light', accent: '2D5016', accentAlt: 'D4891A', surface: 'F5F0E8', surfaceAlt: 'FFFCF6', textMain: '1E2612', textMuted: '5E5A48', border: 'E3DACB', chartColors: ['2D5016', 'D4891A', '7A9A3A', '8C5A2B', 'B8C77A'] },
  { id: 'warm-editorial',   label: 'Warm Editorial',   tone: 'Terracotta and teal on peach cream',     mode: 'light', accent: 'C2410C', accentAlt: '1F6F78', surface: 'FAF1E9', surfaceAlt: 'FFFFFF', textMain: '3B2016', textMuted: '76594A', border: 'EEDCCD', chartColors: ['C2410C', '1F6F78', 'E9A06B', '7A4A32', '4D7C0F'] },
  { id: 'amber-mono',       label: 'Amber Mono',       tone: 'Navy ink with antique gold on ivory',    mode: 'light', accent: 'A87B1E', accentAlt: 'C9A84C', surface: 'F8F6F0', surfaceAlt: 'FFFFFF', textMain: '1B2A4A', textMuted: '5C6376', border: 'E6E0D2', chartColors: ['A87B1E', '1B2A4A', 'C9A84C', '6B7A99', '3F7D3A'] },
  { id: 'rose-report',      label: 'Rose Report',      tone: 'Blush with berry and wine',              mode: 'light', accent: 'BE185D', accentAlt: '6B2D5C', surface: 'FBF0F3', surfaceAlt: 'FFFFFF', textMain: '3A1026', textMuted: '7A5566', border: 'F0D9E1', chartColors: ['BE185D', '6B2D5C', 'F472B6', '9D174D', 'F59E0B'] },
  { id: 'violet-modern',    label: 'Violet Modern',    tone: 'Lavender with deep violet and coral',    mode: 'light', accent: '6D28D9', accentAlt: 'E8505B', surface: 'F5F2FF', surfaceAlt: 'FFFFFF', textMain: '2A1458', textMuted: '625A80', border: 'E4DDF7', chartColors: ['6D28D9', 'E8505B', 'A78BFA', '2A1458', 'F59E0B'] },
  { id: 'saascolor',        label: 'Saas Color',       tone: 'Navy on cream with orange + purple accents', mode: 'light', accent: 'F5821F', accentAlt: '673AB7', surface: 'F9F8F4', surfaceAlt: 'FFFFFF', textMain: '041E42', textMuted: '4E5D6E', border: 'E4E2D8', chartColors: ['F5821F', '673AB7', 'B39DDB', '2E7D32', 'A03B24'] },
  { id: 'navy-orange',      label: 'Navy Orange',      tone: 'Navy on white, orange + purple accents', mode: 'light', accent: 'F7941D', accentAlt: '673AB7', surface: 'FFFFFF', surfaceAlt: 'F4F3F0', textMain: '112340', textMuted: '5A6578', border: 'E8E6E3', chartColors: ['F7941D', '673AB7', 'B39DDB', '95A5B6', '2E7D32'] },
  { id: 'gj-h1',            label: 'GJ H1 Deck',       tone: 'Mint-grey with deep emerald, tomato-red and amber', mode: 'light', accent: '0D6B4E', accentAlt: '34D399', surface: 'F0F5F3', surfaceAlt: 'FFFFFF', textMain: '141F1C', textMuted: '5F706B', border: 'D5DDD9', chartColors: ['0D6B4E', '3B82F6', 'F59E0B', '94A3B8', '34D399'] },
  { id: 'graphite-mono',    label: 'Graphite Mono',    tone: 'Pure white and charcoal, electric blue', mode: 'light', accent: '0066FF', accentAlt: '6B7280', surface: 'FFFFFF', surfaceAlt: 'F2F3F5', textMain: '2C2C2C', textMuted: '5F6368', border: 'E1E3E6', chartColors: ['0066FF', '2C2C2C', '9CA3AF', '60A5FA', '4B5563'] },
  { id: 'graphite-dark',    label: 'Graphite Dark',    tone: 'Neutral blue-dark executive',            mode: 'dark',  accent: '60A5FA', accentAlt: '38BDF8', surface: '0F1729', surfaceAlt: '1E2A44', textMain: 'F1F5F9', textMuted: 'AAB7C7', border: '36455F', chartColors: ['60A5FA', '34D399', 'FBBF24', 'A78BFA', 'F472B6'] },
  { id: 'midnight-indigo',  label: 'Midnight Indigo',  tone: 'Deep indigo dark',                       mode: 'dark',  accent: '818CF8', accentAlt: 'A5B4FC', surface: '12122A', surfaceAlt: '232346', textMain: 'EEF0FB', textMuted: 'AAAECF', border: '3A3A63', chartColors: ['818CF8', '34D399', 'FBBF24', 'F472B6', '38BDF8'] },
  { id: 'forest-dark',      label: 'Forest Dark',      tone: 'Dark green',                             mode: 'dark',  accent: '4ADE80', accentAlt: '2DD4BF', surface: '0C1A14', surfaceAlt: '172C22', textMain: 'ECF5EF', textMuted: '9BB4A6', border: '2C4438', chartColors: ['4ADE80', '2DD4BF', 'FBBF24', '60A5FA', 'F472B6'] },
  { id: 'carbon-dark',      label: 'Carbon Dark',      tone: 'Charcoal neutral, warm orange',          mode: 'dark',  accent: 'FB923C', accentAlt: 'FBBF24', surface: '171717', surfaceAlt: '262626', textMain: 'F5F5F4', textMuted: 'A8A29E', border: '3F3F3F', chartColors: ['FB923C', 'FBBF24', 'A3E635', '38BDF8', 'F472B6'] },
];

// Theme picker filter groups for light palettes; dark palettes are grouped by mode.
export const THEME_MOODS: Record<string, ThemeMood> = {
  'corporate-slate': 'cool', 'sky-minimal': 'cool', 'graphite-mono': 'cool',
  'teal-slate': 'warm', 'forest-editorial': 'warm', 'warm-editorial': 'warm', 'amber-mono': 'warm',
  'emerald-clean': 'bold', 'rose-report': 'bold', 'violet-modern': 'bold',
  'saascolor': 'brand', 'navy-orange': 'brand', 'gj-h1': 'brand',
};

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
