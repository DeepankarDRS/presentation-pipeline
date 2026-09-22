# Graph Report - presentation-pipeline  (2026-09-22)

## Corpus Check
- 187 files · ~122,373 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1531 nodes · 3032 edges · 120 communities (64 shown, 48 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 143 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- API & HTTP Layer
- Context Builder
- Slide Repairer
- Plan Reviewer
- Architecture Overview
- Repair Budget Split
- Visual Critic
- Deck Assembly
- Frontend Slide Review
- Outline & Edit Service
- Evaluator Pipeline
- Layout Audit
- Graph Routing
- Outline Planner Schema
- Slide Edit Service
- Screenshot Backend
- Runner & Logging
- XML Normalizer
- Repairer Core
- Repair Guidance
- Layout Audit Checks
- Graph Construction
- Pipeline State
- Case Loader
- Frontend App Shell
- Validator
- Graph Routing Logic
- Evaluator & Generator
- Generator Inner
- Frontend Plan Editor
- Component Concepts
- Style Resolver
- Compile Graph
- Angular CLI Deps
- Angular Core Deps
- Angular Schematics
- Frontend API Models
- Questionnaire Agent
- Elicitor Agent
- Deck Settings Form
- Angular Build Options
- Frontend Progress & Prompt
- Context Builder Core
- Knowledge Components
- Node Package Deps
- Validator Node
- Deck Test Cases
- Angular Serve Config
- Normalizer Fixes
- Critic Inner
- Slide Component Planner
- Slide Replanner Tests
- Angular Project Config
- Frontend Package
- Phase Test Cases
- Angular Build Config
- LI Nesting Scripts
- Slide Review Component
- Base Test Cases
- POM Compiler
- Angular i18n & Test
- Render Check Script
- Card Recipes
- Typography & Hierarchy
- Graph Test Mocks
- Spacing & Composition
- Golden Fixtures
- Jasmine Core
- Karma Runner
- Karma Chrome Launcher
- Karma Coverage
- Karma Jasmine
- Tailwind CSS
- Frontend Index
- Accent Elements
- Chart Sizing
- Test Conftest
- Layout Audit Col Width
- Layout Audit Dims
- Any Type
- BaseModel
- Test Case Phases
- Deck State Architecture
- Loosely Coupled Architecture
- Pipeline Tool Architecture
- Reentry Points
- Prompt Form TS
- Slide Review TS
- Fable Dashboard Test
- Package Metadata
- PresentationState
- Python Requirements
- CB PresentationState
- CB SlidePlan
- Critic PresentationState
- Deck PresentationState
- Generator PresentationState
- Repairer PresentationState
- Planner PresentationState
- Planner SlidePlan
- Graph PresentationState
- Common Attributes
- Content Invention
- Design Variety
- Hero Panel
- Bullet List Recipe
- Icon Bullet List
- Layer Diagram
- Pitch Deck Case
- Pyramid Strategy Case
- Tree Org Chart Case
- CB SlidePlan Test

## God Nodes (most connected - your core abstractions)
1. `initial_state()` - 87 edges
2. `PresentationState` - 53 edges
3. `audit_layout()` - 45 edges
4. `build_graph()` - 30 edges
5. `critic_node()` - 27 edges
6. `evaluator_node()` - 26 edges
7. `build_contract()` - 26 edges
8. `PlannerSlide` - 22 edges
9. `repairer_node()` - 22 edges
10. `normalize_xml()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Generation Contract (Knowledge Base Assembly)` --semantically_similar_to--> `Context Builder Node (Mechanical)`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `Two-Strategy Repair (PATCH/REGENERATE)` --semantically_similar_to--> `Repairer Node (PATCH/REGENERATE Strategy)`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `Pre-Generation Clarification Questions` --semantically_similar_to--> `Questionnaire Node (Interactive)`  [INFERRED] [semantically similar]
  GENOFFICE_FEATURE_ADOPTION.md → CODE_FLOW.md
- `Dedicated Style Skill (LLM Style Generation)` --semantically_similar_to--> `Style Resolver Node (Theme Resolution)`  [INFERRED] [semantically similar]
  GENOFFICE_FEATURE_ADOPTION.md → CODE_FLOW.md
- `Layout Variety Enforcement (Adjacent Dedup)` --semantically_similar_to--> `Layout Variety Enforcement Discarded by Context Builder`  [INFERRED] [semantically similar]
  GENOFFICE_FEATURE_ADOPTION.md → CODE_REVIEW.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Deck Mode Quality Gaps** — code_review_deck_critic_accounting, code_review_deck_validation_weakness, code_flow_slide_router_node, code_flow_deck_assembler_node [EXTRACTED 1.00]
- **Design Language Visual System** — src_knowledge_core_design_language_visual_hierarchy, src_knowledge_core_design_language_color_usage, src_knowledge_core_design_language_spacing, src_knowledge_core_design_language_card_recipe [EXTRACTED 1.00]
- **Generate-Validate-Repair Feedback Loop** — architecture_generator, architecture_validator, architecture_repairer, architecture_retry_loop, architecture_stall_detection, code_flow_routing_logic [EXTRACTED 1.00]
- **House Style Layout System** — src_knowledge_core_house_style_frame, src_knowledge_core_house_style_sizing_vocabulary, src_knowledge_core_house_style_height_budget, src_knowledge_core_house_style_composition [EXTRACTED 1.00]
- **Knowledge Base Drives XML Generation** — architecture_knowledge_base, architecture_context_builder, flow_generation_contract, architecture_generator [EXTRACTED 1.00]
- **LLM Test Family A Base-Prompt Cases** — tests_llm_test_plan_test_plan, tests_cases_base_competitor_comparison_test_case, tests_cases_base_org_structure_test_case, tests_cases_base_overstuffed_test_case, tests_cases_base_process_overview_test_case, tests_cases_base_quarterly_metrics_test_case [EXTRACTED 1.00]
- **LLM Pipeline Steps (Hierarchical Planning)** — models_elicitor_step, models_outline_planner_step, models_slide_component_planner_step, models_generator_step, models_critic_step, models_repairer_step, models_visual_critic_step, models_slide_editor_step [EXTRACTED 1.00]
- **Dual-Budget Repair System** — docs_repair_budget_split_compile_repairer_strategy, docs_repair_budget_split_visual_repairer_strategy, docs_repair_budget_split_visual_repairer_node, docs_repair_budget_split_safety_rules [EXTRACTED 1.00]
- **** — tests_cases_base_revenue_trend_yaml, tests_cases_base_risks_yaml, tests_cases_base_roadmap_yaml, tests_cases_base_strategy_statement_yaml, tests_cases_base_vague_yaml [EXTRACTED 1.00]
- **** — tests_cases_chart_and_narrative_yaml, tests_cases_chart_and_table_yaml, tests_cases_comparison_matrix_yaml, tests_cases_dark_theme_yaml, tests_cases_financial_report_yaml, tests_cases_flowchart_yaml, tests_cases_inline_formatting_yaml [EXTRACTED 1.00]
- **** — tests_cases_deck_qbr_yaml, tests_cases_deck_qbr_data_yaml, tests_cases_deck_board_update_yaml, tests_cases_deck_sales_enablement_yaml, tests_cases_deck_sales_data_yaml [INFERRED 0.85]
- **Rigid Component Recipe Collection** — src_knowledge_core_recipes_chart_card, src_knowledge_core_recipes_table_card, src_knowledge_core_recipes_timeline, src_knowledge_core_recipes_matrix, src_knowledge_core_recipes_process_arrow, src_knowledge_core_recipes_flow, src_knowledge_core_recipes_pyramid, src_knowledge_core_recipes_tree [INFERRED 0.95]

## Communities (120 total, 48 thin omitted)

### Community 0 - "API & HTTP Layer"
Cohesion: 0.05
Nodes (76): Enum, FileResponse, get, post, put, edit_slide_xml(), Apply a user's NL edit to a slide XML, validate, and repair if needed. Returns…, _build_event() (+68 more)

### Community 1 - "Context Builder"
Cohesion: 0.06
Nodes (71): _all_recipes(), build_contract(), _build_node_attributes(), _build_node_hierarchy(), _clean_list(), context_builder_node(), _detect_components_from_text(), _fmt_house_style_value() (+63 more)

### Community 2 - "Slide Repairer"
Cohesion: 0.06
Nodes (50): _cap_xml(), _choose_strategy(), _collect_problems(), Pick PATCH or REGENERATE for this attempt. The loop is "PATCH, REGENERATE…, Choose a repair strategy, build the prompt, call the LLM, update state., Keep head + tail of XML so root setup and closing tags are visible., Collect error strings from normalize_result, compile_result, and critic_result., repairer_node() (+42 more)

### Community 3 - "Plan Reviewer"
Cohesion: 0.07
Nodes (57): parametrize, PlanReviewerOutput, PlanReviewIssue, BaseModel, Pydantic models for the plan reviewer agent's structured output., PlannerComponent, PlannerSlide, BaseModel (+49 more)

### Community 4 - "Architecture Overview"
Cohesion: 0.05
Nodes (54): Node.js Compiler Bridge (Subprocess), Context Builder Node (Mechanical), Visual Critic Node (Vision LLM Quality Gate), Evaluator Node (Scoring + Manifest), Generator Node (LLM XML Generation), YAML Knowledge Base, LangGraph Presentation Pipeline, Planner Node (LLM Structured Output) (+46 more)

### Community 5 - "Repair Budget Split"
Cohesion: 0.05
Nodes (48): Compile Repairer Strategy Decision, Repair Budget Split Design, Repair Safety Rules, Separate Budgets with Safe Discard, Visual Repairer Node, Visual Repairer Strategy Decision, Few-Shot Over Rules Lesson, Outline Planner Rewording Backfire (+40 more)

### Community 6 - "Visual Critic"
Cohesion: 0.10
Nodes (42): critic_node(), Visual quality gate — screenshot-based review using a vision LLM., CriticIssue, CriticOutput, BaseModel, Pydantic models for the critic's structured LLM output. Used with…, One issue found by the critic., Complete critic review output. (+34 more)

### Community 7 - "Deck Assembly"
Cohesion: 0.08
Nodes (39): assemble_deck_xml(), deck_assembler_node(), _extract_slide_block(), _extract_theme(), Any, Path, Deck multi-slide nodes — slide_router and deck_assembler. slide_router: saves…, Extract the <Theme .../> element from XML. (+31 more)

### Community 8 - "Frontend Slide Review"
Cohesion: 0.09
Nodes (26): EditHistoryEntry, AmountOfText, AppView, ComponentKind, DeckSettingsSchema, EditSessionStatus, ElicitationQuestion, ElicitResponse (+18 more)

### Community 9 - "Outline & Edit Service"
Cohesion: 0.10
Nodes (33): OutlinePlannerOutput, SlideEditResult, OutlineSlide, _make_elicitor_llm(), _make_gen_llm(), _make_outline_llm(), _make_plan_reviewer_llm(), _make_slide_component_llm() (+25 more)

### Community 10 - "Evaluator Pipeline"
Cohesion: 0.11
Nodes (38): _build_step_summary(), _compute_cost(), evaluator_node(), _generate_final_screenshots(), Any, PresentationState, Generate screenshots from the final assembled PPTX. Always (re)renders from…, Write run-manifest.json to output/runs/{run_id}/. (+30 more)

### Community 11 - "Layout Audit"
Cohesion: 0.10
Nodes (34): audit_layout(), Parse POM XML and check spatial/layout constraints. Returns a list of issue…, Tests for the layout audit — mechanical spatial checks on POM XML., Mixed-width table: specified cols under budget, auto-fill cols present., All-auto table: no widths specified, nothing to check., Icon inside Li is silently stripped by POM — audit must catch it., Valid inline tags inside Li should not trigger LI_INVALID_CHILD., HStack-root layout with a VStack column whose heights exceed 720. (+26 more)

### Community 12 - "Graph Routing"
Cohesion: 0.11
Nodes (32): compute_critic_score(), Deterministic score from critic output. Higher is better (max 0)., route_after_critic(), route_after_slide_router(), route_after_validator(), _slide_done_target(), _mock_visual_critic_pass(), _multi_slide_state() (+24 more)

### Community 13 - "Outline Planner Schema"
Cohesion: 0.10
Nodes (29): AzureChatOpenAI, ChatOpenAI, OutlinePlannerOutput, OutlineSlide, BaseModel, Pydantic models for the outline planner's structured output. The outline…, Rich outline entry for one slide — enough context for slide_component_planner., Complete deck outline from the outline planner. (+21 more)

### Community 14 - "Slide Edit Service"
Cohesion: 0.11
Nodes (21): _call_edit_llm(), _call_repair_llm(), Any, Path, Slide edit service — LLM-powered XML editing with mini repair loop. Takes user…, Fix compile errors with the shared tier-1 patch prompt. Reuses the main…, Run visual critic and attempt repairs for high-severity issues. Returns dict…, Attempt screenshot, retrying once on failure. Returns path or None. A failure… (+13 more)

### Community 15 - "Screenshot Backend"
Cohesion: 0.14
Nodes (26): Backend, _check_screenshot_backend(), _kill_new_powerpnt_processes(), _kill_pids(), _list_powerpnt_pids(), PPTX-to-PNG screenshot service. Uses PowerPoint COM automation via comtypes…, Render each slide in a PPTX to PNG via PowerPoint COM. Always returns a result…, Detect whether the PowerPoint COM backend is available. (+18 more)

### Community 16 - "Runner & Logging"
Cohesion: 0.12
Nodes (22): LogRecord, _format_table(), main(), Any, CLI runner — execute test cases and print a summary table. Usage: python -m…, Format results as an aligned ASCII table., Run test cases and return summary rows., run_cases() (+14 more)

### Community 17 - "XML Normalizer"
Cohesion: 0.14
Nodes (25): ensure_single_theme(), normalize_xml(), pre_validate(), Remove every <Theme> element (self-closing, multiline, or paired) from xml., Guarantee exactly one top-level <Theme>. Strips any <Theme> the LLM emitted…, Normalize raw LLM XML output: strip fences, fix colors, remove br/hr. Returns…, Full normalize + regex-based detection fallback for when parseXml is…, strip_theme() (+17 more)

### Community 18 - "Repairer Core"
Cohesion: 0.16
Nodes (22): build_patch_prompts(), _build_repair_context(), _call_llm_and_return(), _get_compile_diags(), _get_pre_issues(), _plan_to_outline_slide(), Any, Repairer agent — two repair strategies. PATCH: feed back failing XML + errors +… (+14 more)

### Community 19 - "Repair Guidance"
Cohesion: 0.15
Nodes (23): build_error_guidance(), cap_diag_msg(), error_signatures(), _extract_attr_from_error(), _extract_nodes_from_errors(), _extract_tag_from_error(), _find_node_attrs(), _format_attrs() (+15 more)

### Community 20 - "Layout Audit Checks"
Cohesion: 0.14
Nodes (22): Element, _check_band_height_sum(), _check_col_widths(), _check_font_sizes(), _check_hstack_column_heights(), _check_li_children(), _check_missing_dims(), _check_nesting() (+14 more)

### Community 21 - "Graph Construction"
Cohesion: 0.14
Nodes (21): build_graph(), _elicitation_wait_node(), fan_out_slide_plans(), placeholder_node(), Any, LangGraph pipeline definition. Hierarchical planning topology: START →…, If elicitation is needed and no answers yet, suspend; else proceed., Fan-out to one slide_component_planner per outline slide. (+13 more)

### Community 22 - "Pipeline State"
Cohesion: 0.17
Nodes (20): AttemptRecord, CompileResult, ComponentPlan, CriticResult, OutlinePlan, PlanReview, PresentationState — single source of truth for the LangGraph pipeline. Every…, ValidateResult (+12 more)

### Community 23 - "Case Loader"
Cohesion: 0.18
Nodes (20): case_to_state(), load_all_cases(), load_case(), Any, Path, YAML test case loader. Loads test case definitions from tests/cases/*.yaml and…, Load a single test case by name (without .yaml extension)., Load all YAML test cases from the cases directory. (+12 more)

### Community 24 - "Frontend App Shell"
Cohesion: 0.12
Nodes (11): AppComponent, Component, appConfig, ElicitationFormComponent, Component, LayoutComponent, Component, ProgressViewComponent (+3 more)

### Community 25 - "Validator"
Cohesion: 0.17
Nodes (18): RuntimeError, normalize_and_compile(), Any, Path, Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.…, Normalize + compile check. Returns (ok, compile_result). Used by the visual…, compile_xml(), CompilerError (+10 more)

### Community 26 - "Graph Routing Logic"
Cohesion: 0.14
Nodes (21): Send, Route after visual repair: re-critique if budget allows and repair produced new…, Route to planning pipeline, questionnaire, or skip directly to generation., route_after_start(), route_after_visual_repairer(), initial_state(), Any, Create a fully-initialized starting state for the graph. (+13 more)

### Community 27 - "Evaluator & Generator"
Cohesion: 0.14
Nodes (15): Evaluator agent — mechanical scoring and run manifest. No LLM. Computes: -…, Generator agent — produces POM XML from the plan + contract + data. Reads:…, _get_constraints(), outline_planner_node(), Any, Outline planner agent — produces the deck skeleton (replaces planner.py). Takes…, Parse DeckSettings dict → constraints dict for prompt injection., Plan the deck outline using an LLM with structured output. (+7 more)

### Community 28 - "Generator Inner"
Cohesion: 0.22
Nodes (20): _generator_inner(), generator_node(), Any, Render system + user prompts from the contract and slide plan., Generate POM XML via LLM using tiered prompts from the contract., _render_prompts(), _make_state(), patch (+12 more)

### Community 29 - "Frontend Plan Editor"
Cohesion: 0.13
Nodes (4): emptyOutlineSlide(), PlanEditorComponent, Component, OutlineSlide

### Community 30 - "Component Concepts"
Cohesion: 0.12
Nodes (19): Complexity Spectrum Testing, Weight Hierarchy Design Pattern, KPI Row Test Case, Matrix Prioritization Test Case, Maximal Density Test Case, Minimal Statement Test Case, Mixed Chart-Matrix Test Case, Mixed Executive Slide Test Case (+11 more)

### Community 31 - "Style Resolver"
Cohesion: 0.20
Nodes (16): _load_yaml(), Any, Style resolver — loosely-coupled theme resolution. Public API:…, Resolve a theme name to a full theme dict. Returns: {name, mode, is_dark,…, LangGraph node: resolve theme and write to state., resolve_theme(), style_resolver_node(), Tests for the style resolver — theme resolution utility and graph node. (+8 more)

### Community 32 - "Compile Graph"
Cohesion: 0.18
Nodes (18): compile_graph(), Return a compiled, runnable graph., _mock_screenshot_batch(), patch, End-to-end: the graph runs to completion with mocked LLM + compiler., End-to-end: graph runs with pre-provided slide_plans (skips planning phase)., Multi-slide: 2 pre-loaded slides, both compile, deck assembles., 8-slide deck completes without hitting the recursion limit. (+10 more)

### Community 33 - "Angular CLI Deps"
Cohesion: 0.12
Nodes (17): @angular/cli, @angular/compiler-cli, @angular-devkit/build-angular, autoprefixer, devDependencies, @angular/cli, @angular/compiler-cli, @angular-devkit/build-angular (+9 more)

### Community 34 - "Angular Core Deps"
Cohesion: 0.12
Nodes (17): @angular/common, @angular/compiler, @angular/core, @angular/forms, @angular/platform-browser, @angular/router, dependencies, @angular/common (+9 more)

### Community 35 - "Angular Schematics"
Cohesion: 0.12
Nodes (17): schematics, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests (+9 more)

### Community 36 - "Frontend API Models"
Cohesion: 0.19
Nodes (4): GenerateRequest, ProgressEvent, GenerationService, Injectable

### Community 37 - "Questionnaire Agent"
Cohesion: 0.17
Nodes (16): _ask(), _load_palette_names(), Any, questionnaire_node(), Collect audience context via interactive CLI questions., Return [(name, tone), ...] from palettes.yaml, light first then dark., Print numbered menu and collect user choice. Returns the selected option., Map the slide-count answer to a planner target slide count. (+8 more)

### Community 38 - "Elicitor Agent"
Cohesion: 0.19
Nodes (13): ElicitorOutput, check_and_elicit(), _elicitor_inner(), elicitor_node(), Any, PresentationState, Elicitor agent — detects vague queries and generates clarifying questions.…, Check if context is sufficient and return clarifying questions if not. Pure LLM… (+5 more)

### Community 39 - "Deck Settings Form"
Cohesion: 0.19
Nodes (5): DeckSettingsFormComponent, Component, DeckSettings, DeckSettingsField, DeckSettingsFieldOption

### Community 40 - "Angular Build Options"
Cohesion: 0.19
Nodes (14): options, assets, browser, index, outputPath, polyfills, scripts, styles (+6 more)

### Community 41 - "Frontend Progress & Prompt"
Cohesion: 0.19
Nodes (9): PromptFormComponent, PIPELINE_PHASES, PipelinePhase, PROGRESS_RANGES, SLIDE_COUNT_TO_THRESHOLD, STEP_LABELS, THEME_PALETTES, CriticMode (+1 more)

### Community 42 - "Context Builder Core"
Cohesion: 0.23
Nodes (12): _build_default_plan(), Context builder agent — assembles knowledge base into a generation contract.…, Build a SlidePlan from test_case components, intent detection, or fallback., _merge_content_data(), Any, Slide replanner — decides whether an edit needs a richer SlidePlan. Feedback on…, Keep original values for existing keys; only take new keys from the replan. The…, Convert an existing SlidePlan to a minimal OutlineSlide for re-planning.… (+4 more)

### Community 43 - "Knowledge Components"
Cohesion: 0.15
Nodes (13): Tree Component (POM), POM Document Structure, Chart-on-Dark Workaround, Theme Palette Library, compile-pom.js (POM Compiler Wrapper), @hirokisakabe/pom v10.3.0 (External Dependency), presentation-mvp-compiler (npm package), Test Case: Competitor Comparison (+5 more)

### Community 44 - "Node Package Deps"
Cohesion: 0.17
Nodes (11): @hirokisakabe/pom, dependencies, @hirokisakabe/pom, description, main, name, private, scripts (+3 more)

### Community 45 - "Validator Node"
Cohesion: 0.26
Nodes (12): PresentationState, Run the normalize → validate → compile pipeline on current_xml., validator_node(), patch, test_validator_compile_error_not_retryable(), test_validator_empty_xml(), test_validator_empty_xml_has_layout_issues_key(), test_validator_falls_back_to_pre_validate() (+4 more)

### Community 46 - "Deck Test Cases"
Cohesion: 0.22
Nodes (11): Family B — Deck Tests, Supplied Data Test Pattern, Deck Board Update Test Case, Deck Minimal 2-Slide Test Case, Deck Product Launch Data Test Case, Deck Product Launch Test Case, Deck QBR Data Test Case, Deck QBR Test Case (+3 more)

### Community 47 - "Angular Serve Config"
Cohesion: 0.18
Nodes (11): serve, development, buildTarget, extractLicenses, optimization, sourceMap, proxyConfig, builder (+3 more)

### Community 48 - "Normalizer Fixes"
Cohesion: 0.20
Nodes (10): Match, _fix_pyramid_block(), _fix_pyramids(), _perceived_brightness(), Any, XML normalizer — strip fences, fix colors, remove br/hr, zero spacing. Returns…, Fix fontSize and textColor inside a single <Pyramid>...</Pyramid> block., Find all Pyramid blocks and fix fontSize + textColor. (+2 more)

### Community 49 - "Critic Inner"
Cohesion: 0.29
Nodes (9): _constrain_round2_strategy(), _critic_inner(), Any, Critic agent — visual quality gate after successful compilation. The visual…, Force patch-only on round 2 — no double-regenerate., Take screenshot and run visual critic. Returns (issues, screenshot_path, usage,…, _run_visual_review(), Pre-generation questionnaire — collects audience/style/focus context. Presents… (+1 more)

### Community 50 - "Slide Component Planner"
Cohesion: 0.29
Nodes (10): _filter_supplied_content_for_slide(), plan_single_slide(), Any, Slide component planner — plans ONE slide in detail (fan-out target). Called…, Return subset of supplied_content relevant to this slide's key_messages., Plan one slide and return a SlidePlan TypedDict. Can be called directly (e.g.…, Plan all slides sequentially in a single node (SERIALIZE_SLIDES=True path)., Plan ONE slide (receives specific slide via Send() state injection). The… (+2 more)

### Community 51 - "Slide Replanner Tests"
Cohesion: 0.33
Nodes (9): patch, Tests for the slide replanner's two-tier gate., Feedback that only mentions kinds already on the slide never triggers a replan., _slide_plan(), test_resolve_slide_plan_empty_theme_info_returns_empty_contract(), test_tier0_no_new_kind_skips_replan(), test_tier0_removal_feedback_skips_replan(), test_tier2_new_kind_triggers_replan() (+1 more)

### Community 52 - "Angular Project Config"
Cohesion: 0.20
Nodes (9): prefix, projectType, root, sourceRoot, newProjectRoot, projects, frontend, $schema (+1 more)

### Community 53 - "Frontend Package"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, ng, start, test, watch (+1 more)

### Community 54 - "Phase Test Cases"
Cohesion: 0.32
Nodes (8): Phase-Based Test System, Chart and Narrative Test Case, Chart and Table Test Case, Comparison Matrix Test Case, Dark Theme Test Case, Financial Report Test Case, Flowchart Test Case, Inline Formatting Test Case

### Community 55 - "Angular Build Config"
Cohesion: 0.25
Nodes (8): build, builder, configurations, defaultConfiguration, production, budgets, buildTarget, outputHashing

### Community 56 - "LI Nesting Scripts"
Cohesion: 0.48
Nodes (6): _compile(), _count_icons_in_pptx(), main(), Path, Verify that LI_INVALID_CHILD audit catches silently-stripped block elements.…, Count icon/image references in the PPTX slide XML.

### Community 58 - "Base Test Cases"
Cohesion: 0.33
Nodes (6): Family A — Base Prompt Tests, Base Revenue Trend Test Case, Base Risks Test Case, Base Roadmap Test Case, Base Strategy Statement Test Case, Base Vague Test Case

### Community 59 - "POM Compiler"
Cohesion: 0.53
Nodes (5): classifyError(), compile(), printSummary(), SLIDE_SIZE, validate()

### Community 60 - "Angular i18n & Test"
Cohesion: 0.40
Nodes (5): extract-i18n, test, builder, architect, builder

### Community 61 - "Render Check Script"
Cohesion: 0.60
Nodes (4): _compile(), main(), Path, Render + audit a folder of POM XML files — the offline quality feedback loop.…

### Community 62 - "Card Recipes"
Cohesion: 0.50
Nodes (4): Card Recipe, Accent Card Recipe, Surface Card Recipe, Callout Recipe

### Community 63 - "Typography & Hierarchy"
Cohesion: 0.50
Nodes (4): Visual Hierarchy, Micro Pair Recipe, Type Ramp, KPI Row Recipe

### Community 65 - "Spacing & Composition"
Cohesion: 0.67
Nodes (3): Spacing Scale, Composition Grammar, Sizing Vocabulary

## Knowledge Gaps
- **157 isolated node(s):** `PipelinePhase`, `EditHistoryEntry`, `AmountOfText`, `ComponentKind`, `PlanReviewIssue` (+152 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 560 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `initial_state()` connect `Graph Routing Logic` to `API & HTTP Layer`, `Context Builder`, `Compile Graph`, `Plan Reviewer`, `Slide Repairer`, `Questionnaire Agent`, `Visual Critic`, `Evaluator Pipeline`, `Graph Routing`, `Validator Node`, `Critic Inner`, `XML Normalizer`, `Graph Construction`, `Pipeline State`, `Case Loader`, `Generator Inner`, `Style Resolver`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `audit_layout()` connect `Layout Audit` to `Validator Node`, `Layout Audit Col Width`, `Layout Audit Dims`, `Layout Audit Checks`, `LI Nesting Scripts`, `Validator`, `Render Check Script`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `PresentationState` connect `Critic Inner` to `Context Builder`, `Slide Repairer`, `Questionnaire Agent`, `Visual Critic`, `Deck Assembly`, `Context Builder Core`, `Graph Routing`, `Repairer Core`, `Slide Component Planner`, `Graph Construction`, `Pipeline State`, `Case Loader`, `Graph Routing Logic`, `Evaluator & Generator`, `Generator Inner`, `Style Resolver`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `PresentationState` (e.g. with `_build_default_plan()` and `context_builder_node()`) actually correct?**
  _`PresentationState` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `build_graph()` (e.g. with `context_builder_node()` and `critic_node()`) actually correct?**
  _`build_graph()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `critic_node()` (e.g. with `PresentationState` and `build_graph()`) actually correct?**
  _`critic_node()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `PipelinePhase`, `EditHistoryEntry`, `AmountOfText` to the rest of the system?**
  _157 weakly-connected nodes found - possible documentation gaps or missing edges._