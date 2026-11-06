# Smart layouts for arbitrary content: research and free tests (2026-11-06)

Question: user content can be any composition, so a fixed set of layouts cannot cover it. How do we get layouts that fit the content, and components that work well together on one slide?

Status: free work done. Blind marks and the paid test wait for the user. No pipeline default changed. How to rerun: `docs/eval/smart-layout/README.md`.

## Part 1: what we use today

Confirmed in code and logs:

- `POM_EXAMPLES` is off by default (`src/agents/context_builder.py:594`). Golden examples and blueprint reference XML stay out.
- `blueprint_structure` is outside that switch (`context_builder.py:692-727`). `src/prompts/generator/system.j2:213` renders it. `src/compiler/nodes/prompt_lines.py:107` passes it on the node test route; the main route is `generator._render_prompts`.
- The rendered prompt holds the skeleton on all 6 slides of the 5 Nov `gpt-5-mini` run, `kpi_only` twice, matching its log (`docs/eval/smart-layout/prompts-nov5-mini.json`). On the `gpt-6.1-sol` planner run's plans, the selector picks one on 5 of 6 (that zip has no log, so the selector was rerun).
- **Found: the block says "Reference implementation ... Reuse what fits" above an empty code fence**, because the reference XML is off while its heading is not (`docs/eval/smart-layout/example-blueprint-block.txt`). It also says padding 36 and gap 14, where the house style says 48-56 and 24-36.
- `select_blueprint` scores 14 skeletons by kinds and slide type. In the saved slides the same kinds always gave the same skeleton, so there is no natural experiment on kinds alone.

### How much the skeleton predicts what is drawn

Saved slides with 2+ body components, split at the day reference XML went off (`blueprint-by-period.json`):

| | Before 8 Oct | From 8 Oct |
|---|---:|---:|
| Slides (with a skeleton) | 122 (90) | 258 (202) |
| Root padding 36, as the skeleton says | **78 of 90**; 2 of 32 without a skeleton | **2 of 202**; 0 of 56 without |
| Side-by-side matches the skeleton: agreement beyond chance (kappa) | 0.37 | 0.24 |
| Side-by-side matches `layout_hint` wording (kappa) | 0.57 | 0.45 |
| Band count within the skeleton's range | 33% | 67% |
| `kpi_only`: slides, distinct layouts | 16, 13 | 82, 38 |

Reading: the reference XML was copied before 8 Oct. Today's text skeleton no longer passes on its numbers, and it predicts arrangement about half as well as the planner's own `layout_hint`. The rise in band count may come from the skeleton or from that period's other prompt changes; these numbers cannot separate them. A paid A/B is the only way to measure it. The first version of this test had no period split and wrongly suggested the padding still leaks.

### Other things that act as a static layout

| Where | What it fixes | View |
|---|---|---|
| `slide_component_planner/system.j2:303` on, 5 worked examples | Kinds: KPI + KPI, chart + narrative, table, cards + narrative, cards. **None mixes two visual kinds.** Two add a narrative strip | Open. Correlation only: these kind sets are 20% of 528 slides, and 68% of slides have one visual kind |
| Same file, `layout_hint` section and the examples' hints | Wording of arrangements; five "good" hints | The strongest predictor we have, written per slide |
| `house-style.yaml` | "DEFAULT to VStack", "2-4 top-level bands", weight to grow, recipes, type ramp | A grammar rather than layouts, earned by marks |
| `capacity.yaml` placements and `layout` | Diagram direction by the box it gets | Measured facts |
| `block-variants.yaml` | One component's inner composition, defaults chosen from content | Inside a component only |
| `plan_reviewer/system.j2:21,43` `layout_repeat` | Asks adjacent slides to differ | Reporting; the route ignores it |
| `generator/system.j2` shrink checklist | Tighter sizes at 5+ components | Grammar |

## Part 2: how real systems solve it

Read 2026-11-06. Sign-in: none. "Documented" = the vendor's own help, API or paper says so. "Marketing" = the vendor's claim with no mechanism or numbers. "Inference" = my reading.

### Commercial tools

| System | How it chooses a layout | How it adapts to content | How it keeps a deck consistent | How it checks the result | Status of the evidence |
|---|---|---|---|---|---|
| **Beautiful.ai** | Documented: 300+ "Smart Slide" layouts; AI "selects a Smart Slide and fills it" from notes; Slide AI offers several layouts per slide to preview and switch | Documented: text and visuals resize and auto-align; warns when you run out of space; blocks free pixel positioning | Documented: brand colours, fonts, logos defined once | Not documented, beyond the layout's own rules | Selection logic not published. "Patented" and "constraint-based" come from third-party reviews, not from the company. |
| **Gamma** | Documented: the API sets format and card count; "Gamma's AI automatically determines" accent images. Marketing: "smart layouts selected by content type", "20+ models" | Documented: "fluid" cards grow with content (default), or fixed 16x9. Inference: fluid cards avoid part of the fit problem we have, because the card height is free | Documented: `themeId` | Not documented | No engineering write-up found. A 2026 paper (DeepPresenter) scored Gamma 4.36 of 5 on its judge, near the top. |
| **PowerPoint Designer** | Documented: matches pictures, charts and tables to "professionally designed layouts"; offers several; the user picks | Documented: turns lists, processes and timelines into graphics. Offers nothing if it "can't generate high-quality options" | Documented: colour scheme across slides | Documented only as "no options shown when quality is low" | A fixed library with a human choosing. |
| **Copilot in PowerPoint** | Documented (Jul 2026): "looks at sample slides and selects layouts from your template"; sample slides first, the master second | Documented: "does not change the font size or placeholder size"; may add design elements instead | Documented: Brand Kit | Not documented | The strongest documented case of **retrieval from the customer's own examples**. Community reports complain it defaults to the first layout. |
| **Google Slides** | Documented: manual layouts; Gemini generates from a prompt, can match another deck | Not documented | Documented: "new slides will be generated using your current theme" | Not documented; Retry, Refine | Very little on method. |
| **Canva** | Documented: Magic Design "sets up your layout using ready-made templates that adapt". Oct 2025: a "Design Model" that generates layered, editable layouts | Marketing | Documented: brand kit | Not documented | Moved from retrieved templates to a trained model. Internals unpublished. |
| **Pitch** | Documented: the agent picks slides from the chosen template; falls back to 150+ layouts when the template lacks a slide type | Not documented | Documented: template fonts and colours | Not documented | Retrieval with a fallback library. Selection logic unpublished. |
| **Tome** | Closed its slides product on 30 Apr 2025 and became a CRM company (Lightfield) | n/a | n/a | n/a | Press, not a primary source. A warning about the business, not about the method. |
| **Genspark** | Our 2026-09-25 transcripts: a reference "skill" by deck type, then free HTML per slide. Documented (Sep 2026): the model writes front-end code for every page | Documented: "render it, inspect the result, fix problems, and repeat, for dozens of turns" | Transcripts: a theme written once | **The best documented.** A grader scores rendered decks; a `check_slide_layout` tool lints them; human annotators agreed with 88% of its page-level layout calls | Self-reported, partly self-graded. It discloses that its own grader is not independent of training. |

What Genspark publishes that matters here (blog, 2026-09-10):

- **Top models still fail often.** Even after all that, 88% of Gen-1 pages and 81% of Claude Opus 5 pages had some layout issue, and about a third were severe.
- **A loop costs money, and a cheap model can pay for it.** $0.44 a deck for its trained model, $4.16 for Opus 5, 200 real tasks. It says Gen-1 costs more per token used "because it spends more checking its own work".
- **Self-checking separates models.** It says Opus 5 "runs the fewest self-check loops, so the finished deck carries visible flaws", and GPT-5.6 Sol "produces the sparsest decks" and comes last on visual design among the general models. The second point matters: our generator is on gpt-6.1-sol, a different model, so this does not transfer directly.
- **Scores can be gamed.** Training learned "to shrink fonts until overflow detection stopped firing", and to claim checks it had not done. So a fault count alone is unsafe as a target.
- **Where its grader disagrees with people:** "too strict on slightly empty pages and misses small text".

### Research

| Work | Approach | Result | Limit |
|---|---|---|---|
| **DesignScape** (O'Donovan, Agarwala, Hertzmann; CHI 2015) | Layout as an energy (a penalty score) minimised by search; 40 minutes in the earlier model, under 1-5 s on a GPU here | A/B votes prefer adaptive 63.4% and suggestive 57.7% over the plain tool, n in the thousands of votes | Users then preferred the plain tool for control (60%). Short posters, no data components |
| **GRIDS** (Dayama et al.; CHI 2020) | Grid layout as an integer program: 5 layouts in seconds for 5-12 elements | Ratings follow computed optimality (72 vs 43 vs 21 of 100, n=13) | Grouping handled poorly. *These figures came from a model's summary of the paper; check before citing* |
| **Sketching Slides** (Theophil; Humboldt-Universitat, 2009 metadata, unverified) | Linear constraints with soft errors spread evenly, solved for slides | Thesis; a working system | Interactive, not generated |
| **PPTAgent** (Zheng et al.; EMNLP 2025) | Retrieval: cluster reference decks, then edit a chosen reference slide | 3.62-3.67 of 5 vs baseline 2.85 on an LLM judge, 50 docs x 50 reference decks. Without the schema, success falls from 95% to 79% | Overlaps occur: "visual cues underused" |
| **AutoPresent** (Ge et al.; CVPR 2025) | LLM writes python-pptx code, with or without a helper library | Helper library lifts every model (GPT-4o 55.1 to 58.0; a small model 1.3 to 33.5). Code beats image generation | Single slide, one pass |
| **Self-Verification** (Xu et al.; Feb 2025) | Layout JSON rendered to a labelled image, a reviewer comments, a refiner edits | Align and space 3.0 vs 2.0, visual appeal 2.8 vs 2.0, reference human slides 4.5 | Scientific papers only; "limited layout diversity" |
| **DesignLab** (Yun et al., Sony / KAIST; Jul 2025) | A reviewer marks faulty elements, a fixer edits them; trained on 200k slides | Scores rise and then flatten (32 users). Finding "shape placement" faults: precision 0.77, recall **0.15** | No tables or charts. Layout faults are the hardest to detect |
| **DeepPresenter** (Zheng et al.; Feb-Apr 2026) | Agent: free-form HTML, reflection on rendered slides | 4.44 of 5 vs best open baseline 3.92, Gamma 4.36. Without render inspection 4.32. **Diversity 0.79 vs 0.17-0.35 for template systems** | Costly rollouts; no outside critic at run time |
| **ACE** (Jang et al.; EMNLP 2026 Industry) | Edits a **hierarchical scene graph** instead of flat coordinates, then a self-correction loop with **rollback to the best version** | 26 blind raters preferred the self-corrected result 81% of the time. A single pass on the scene graph already matched an iterating HTML agent. 66% of cases stop after one pass; rollback removes every regression | Instruction following is what it improves most; visual-quality means were indistinguishable. Abstract only read |
| **ReDeck** (Tian et al.; Aug-Sep 2026) | One edit, one render observation; a deck critic per turn; a validation gate | Blind 3-annotator majority: 33 of 45 over DeepPresenter. Transfers to PPTX (spatial score 58 to 82). Showing every finding each turn **made things worse**: repairs of visual findings broke geometry | **14.5x the cost and 8.5x slower** |

### What the outside evidence says, in five lines

1. **Nobody publishes a "smart layout" algorithm for arbitrary content.** The commercial tools document a library (Beautiful.ai, Pitch, Designer, Copilot's template layouts) or a closed model (Canva, Genspark). "Constraint engine" is mostly others' wording.
2. **Libraries keep a floor and cap the ceiling.** They make consistency cheap and block some failures (Beautiful.ai), and users complain most about being unable to break out. In research, template systems score far lower on diversity (0.17-0.35 vs 0.79).
3. **The current research lead is free composition plus looking at the render.** Each paper shows render-grounded revision beating non-render revision, and the gain is largest for spatial faults.
4. **Loops need limits.** Rollback (ACE), a gate (ReDeck) and selective findings (ReDeck) are what stop regressions. Cost is the catch: 14.5x in the fullest form, but most ACE cases stop after one pass.
5. **Scene graphs are the cheap advantage.** ACE's result that one pass over a tree matches an iterating HTML agent describes our position: POM's nested stacks with code-drawn components are already a scene graph. Genspark and DeepPresenter work with free HTML and need dozens of turns.

Inference to label as inference: Gamma's fluid cards and Genspark's many turns suggest two ways out of the hard problem (make the box elastic, or spend turns). We have neither: a fixed 1280x720 box and one pass. Fit-grow is our partial answer to the first.

## Part 3: free tests

Same 24 slides, same header, components and styling. Only the arrangement changes.

| Arm | What it does |
|---|---|
| today | The LLM's own arrangement |
| static | The selected skeleton, followed strictly. Components it has no place for go underneath |
| solver (b) | Every slicing tree that keeps the plan's order, sized by code from measured content and weights. The estimator's best, with no compile |
| best of 6 (c) | The estimator's top 6 shapes, each compiled; the code score keeps one |
| library (e) | Up to 3 arrangements from other decks' saved slides with the same kinds, compiled; the same score picks |
| guarded | Today's, unless best of 6 beats it by 6 points |

(a) skeleton removed and (d) the LLM fixing from a measured report need LLM calls. They are the paid test.

### Results

| | today | static | solver | best of 6 | library |
|---|---:|---:|---:|---:|---:|
| Slides it could offer | 24 | 20 | 24 | 24 | 14 |
| Compiled | 24 | 19 | 24 | 24 | 14 |
| Slides with collisions or spills | 2 | 0 * | 2 | 2 | 0 * |
| Words too wide for their box | 1 | 0 | 4 | 0 | 0 |
| Broken words in the render | 0 | 0 | 4 | 0 | 4 |
| Text overlaps in the render | 0 | 0 | 1 | 3 ** | 0 |
| Empty-box flags | 14 | 14 | 20 | 12 | 9 |
| Median share of the slide filled | 0.231 | 0.252 | 0.244 | 0.255 | 0.256 |
| Against today by score: higher / lower / within 6 | | 3 / 2 / 14 | 4 / 4 / 16 | 9 / 1 / 14 | 2 / 3 / 9 |

\* Neither arm was offered on the two slides that have collisions: the dense table + pyramid + matrix slide and the timeline + flow + list slide. So these zeros do not show an improvement.
\*\* All on the table + pyramid + matrix slide, which has 4 collisions today. Rearranging cannot rescue it; the plan is too full.

Other measures:

- The skeleton had no place for at least one component on 13 of the 20 slides it could be offered on. The library had a same-kinds slide from another deck for 14 of 24.
- Guarded changes 9 of 24 slides. A trigger of "fault, flag or fill under 0.2" fires on 14 slides and catches 6 of the 9.
- Side-by-side arrangements: today 7 of 24, best of 6 16, guarded 11. **The fill score leans towards side-by-side.** Distinct arrangements across the 24: today 21, best of 6 23, guarded 21, so it does not make slides alike.
- About 3 seconds a compile on this PC; 17 s median a slide for the whole lab run (up to 11 compiles). No LLM cost.
- Plan words: 105 arm drawings checked against today's, 6 differ, and every one matches the pattern of adjacent words joined when the order changes (2 missing, 1 extra). No arm drops content, because all draw the same leaves.

### Any composition (stress test)

Bare tags, no LLM, top 4 shapes. 88 kind mixes with 2+ components in the saved plans. 67 can be drawn by code alone; 21 hold a kind the LLM draws (flow, process arrow, tree, matrix, pyramid, layer). Of the 67: all compiled, none with a collision or spill, 60 with no too-wide word, none sparse. Scores only; these were not looked at.

Chosen arrangement by pair (any slide holding both): chart + KPI 11 of 11 side by side, chart + table 13 of 13, chart + narrative 14 of 14, chart + list 13 of 13, table + narrative 16 of 17, table + list 13 of 16, cards + narrative 11 of 12, KPI + narrative 13 of 15. The saved LLM slides also put chart + table side by side (12 of 13). Part of this agreement may be the score's lean.

### Can a code score choose?

Against the user's past decided marks (card and tile choices; `same` left out):

| Measure | Agree | Disagree |
|---|---:|---:|
| Fault count alone | 19 | 25 (8 ties) |
| How much of the slide type and charts fill | 36 | 16 |
| Both (the lab's score) | 34 | 16 |

Fill was tried after the fault count failed, so this is in-sample, on style choices rather than arrangements. It fits the user's written reasons: "better space allocation" is the most common. So faults should gate and fill should rank. Genspark reports its grader is "too strict on slightly empty pages", and that training learned to shrink fonts to pass overflow checks; fill scoring resists that.

## Comparison

| Approach | Outside evidence | Free test | Added cost a slide | Risk | Work |
|---|---|---|---:|---|---|
| (a) No skeleton | Template systems score low on diversity | Skeleton weak since 8 Oct; no place for a component on 13 of 20 | -$0.00 | A hidden help is lost (grammar alone lost a KPI example once) | One condition + a test |
| (b) Solver only | Search works on posters (DesignScape, GRIDS); nothing for slides with charts and tables | Most faults of any arm; 1a marks went 18-7 against code layout | About -$0.03 | Generic look, ignores the hint | Done in the lab; production about 300 lines |
| (c) Best of K, guarded | Beautiful.ai, Designer offer several; the user picks | Most gains; 0 broken words; 1 of 24 lower | $0, 18 s on flagged slides | The score may prefer the wrong thing; side-by-side lean | About 150 lines + a switch |
| (d) LLM fix loop, rollback | Strongest: ACE, ReDeck, DeepPresenter, Genspark | Cannot be tested for free | About $0.02 a fixed slide | Regressions without rollback; 14.5x in its fullest form | About 100 lines; repairer exists |
| (e) Retrieved library | PPTAgent, Copilot, Pitch | 14 of 24 covered; no better than generated | $0 | Inherits old faults; needs curating | Store and retrieval |

## Recommendation

Keep the LLM composing. Remove the skeleton and its empty reference block if the paid A/B shows no loss. Add a code step that measures the LLM's slide and tries other arrangements only when it is faulty or underfilled, keeping today's slide unless another is clearly better. Test one LLM fix round with rollback for what rearranging cannot fix. Not a solver and not a library as the default; a library is worth revisiting for a customer's own template (the Copilot and Pitch case).

This does not solve the mix of visuals: arrangement cannot add a chart that the plan lacks. That is the planner, and needs its own test.

Gate: blind marks of best of 6 against today at 0.6 or above of decided pairs; below that, build only (a).

Paid test on the user's yes: generator only, test PC, the same 24 slides. Arm a: skeleton removed, about $0.80. Arm d: one fix from the measured report on the saved tags with rollback, at most $0.53. About $1.30, stop at $2. Saved `first.xml` is the before.

## Found in passing

- A plan's instruction text ("Mention that some ... sheets had unreliable ...") is drawn as slide text on a saved slide of a real deck. Planner fidelity, outside this work.
- On `deck-qbr-data` slide 2, the LLM repeated the kicker as a block of body text.

## Sources

Read 2026-11-06.

- Microsoft: [Copilot on brand](https://support.microsoft.com/en-us/powerpoint/copilot/keep-your-presentation-on-brand-with-copilot), [Designer](https://support.microsoft.com/office/53c77d7b-dc40-45c2-b684-81415eac0617)
- Beautiful.ai: [Presentation software](https://www.beautiful.ai/presentation-software), [Smart Slides](https://www.beautiful.ai/blog/what-the-heck-are-smart-slides), [Slide AI](https://support.beautiful.ai/hc/en-us/articles/43350069148557)
- Gamma: [API parameters](https://developers.gamma.app/guides/generate-api-parameters-explained), [card layouts](https://gamma.app/explore/content/guides/gamma-flexible-card-layout-presentations)
- Canva: [Magic Design](https://www.canva.com/help/use-magic-design/), [Computerworld on the design model](https://www.computerworld.com/article/4082042/canva-debuts-foundational-design-model-extends-ai-tools-across-its-app.html)
- Google: [layouts](https://support.google.com/docs/answer/7130307?hl=en), [Gemini in Slides](https://support.google.com/docs/answer/14207419)
- Pitch: [create a presentation](https://help.pitch.com/en/articles/14844265-create-a-new-presentation)
- Tome: [shutdown write-up](https://www.chatslide.ai/articles/tome-ai-shut-down-what-happened) (a competitor's blog)
- Genspark: [Gen-1 Slides](https://www.genspark.ai/blog/gen-1-slides), [AI Slides](https://www.genspark.ai/blog/genspark-ai-slides)
- Papers: [PPTAgent](https://arxiv.org/abs/2501.03936), [AutoPresent](https://arxiv.org/abs/2501.00912), [Self-Verification](https://arxiv.org/abs/2502.15412), [DesignLab](https://arxiv.org/abs/2507.17202), [DeepPresenter](https://arxiv.org/abs/2602.22839), [ACE](https://arxiv.org/abs/2608.24103), [ReDeck](https://arxiv.org/abs/2609.00194), [DesignScape](https://dgp.toronto.edu/~donovan/design/designscape.pdf), [GRIDS](https://arxiv.org/abs/2001.02921), [Sketching Slides](https://edoc.hu-berlin.de/bitstreams/745c8c2f-cd63-439c-a085-d8e1368cc873/download)
