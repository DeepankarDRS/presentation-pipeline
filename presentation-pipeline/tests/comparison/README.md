# Slide Designer Comparison Test

## Purpose
Compare the pipeline's output (with the new weight/design_hint upgrade) against
a hand-crafted reference XML. Both produce the same slide from the same data.

## How to Run

### Step 1 — Generate via UI

1. Pull latest: `git pull`
2. Start the backend: `python -m uvicorn src.api:app --reload`
3. Start the frontend: `cd frontend && ng serve`
4. Open `http://localhost:4200`

### Step 2 — Enter this prompt

**Prompt** (paste into the text area):

```
Create a single executive dashboard slide for our Q3 FY26 board meeting.

Headline KPIs:
- ARR: $42.8M (+18% QoQ)
- Net Revenue Retention: 114% (+2 pts)
- Gross Margin: 72.1% (-1.4 pts)
- CAC Payback: 14 months (-2 months)

Revenue trend (quarterly):
- Q4 FY25: $28.4M
- Q1 FY26: $31.2M
- Q2 FY26: $36.1M
- Q3 FY26: $42.8M

Segment breakdown:
| Segment     | Revenue | QoQ Growth | % of ARR |
|-------------|---------|------------|----------|
| Enterprise  | $28.1M  | +22%       | 65.7%    |
| Mid-Market  | $10.4M  | +14%       | 24.3%    |
| SMB         | $4.3M   | +8%        | 10.0%    |

The revenue chart should be the hero — the thing the board sees first.
KPIs across the top as a quick scorecard. The segment table is supporting
context. Color-code the KPI deltas: green for positive, amber/red for negative.
The chart should feel like the centerpiece with the trend line emphasized.
```

**Settings:**
- Theme: **Sky Minimal**
- Slide count: **1**
- Content handling: **Preserve**
- Amount of text: **Concise**
- Write for: **Board**
- Tone: **Executive**
- Critic mode: **Auto** (under Advanced Options)

### Step 3 — Download and compare

1. Download the generated PPTX
2. Click "Review & Edit Slides" to see the XML and screenshot
3. Compare against `reference-output.xml` (compile it separately or
   view side-by-side in the slide review editor)

### Step 4 — Score both outputs

| Parameter              | System (1-5) | Reference (1-5) | Notes |
|------------------------|:------------:|:---------------:|-------|
| Data fidelity          |              |                 | Every number matches prompt exactly |
| Weight hierarchy       |              |                 | Chart visually dominates, title minimal |
| Visual differentiation |              |                 | KPI deltas color-coded, contrast used |
| Layout quality         |              |                 | No dead space, proportions intentional |
| Compilability          |              |                 | Valid POM, compiles to .pptx |
| Design polish          |              |                 | Radius, spacing, icons, badges |
| Readability            |              |                 | Font sizes right per band |
| **Total**              |    **/35**   |    **/35**      |       |

## Files
- `slide-designer-comparison.yaml` — test case definition
- `reference-output.xml` — hand-crafted reference POM XML
- `README.md` — this file
