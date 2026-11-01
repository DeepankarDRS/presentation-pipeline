import { ThemeMood, ThemePalette } from '../models/api.models';

// Colors mirror src/knowledge/theme/palettes.yaml
export const THEME_PALETTES: ThemePalette[] = [
  { id: 'corporate-slate',  label: 'Corporate Slate',  tone: 'Corporate / cool blue',                  mode: 'light', accent: '2563EB', accentAlt: '0D97D6', surface: 'F7F9FC', surfaceAlt: 'FFFFFF', textMain: '16202E', textMuted: '55627A', border: 'E2E8F0', chartColors: ['2563EB', '0EA5E9', '14B8A6', '6366F1', 'F59E0B'] },
  { id: 'sky-minimal',      label: 'Sky Minimal',      tone: 'Ocean blues on a pale sky wash',         mode: 'light', accent: '0077B6', accentAlt: '009AB9', surface: 'EAF6FB', surfaceAlt: 'FFFFFF', textMain: '03045E', textMuted: '3E5C76', border: 'CFE6F2', chartColors: ['0077B6', '00B4D8', '03045E', '3FC7E3', 'F59E0B'] },
  { id: 'teal-slate',       label: 'Teal Slate',       tone: 'Warm sand with deep teal and copper',    mode: 'light', accent: '0E7C7B', accentAlt: 'C8702A', surface: 'F3EFE7', surfaceAlt: 'FFFFFF', textMain: '12302F', textMuted: '5B6461', border: 'E2DCCF', chartColors: ['0E7C7B', 'C8702A', '5FA8A0', '12302F', 'DFAF56'] },
  { id: 'emerald-clean',    label: 'Emerald Clean',    tone: 'Crisp mint with emerald and lime',       mode: 'light', accent: '059669', accentAlt: '629E0D', surface: 'ECF8F2', surfaceAlt: 'FFFFFF', textMain: '053B2B', textMuted: '4B6B5E', border: 'CDEBDD', chartColors: ['059669', '65A30D', '0EA5E9', '065F46', 'E8A804'] },
  { id: 'forest-editorial', label: 'Forest Editorial', tone: 'Forest green and amber on cream paper',  mode: 'light', accent: '2D5016', accentAlt: 'BD7A17', surface: 'F5F0E8', surfaceAlt: 'FFFCF6', textMain: '1E2612', textMuted: '5E5A48', border: 'E3DACB', chartColors: ['2D5016', 'D4891A', '7A9A3A', '8C5A2B', 'ABBC61'] },
  { id: 'warm-editorial',   label: 'Warm Editorial',   tone: 'Terracotta and teal on peach cream',     mode: 'light', accent: 'C2410C', accentAlt: '1F6F78', surface: 'FAF1E9', surfaceAlt: 'FFFFFF', textMain: '3B2016', textMuted: '76594A', border: 'EEDCCD', chartColors: ['C2410C', '1F6F78', 'E9A06B', '7A4A32', '4D7C0F'] },
  { id: 'amber-mono',       label: 'Amber Mono',       tone: 'Navy ink with antique gold on ivory',    mode: 'light', accent: 'A87B1E', accentAlt: 'AA8A33', surface: 'F8F6F0', surfaceAlt: 'FFFFFF', textMain: '1B2A4A', textMuted: '5C6376', border: 'E6E0D2', chartColors: ['A87B1E', '1B2A4A', 'C9A84C', '6B7A99', '3F7D3A'] },
  { id: 'rose-report',      label: 'Rose Report',      tone: 'Blush with berry and wine',              mode: 'light', accent: 'BE185D', accentAlt: '6B2D5C', surface: 'FBF0F3', surfaceAlt: 'FFFFFF', textMain: '3A1026', textMuted: '7A5566', border: 'F0D9E1', chartColors: ['BE185D', '6B2D5C', 'F472B6', '9D174D', 'F59E0B'] },
  { id: 'violet-modern',    label: 'Violet Modern',    tone: 'Lavender with deep violet and coral',    mode: 'light', accent: '6D28D9', accentAlt: 'E8505B', surface: 'F5F2FF', surfaceAlt: 'FFFFFF', textMain: '2A1458', textMuted: '625A80', border: 'E4DDF7', chartColors: ['6D28D9', 'E8505B', 'A78BFA', '2A1458', 'F59E0B'] },
  { id: 'saascolor',        label: 'Saas Color',       tone: 'Navy on cream with orange + purple accents', mode: 'light', accent: 'F5821F', accentAlt: '673AB7', surface: 'F9F8F4', surfaceAlt: 'FFFFFF', textMain: '041E42', textMuted: '4E5D6E', border: 'E4E2D8', chartColors: ['F5821F', '673AB7', 'B39DDB', '2E7D32', 'A03B24'] },
  { id: 'navy-orange',      label: 'Navy Orange',      tone: 'Navy on white, orange + purple accents', mode: 'light', accent: 'F7941D', accentAlt: '673AB7', surface: 'FFFFFF', surfaceAlt: 'F4F3F0', textMain: '112340', textMuted: '5A6578', border: 'E8E6E3', chartColors: ['F7941D', '673AB7', 'B39DDB', '95A5B6', '2E7D32'] },
  { id: 'gj-h1',            label: 'GJ H1 Deck',       tone: 'Mint-grey with deep emerald, tomato-red and amber', mode: 'light', accent: '0D6B4E', accentAlt: '229D70', surface: 'F0F5F3', surfaceAlt: 'FFFFFF', textMain: '141F1C', textMuted: '5F706B', border: 'D5DDD9', chartColors: ['0D6B4E', '3B82F6', 'F59E0B', '94A3B8', '2CCC91'] },
  { id: 'claude-cream',     label: 'Claude Cream',     tone: 'Warm cream paper, slate ink and a single clay accent', mode: 'light', accent: 'C4623F', accentAlt: 'D56A46', surface: 'F0EEE6', surfaceAlt: 'FFFFFF', textMain: '141413', textMuted: '6B6A62', border: 'DDD9CC', chartColors: ['C4623F', '141413', 'B0AEA5', 'D4A27F', '3F7D4E'] },
  { id: 'graphite-mono',    label: 'Graphite Mono',    tone: 'Pure white and charcoal, electric blue', mode: 'light', accent: '0066FF', accentAlt: '6B7280', surface: 'FFFFFF', surfaceAlt: 'F2F3F5', textMain: '2C2C2C', textMuted: '5F6368', border: 'E1E3E6', chartColors: ['0066FF', '2C2C2C', '9CA3AF', '60A5FA', '4B5563'] },
  { id: 'graphite-dark',    label: 'Graphite Dark',    tone: 'Neutral blue-dark executive',            mode: 'dark',  accent: '60A5FA', accentAlt: '38BDF8', surface: '0F1729', surfaceAlt: '1E2A44', textMain: 'F1F5F9', textMuted: 'AAB7C7', border: '36455F', chartColors: ['60A5FA', '2BC78E', 'E3A504', 'A78BFA', 'F472B6'] },
  { id: 'midnight-indigo',  label: 'Midnight Indigo',  tone: 'Deep indigo dark',                       mode: 'dark',  accent: '818CF8', accentAlt: 'A5B4FC', surface: '12122A', surfaceAlt: '232346', textMain: 'EEF0FB', textMuted: 'AAAECF', border: '3A3A63', chartColors: ['818CF8', '2BC78E', 'E3A504', 'F472B6', '33BBF8'] },
  { id: 'forest-dark',      label: 'Forest Dark',      tone: 'Dark green',                             mode: 'dark',  accent: '4ADE80', accentAlt: '2DD4BF', surface: '0C1A14', surfaceAlt: '172C22', textMain: 'ECF5EF', textMuted: '9BB4A6', border: '2C4438', chartColors: ['24C75F', '28C4B1', 'E3A504', '60A5FA', 'F472B6'] },
  { id: 'carbon-dark',      label: 'Carbon Dark',      tone: 'Charcoal neutral, warm orange',          mode: 'dark',  accent: 'FB923C', accentAlt: 'FBBF24', surface: '171717', surfaceAlt: '262626', textMain: 'F5F5F4', textMuted: 'A8A29E', border: '3F3F3F', chartColors: ['FB923C', 'E8A804', '84C518', '38BDF8', 'F472B6'] },
  // Seed palettes (2026-10-22): values as the resolver derives them from palettes.yaml `seed:`
  { id: 'boardroom-orange', label: 'Boardroom Orange', tone: "Clean boardroom white, orange + purple brand accents", mode: 'light', accent: 'F4541E', accentAlt: '5B2A86', surface: 'FFFFFF', surfaceAlt: 'F8FAFC', textMain: '0F172A', textMuted: '6B7280', border: 'D1D4DB', chartColors: ['F4541E', '5B2A86', 'B23A2D', '15803D', '6B7280'] },
  { id: 'paper-clay', label: 'Paper Clay', tone: "Warm editorial paper, clay + deep teal", mode: 'light', accent: 'C0472A', accentAlt: '2D5063', surface: 'F1E9D6', surfaceAlt: 'FAF4E5', textMain: '1A1814', textMuted: '5A544A', border: 'C8B891', chartColors: ['C0472A', '2D5063', '4A7752', 'B07A1E', '6F8FA0'] },
  { id: 'bone-copper', label: 'Bone Copper', tone: "Editorial bone canvas, slate ink, copper hero", mode: 'light', accent: 'C46A3F', accentAlt: '233246', surface: 'EEE7D5', surfaceAlt: 'F4EEDE', textMain: '18222F', textMuted: '4A5A6E', border: 'CAC3B2', chartColors: ['C46A3F', '233246', '5F7A60', 'B6873B', '8C9CAD'] },
  { id: 'ocean-light', label: 'Ocean Light', tone: "Ocean blue serenity \u2014 white canvas, deep twilight ink", mode: 'light', accent: '0077B6', accentAlt: '009AB9', surface: 'F4FBFD', surfaceAlt: 'FFFFFF', textMain: '03045E', textMuted: '5F629A', border: '92E0F0', chartColors: ['0077B6', '00B4D8', '023E8A', '15803D', 'B45309'] },
  { id: 'terracotta-light', label: 'Terracotta Light', tone: "Charcoal blue ink, verdigris + burnt peach on warm white", mode: 'light', accent: '2A9D8F', accentAlt: 'E66848', surface: 'FAF7F2', surfaceAlt: 'FFFFFF', textMain: '264653', textMuted: '647479', border: 'D2D3CF', chartColors: ['2A9D8F', 'E76F51', '264653', 'F4A261', 'E1AF35'] },
  { id: 'ink-copper', label: 'Ink Copper', tone: "Deep slate statement slides, copper hero", mode: 'dark', accent: 'C46A3F', accentAlt: 'B6873B', surface: '18222F', surfaceAlt: '233246', textMain: 'F5EFE0', textMuted: '8C9CAD', border: '424A52', chartColors: ['C46A3F', '233246', '5F7A60', 'B6873B', '8C9CAD'] },
  { id: 'lime-ink', label: 'Lime Ink', tone: "Premium investor near-black, electric lime + rust", mode: 'dark', accent: 'C9F24D', accentAlt: 'C7572C', surface: '0E1116', surfaceAlt: '1A1F2A', textMain: 'F2EEE3', textMuted: '908A7D', border: '373B40', chartColors: ['91BC0E', 'C7572C', '6E7E6D', '1A1F2A', 'E3A504'] },
  { id: 'ocean-dark', label: 'Ocean Dark', tone: "Ocean blue serenity \u2014 deep twilight canvas, aqua accents", mode: 'dark', accent: '48CAE4', accentAlt: '90E0EF', surface: '03045E', surfaceAlt: '0B1470', textMain: 'CAF0F8', textMuted: '90E0EF', border: '2C3581', chartColors: ['0077B6', '00B4D8', '023E8A', '24C75F', 'DEA104'] },
  { id: 'tropic-dark', label: 'Tropic Dark', tone: "Dark teal canvas, emerald / pink / golden pop", mode: 'dark', accent: '06D6A0', accentAlt: 'FFD166', surface: '073B4C', surfaceAlt: '1A4A5A', textMain: 'F7FAFB', textMuted: 'A2B6BC', border: '37616F', chartColors: ['118AB2', 'EF476F', '06CC99', 'EBA400', '073B4C'] },
  { id: 'terracotta-dark', label: 'Terracotta Dark', tone: "Charcoal blue canvas, tuscan sun + sandy brown", mode: 'dark', accent: 'E9C46A', accentAlt: 'F4A261', surface: '264653', surfaceAlt: '37545F', textMain: 'F8F5EF', textMuted: 'BBC3C5', border: '526C75', chartColors: ['2A9D8F', 'E76F51', '264653', 'F49F5C', 'E0AB2C'] },
  // Perceptis templates (2026-10-27): mbb-blue from a real export, the others assumed from the swatches
  { id: 'mbb-blue', label: 'MBB Blue', tone: "Consulting white, navy ink, sky-blue accents (Perceptis MBB Blue)", mode: 'light', accent: '042440', accentAlt: '2A91CF', surface: 'FFFFFF', surfaceAlt: 'F2F0E9', textMain: '000000', textMuted: '6C6C6C', border: 'E0E0E0', chartColors: ['042440', '48A3DA', '1B6CB3', '808080', '15803D'] },
  { id: 'mbb-blue-dark', label: 'MBB Blue Dark', tone: "Deep navy canvas, sky-blue accents (Perceptis MBB Blue title slides)", mode: 'dark', accent: '48A3DA', accentAlt: '6FD2EF', surface: '051D2F', surfaceAlt: '0B266A', textMain: 'FFFFFF', textMuted: 'C5EDF8', border: '374A59', chartColors: ['48A3DA', '46C5EA', '1B6CB3', '808080', '26CF64'] },
  { id: 'perceptis', label: 'Perceptis', tone: "Consulting white, deep green ink, emerald + mint accents (Perceptis)", mode: 'light', accent: '084132', accentAlt: '009367', surface: 'FFFFFF', surfaceAlt: 'F2F0E9', textMain: '000000', textMuted: '6C6C6C', border: 'E0E0E0', chartColors: ['084132', '009367', '00C384', '808080', '15803D'] },
  { id: 'perceptis-dark', label: 'Perceptis Dark', tone: "Deep green canvas, mint accents (Perceptis title slides)", mode: 'dark', accent: '00C887', accentAlt: '6FE3B8', surface: '052A20', surfaceAlt: '084132', textMain: 'FFFFFF', textMuted: '9FE8CF', border: '37554D', chartColors: ['00C887', '009367', '808080', '26CF64', 'E8A804'] },
  { id: 'mbb-green', label: 'MBB Green', tone: "Consulting white, dark teal-green ink, sage accents (Perceptis MBB Green)", mode: 'light', accent: '005947', accentAlt: '367B69', surface: 'FFFFFF', surfaceAlt: 'F2F0E9', textMain: '000000', textMuted: '6C6C6C', border: 'E0E0E0', chartColors: ['005947', '6FA898', '808080', '15803D', 'B45309'] },
  { id: 'mbb-green-dark', label: 'MBB Green Dark', tone: "Dark teal-green canvas, sage accents (Perceptis MBB Green title slides)", mode: 'dark', accent: '5FBFA0', accentAlt: 'B9D9CF', surface: '03302A', surfaceAlt: '005947', textMain: 'FFFFFF', textMuted: 'B9D9CF', border: '355955', chartColors: ['5FBFA0', '8BC0AF', '367B69', '808080', '26CF64'] },
  { id: 'mbb-red', label: 'MBB Red', tone: "Consulting white, black ink, red accents (Perceptis MBB Red)", mode: 'light', accent: 'CC2225', accentAlt: '8C1A1C', surface: 'FFFFFF', surfaceAlt: 'F2F0E9', textMain: '000000', textMuted: '6C6C6C', border: 'E0E0E0', chartColors: ['CC2225', '8C1A1C', 'F28B8C', '979797', '4D4D4D'] },
  { id: 'mbb-red-dark', label: 'MBB Red Dark', tone: "Charcoal canvas, bright red accents (Perceptis MBB Red title slides)", mode: 'dark', accent: 'FD2729', accentAlt: 'F28B8C', surface: '1C1C1C', surfaceAlt: '2A2A2A', textMain: 'FFFFFF', textMuted: '979797', border: '494949', chartColors: ['FD2729', 'F28B8C', 'CC2225', '979797', '26CF64'] },
];

// Theme picker filter groups for light palettes; dark palettes are grouped by mode.
export const THEME_MOODS: Record<string, ThemeMood> = {
  'corporate-slate': 'cool', 'sky-minimal': 'cool', 'graphite-mono': 'cool',
  'teal-slate': 'warm', 'forest-editorial': 'warm', 'warm-editorial': 'warm', 'amber-mono': 'warm',
  'emerald-clean': 'bold', 'rose-report': 'bold', 'violet-modern': 'bold',
  'saascolor': 'brand', 'navy-orange': 'brand', 'gj-h1': 'brand',
  'claude-cream': 'warm',
  'paper-clay': 'warm', 'bone-copper': 'warm', 'terracotta-light': 'warm',
  'ocean-light': 'cool', 'boardroom-orange': 'brand',
  'mbb-blue': 'brand', 'perceptis': 'brand', 'mbb-green': 'brand', 'mbb-red': 'brand',
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
