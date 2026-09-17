# Graph Report - presentation-pipeline  (2026-09-17)

## Corpus Check
- 105 files · ~106,979 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1361 nodes · 2959 edges · 88 communities (66 shown, 14 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 145 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `253c2edf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- state.py
- test_repairer.py
- api.py
- get_llm
- audit_layout
- test_api.py
- load_case
- test_planner.py
- test_evaluator.py
- api.models.ts
- test_graph.py
- test_critic.py
- edit_slide_xml
- House Style Layout Grammar
- DeckSettingsFormComponent
- test_deck_nodes.py
- PresentationState
- slide_component_planner.py
- PlanEditorComponent
- _detect_components_from_text
- test_generator.py
- resolve_slide_plan
- dependencies
- Mixed Executive Slide Test Case
- initial_state
- test_validator.py
- test_context_builder.py
- slide_edit_service.py
- resolve_theme
- devDependencies
- schematics
- app.component.ts
- build_contract
- GenerationService
- context_builder.py
- test_full_pipeline.py
- LangGraph Presentation Pipeline
- options
- node/package.json
- validator_node
- Line-by-Line Code and State Flow
- Family B — Deck Tests
- development
- slide-review.component.ts
- frontend
- frontend/package.json
- theme.constants.ts
- Repairer Node (LLM)
- Validator Node (Mechanical)
- YAML Knowledge Base
- Phase-Based Test System
- build
- Generator Node (LLM)
- Family A — Base Prompt Tests
- OutlineSlide
- compile-pom.js
- screenshot-pom.js
- LLM Test Plan (Planner & Generator)
- architect
- @angular/compiler-cli
- Golden Fixture Regression Testing
- jasmine-core
- karma
- karma-coverage
- karma-jasmine
- postcss
- conftest.py
- Test Case Phase System
- State Re-Entry Points
- presentation-pipeline
- Pitch Deck Test Case
- Pyramid Strategy Test Case
- Tree Org Chart Test Case
- route_after_start
- plan_reviewer_node
- Group Composition (`66dc5e9`) — Post-Mortem
- compute_provenance
- plan_single_slide
- _render_house_style
- _mock_outline_output

## God Nodes (most connected - your core abstractions)
1. `initial_state()` - 90 edges
2. `PresentationState` - 59 edges
3. `repairer_node()` - 35 edges
4. `audit_layout()` - 33 edges
5. `build_graph()` - 32 edges
6. `evaluator_node()` - 28 edges
7. `get_llm()` - 27 edges
8. `normalize_xml()` - 24 edges
9. `build_contract()` - 23 edges
10. `validator_node()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `POM Pipeline Architecture Overview` --semantically_similar_to--> `LangGraph Presentation Pipeline`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `test_pipeline_with_hierarchical_planner()` --uses--> `ElicitorOutput`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/elicitor_schema.py
- `test_pipeline_with_hierarchical_planner()` --uses--> `OutlineSlide`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/outline_planner_schema.py
- `test_refine_plan_passes_feedback_to_planner()` --uses--> `OutlineSlide`  [INFERRED]
  tests/unit/test_api.py → src/agents/outline_planner_schema.py
- `test_refine_plan_returns_revised_plan()` --uses--> `OutlineSlide`  [INFERRED]
  tests/unit/test_api.py → src/agents/outline_planner_schema.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **POM Knowledge Core (Document + Nodes + Attributes + Validation)** — src_knowledge_core_document_document_structure, src_knowledge_core_nodes_node_allowlist, src_knowledge_core_attributes_common_attributes, src_knowledge_core_validation_validation_rules [EXTRACTED 0.95]
- **Deck Mode Multi-Slide Processing Loop** — code_flow_slide_router_node, code_flow_deck_assembler_node, architecture_context_builder_node, architecture_generator_node, architecture_validator_node [EXTRACTED 1.00]
- **Component Knowledge Base Specifications** — architecture_knowledge_base, src_knowledge_components_chart, src_knowledge_components_drawing, src_knowledge_components_flow, src_knowledge_components_list, src_knowledge_components_matrix, src_knowledge_components_process_arrow, src_knowledge_components_pyramid, src_knowledge_components_shape [EXTRACTED 1.00]
- **LLM Test Family A Base-Prompt Cases** — tests_llm_test_plan_test_plan, tests_cases_base_competitor_comparison_test_case, tests_cases_base_org_structure_test_case, tests_cases_base_overstuffed_test_case, tests_cases_base_process_overview_test_case, tests_cases_base_quarterly_metrics_test_case [EXTRACTED 1.00]
- **Core Pipeline Flow (Plan-Generate-Validate-Repair-Evaluate)** — architecture_planner_node, architecture_context_builder_node, architecture_generator_node, architecture_validator_node, architecture_critic_node, architecture_repairer_node, architecture_evaluator_node [EXTRACTED 1.00]
- **** — tests_cases_base_revenue_trend_yaml, tests_cases_base_risks_yaml, tests_cases_base_roadmap_yaml, tests_cases_base_strategy_statement_yaml, tests_cases_base_vague_yaml [EXTRACTED 1.00]
- **** — tests_cases_chart_and_narrative_yaml, tests_cases_chart_and_table_yaml, tests_cases_comparison_matrix_yaml, tests_cases_dark_theme_yaml, tests_cases_financial_report_yaml, tests_cases_flowchart_yaml, tests_cases_inline_formatting_yaml [EXTRACTED 1.00]
- **Slide Layout Composition (House Style + Design Language + Recipes)** — src_knowledge_core_house_style_house_style_grammar, src_knowledge_core_design_language_design_language, src_knowledge_core_recipes_compiled_recipes, src_knowledge_theme_palettes_palette_library [INFERRED 0.85]
- **** — tests_cases_deck_qbr_yaml, tests_cases_deck_qbr_data_yaml, tests_cases_deck_board_update_yaml, tests_cases_deck_sales_enablement_yaml, tests_cases_deck_sales_data_yaml [INFERRED 0.85]

## Communities (88 total, 14 thin omitted)

### Community 0 - "state.py"
Cohesion: 0.16
Nodes (23): AttemptRecord, CompileResult, ComponentPlan, CriticResult, DeckPlan, OutlinePlan, OutlineSlide, PlanReview (+15 more)

### Community 1 - "test_repairer.py"
Cohesion: 0.06
Nodes (85): _call_deck_repair_llm(), Deck multi-slide nodes — slide_router and deck_assembler. slide_router: saves…, Fix compile errors in the assembled multi-slide document, preserving all…, build_patch_prompts(), _choose_strategy(), _collect_problems(), _get_compile_diags(), _get_pre_issues() (+77 more)

### Community 2 - "api.py"
Cohesion: 0.06
Nodes (70): Enum, FileResponse, get, post, put, _build_event(), _cleanup_old_runs(), ComponentPlanPayload (+62 more)

### Community 3 - "get_llm"
Cohesion: 0.13
Nodes (21): AzureChatOpenAI, ChatOpenAI, check_and_elicit(), elicitor_node(), Any, Elicitor agent — detects vague queries and generates clarifying questions.…, Check if context is sufficient and return clarifying questions if not. Pure LLM…, Graph node: run elicitor and write results to state. If elicitation_answers are… (+13 more)

### Community 4 - "audit_layout"
Cohesion: 0.08
Nodes (46): Element, _compile(), _find_soffice(), main(), Path, Render + audit a folder of POM XML files — the offline quality feedback loop.…, _to_pdf(), audit_layout() (+38 more)

### Community 5 - "test_api.py"
Cohesion: 0.12
Nodes (32): RuntimeError, SlideEditResult, _load_edit_session(), Load edit session from slides.json on disk., _make_critic_llm(), _make_elicitor_llm(), _make_gen_llm(), _make_outline_llm() (+24 more)

### Community 6 - "load_case"
Cohesion: 0.08
Nodes (42): LogRecord, _format_table(), main(), Any, CLI runner — execute test cases and print a summary table. Usage: python -m…, Format results as an aligned ASCII table., Run test cases and return summary rows., run_cases() (+34 more)

### Community 7 - "test_planner.py"
Cohesion: 0.24
Nodes (20): PlannerComponent, PlannerSlide, BaseModel, Pydantic models for the per-slide planner's structured LLM output. PlannerSlide…, Plan for a single slide., One component the slide should contain, with its own content data., _planner_slide_to_state(), Convert PlannerSlide Pydantic model to SlidePlan TypedDict. (+12 more)

### Community 8 - "test_evaluator.py"
Cohesion: 0.10
Nodes (40): _build_step_summary(), _compute_cost(), evaluator_node(), _generate_final_screenshots(), Any, Evaluator agent — mechanical scoring and run manifest. No LLM. Computes: -…, Generate screenshots from the final assembled PPTX. Always (re)renders from…, Write run-manifest.json to output/runs/{run_id}/. (+32 more)

### Community 9 - "api.models.ts"
Cohesion: 0.10
Nodes (23): AmountOfText, AppView, ComponentKind, DeckSettingsSchema, EditSessionStatus, ElicitationQuestion, EvaluationSummary, EventType (+15 more)

### Community 10 - "test_graph.py"
Cohesion: 0.16
Nodes (24): route_after_critic(), route_after_slide_router(), route_after_validator(), _slide_done_target(), _multi_slide_state(), Tests for the LangGraph pipeline with stub agents., Create a state with 2 slide_plans (multi-slide mode)., test_graph_builds() (+16 more)

### Community 11 - "test_critic.py"
Cohesion: 0.06
Nodes (70): Backend, critic_node(), Any, Critic agent — visual quality gate after successful compilation. The visual…, Take screenshot and run visual critic. Returns (issues, screenshot_path, usage,…, Visual quality gate — screenshot-based review using a vision LLM., _run_visual_review(), CriticIssue (+62 more)

### Community 12 - "edit_slide_xml"
Cohesion: 0.11
Nodes (22): _call_edit_llm(), _call_repair_llm(), edit_slide_xml(), Any, Path, Fix compile errors with the shared tier-1 patch prompt. Reuses the main…, Apply a user's NL edit to a slide XML, validate, and repair if needed. Returns…, Run visual critic and attempt repairs for high-severity issues. Returns dict… (+14 more)

### Community 13 - "House Style Layout Grammar"
Cohesion: 0.16
Nodes (14): Text Component (POM), Common Box/Layout Attributes, Design Language Patterns, POM Document Structure, Group Rendering Rules, Height Budget System, House Style Layout Grammar, Weight Allocation System (+6 more)

### Community 14 - "DeckSettingsFormComponent"
Cohesion: 0.11
Nodes (11): DeckSettingsFormComponent, Component, PromptFormComponent, Component, SLIDE_COUNT_TO_THRESHOLD, THEME_PALETTES, CriticMode, DeckSettings (+3 more)

### Community 15 - "test_deck_nodes.py"
Cohesion: 0.11
Nodes (32): assemble_deck_xml(), deck_assembler_node(), _extract_slide_block(), _extract_theme(), Any, Extract the <Theme .../> element from XML., Extract the <Slide>...</Slide> block from XML., Combine all completed slide XMLs into one multi-slide POM document and compile. (+24 more)

### Community 16 - "PresentationState"
Cohesion: 0.14
Nodes (23): Pre-generation questionnaire — collects audience/style/focus context. Presents…, Plan all slides sequentially in a single node (SERIALIZE_SLIDES=True path)., slide_plan_serial_node(), Style resolver — loosely-coupled theme resolution. Public API:…, LangGraph node: resolve theme and write to state., style_resolver_node(), build_graph(), _elicitation_wait_node() (+15 more)

### Community 17 - "slide_component_planner.py"
Cohesion: 0.18
Nodes (16): _get_constraints(), outline_planner_node(), Any, Outline planner agent — produces the deck skeleton (replaces planner.py). Takes…, Parse DeckSettings dict → constraints dict for prompt injection., Plan the deck outline using an LLM with structured output., DeckSettings, BaseModel (+8 more)

### Community 18 - "PlanEditorComponent"
Cohesion: 0.13
Nodes (4): emptyOutlineSlide(), PlanEditorComponent, Component, OutlineSlide

### Community 19 - "_detect_components_from_text"
Cohesion: 0.29
Nodes (7): _detect_components_from_text(), Extract component kinds by scanning text for keywords., test_detect_components_chart(), test_detect_components_multiple(), test_detect_components_no_match(), test_detect_components_table_and_kpi(), test_detect_components_timeline()

### Community 20 - "test_generator.py"
Cohesion: 0.21
Nodes (20): generator_node(), Any, Generator agent — produces POM XML from the plan + contract + data. Uses tiered…, Render system + user prompts from the contract and slide plan., Generate POM XML via LLM using tiered prompts from the contract., _render_prompts(), _make_state(), patch (+12 more)

### Community 21 - "resolve_slide_plan"
Cohesion: 0.20
Nodes (18): _merge_content_data(), Any, Slide replanner — decides whether an edit needs a richer SlidePlan. Feedback on…, Keep original values for existing keys; only take new keys from the replan. The…, Convert an existing SlidePlan to a minimal OutlineSlide for re-planning.…, Return (possibly-updated slide_plan, generation contract) for an edit. Degrades…, resolve_slide_plan(), _slide_plan_to_outline_slide() (+10 more)

### Community 22 - "dependencies"
Cohesion: 0.11
Nodes (19): @angular/common, @angular/compiler, @angular/core, @angular/forms, @angular/platform-browser, @angular/router, dependencies, @angular/common (+11 more)

### Community 23 - "Mixed Executive Slide Test Case"
Cohesion: 0.12
Nodes (19): Complexity Spectrum Testing, Weight Hierarchy Design Pattern, KPI Row Test Case, Matrix Prioritization Test Case, Maximal Density Test Case, Minimal Statement Test Case, Mixed Chart-Matrix Test Case, Mixed Executive Slide Test Case (+11 more)

### Community 24 - "initial_state"
Cohesion: 0.14
Nodes (21): _ask(), _load_palette_names(), Any, questionnaire_node(), Collect audience context via interactive CLI questions., Return [(name, tone), ...] from palettes.yaml, light first then dark., Print numbered menu and collect user choice. Returns the selected option., Map the slide-count answer to a planner target slide count. (+13 more)

### Community 25 - "test_validator.py"
Cohesion: 0.12
Nodes (28): ensure_single_theme(), normalize_xml(), pre_validate(), Any, XML normalizer — strip fences, fix colors, remove br/hr, zero spacing. Returns…, Normalize raw LLM XML output: strip fences, fix colors, remove br/hr. Returns…, Full normalize + regex-based detection fallback for when parseXml is…, Remove every <Theme> element (self-closing, multiline, or paired) from xml. (+20 more)

### Community 26 - "test_context_builder.py"
Cohesion: 0.13
Nodes (30): _load_yaml(), Select POM nodes needed for the given component kinds., Build per-node attribute lists for only the nodes we selected., Select only notes relevant to the components in this slide. When has_grammar is…, _select_attributes(), _select_nodes(), _select_notes(), Tests for the context builder agent. (+22 more)

### Community 27 - "slide_edit_service.py"
Cohesion: 0.20
Nodes (14): Slide edit service — LLM-powered XML editing with mini repair loop. Takes user…, Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.…, compile_xml(), CompilerError, _parse_result(), Any, Path, Subprocess bridge to compile-pom.js (src/node/). The Node script writes… (+6 more)

### Community 28 - "resolve_theme"
Cohesion: 0.26
Nodes (12): _load_yaml(), Any, Resolve a theme name to a full theme dict. Returns: {name, mode, is_dark,…, resolve_theme(), Tests for the style resolver — theme resolution utility and graph node., test_resolve_chart_colors(), test_resolve_corporate_slate_explicit(), test_resolve_default_theme() (+4 more)

### Community 29 - "devDependencies"
Cohesion: 0.12
Nodes (17): @angular/cli, @angular-devkit/build-angular, autoprefixer, devDependencies, @angular/cli, @angular-devkit/build-angular, autoprefixer, karma-chrome-launcher (+9 more)

### Community 30 - "schematics"
Cohesion: 0.12
Nodes (17): schematics, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests (+9 more)

### Community 31 - "app.component.ts"
Cohesion: 0.15
Nodes (9): AppComponent, Component, appConfig, ElicitationFormComponent, Component, LayoutComponent, Component, ResultViewComponent (+1 more)

### Community 32 - "build_contract"
Cohesion: 0.23
Nodes (16): build_contract(), _clean_list(), Any, Build a generation contract for one slide from its plan. Args: slide_plan: The…, _estimate_tokens(), _make_plan(), Rough token estimate: ~4 chars per token for English., Maximal-density (6 components): grammar + recipes + shrink checklist. (+8 more)

### Community 33 - "GenerationService"
Cohesion: 0.22
Nodes (3): ProgressEvent, GenerationService, Injectable

### Community 34 - "context_builder.py"
Cohesion: 0.13
Nodes (16): _all_recipes(), _build_default_plan(), _build_node_attributes(), _build_node_hierarchy(), context_builder_node(), Context builder agent — assembles knowledge base into a generation contract.…, Render a compact parent -> children map for the nodes on this slide. Extracts…, node name -> node-specific attributes from nodes.yaml. (+8 more)

### Community 35 - "test_full_pipeline.py"
Cohesion: 0.11
Nodes (30): parametrize, CriticOutput, Complete critic review output., _run_pipeline_sync(), compile_graph(), Return a compiled, runnable graph., _make_critic_llm(), _make_gen_llm() (+22 more)

### Community 36 - "LangGraph Presentation Pipeline"
Cohesion: 0.17
Nodes (13): LangGraph Presentation Pipeline, POM XML Markup Language, PresentationState TypedDict, Generate-Validate-Repair Retry Loop, DeckState Extended State Model, Loosely Coupled Editing Architecture, XML as Source of Truth, POM Pipeline Architecture Overview (+5 more)

### Community 37 - "options"
Cohesion: 0.21
Nodes (13): options, assets, browser, index, outputPath, polyfills, scripts, styles (+5 more)

### Community 38 - "node/package.json"
Cohesion: 0.17
Nodes (11): @hirokisakabe/pom, dependencies, @hirokisakabe/pom, description, main, name, private, scripts (+3 more)

### Community 39 - "validator_node"
Cohesion: 0.26
Nodes (12): Any, Run the normalize → validate → compile pipeline on current_xml., validator_node(), patch, test_validator_compile_error_not_retryable(), test_validator_empty_xml(), test_validator_empty_xml_has_layout_issues_key(), test_validator_falls_back_to_pre_validate() (+4 more)

### Community 40 - "Line-by-Line Code and State Flow"
Cohesion: 0.22
Nodes (10): Evaluator Node (Mechanical), API Path (FastAPI + SSE), Deck Assembler Node, Questionnaire Node, Slide Router Node (Deck Mode), Line-by-Line Code and State Flow, Style Resolver Node, Deck Mode Critic Accounting Bug (+2 more)

### Community 41 - "Family B — Deck Tests"
Cohesion: 0.22
Nodes (11): Family B — Deck Tests, Supplied Data Test Pattern, Deck Board Update Test Case, Deck Minimal 2-Slide Test Case, Deck Product Launch Data Test Case, Deck Product Launch Test Case, Deck QBR Data Test Case, Deck QBR Test Case (+3 more)

### Community 42 - "development"
Cohesion: 0.18
Nodes (11): serve, development, buildTarget, extractLicenses, optimization, sourceMap, proxyConfig, builder (+3 more)

### Community 43 - "slide-review.component.ts"
Cohesion: 0.18
Nodes (5): EditHistoryEntry, SlideReviewComponent, Component, SlideEditResponse, SlideInfoReview

### Community 44 - "frontend"
Cohesion: 0.20
Nodes (9): prefix, projectType, root, sourceRoot, newProjectRoot, projects, frontend, $schema (+1 more)

### Community 45 - "frontend/package.json"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, ng, start, test, watch (+1 more)

### Community 46 - "theme.constants.ts"
Cohesion: 0.22
Nodes (7): ProgressViewComponent, Component, PIPELINE_PHASES, PipelinePhase, PROGRESS_RANGES, STEP_LABELS, ThemePalette

### Community 47 - "Repairer Node (LLM)"
Cohesion: 0.25
Nodes (9): Critic Node (LLM), Repair Guidance System, Repairer Node (LLM), Stall Detection Mechanism, Fail-Open Critic Risk, GPT-4.1 Model, Hierarchical Planning Pipeline Steps, LLM Model Configuration (+1 more)

### Community 48 - "Validator Node (Mechanical)"
Cohesion: 0.25
Nodes (8): Node.js Compiler Bridge, POM Compiler v10.3.0 (@hirokisakabe/pom), Validator Node (Mechanical), XML Normalizer, Speaker Notes Lost in Pipeline, Layout Audit Post-Generation, Chart Component Spec, Dark Theme Chart Axis Bug Workaround

### Community 49 - "YAML Knowledge Base"
Cohesion: 0.32
Nodes (8): YAML Knowledge Base, Drawing Component Spec (Layer/Line/Arrow/Svg), Flow Component Spec (Flowchart), List Component Spec (Ul/Ol/Li), Matrix Component Spec (2x2 Grid), ProcessArrow Component Spec, Pyramid Component Spec, Shape Component Spec

### Community 50 - "Phase-Based Test System"
Cohesion: 0.32
Nodes (8): Phase-Based Test System, Chart and Narrative Test Case, Chart and Table Test Case, Comparison Matrix Test Case, Dark Theme Test Case, Financial Report Test Case, Flowchart Test Case, Inline Formatting Test Case

### Community 51 - "build"
Cohesion: 0.25
Nodes (8): build, builder, configurations, defaultConfiguration, production, budgets, buildTarget, outputHashing

### Community 52 - "Generator Node (LLM)"
Cohesion: 0.20
Nodes (11): Context Builder Node, Generation Contract, Generator Node (LLM), Planner Node (LLM), Tiered Prompt Assembly, Layout Variety Enforcement Discarded, PipelineTool Base Class, 14-Kind Component Vocabulary (+3 more)

### Community 53 - "Family A — Base Prompt Tests"
Cohesion: 0.33
Nodes (6): Family A — Base Prompt Tests, Base Revenue Trend Test Case, Base Risks Test Case, Base Roadmap Test Case, Base Strategy Statement Test Case, Base Vague Test Case

### Community 54 - "OutlineSlide"
Cohesion: 0.20
Nodes (15): OutlinePlannerOutput, OutlineSlide, BaseModel, Pydantic models for the outline planner's structured output. The outline…, Rich outline entry for one slide — enough context for slide_component_planner., Complete deck outline from the outline planner., Any, Outline replanner — regenerates a single outline slide from user feedback. Pre-… (+7 more)

### Community 55 - "compile-pom.js"
Cohesion: 0.53
Nodes (5): classifyError(), compile(), printSummary(), SLIDE_SIZE, validate()

### Community 56 - "screenshot-pom.js"
Cohesion: 0.60
Nodes (5): findExecutable(), findImageMagick(), findSoffice(), isRealImageMagick(), main()

### Community 57 - "LLM Test Plan (Planner & Generator)"
Cohesion: 0.19
Nodes (13): Pipeline Critical Review, Table Component (POM), Timeline Component (POM), Tree Component (POM), POM Node Allowlist (Phase Registry), POM Validation Rules & Forbidden Tags, Test Case: Architecture Diagram (Phase D), Test Case: Competitor Comparison (+5 more)

### Community 58 - "architect"
Cohesion: 0.40
Nodes (5): extract-i18n, test, builder, architect, builder

### Community 81 - "route_after_start"
Cohesion: 0.18
Nodes (12): Send, fan_out_slide_plans(), Fan-out to one slide_component_planner per outline slide., Route to planning pipeline, questionnaire, or skip directly to generation., route_after_start(), A user-edited outline (e.g. via PUT /plan/{run_id}/outline) skips elicitor +…, test_route_after_start_interactive_questionnaire(), test_route_after_start_preloaded_outline_fans_out() (+4 more)

### Community 82 - "plan_reviewer_node"
Cohesion: 0.27
Nodes (8): plan_reviewer_node(), Any, Plan reviewer agent — evaluates assembled deck plan quality. Runs after all…, Review the assembled slide plans and emit a confidence score., PlanReviewerOutput, PlanReviewIssue, BaseModel, Pydantic models for the plan reviewer agent's structured output.

### Community 83 - "Group Composition (`66dc5e9`) — Post-Mortem"
Cohesion: 0.25
Nodes (7): 1. Prompt dilution, 2. The outline planner rewording backfired, 3. No few-shot examples, Group Composition (`66dc5e9`) — Post-Mortem, Lessons for future attempts, What was added, What went wrong

### Community 84 - "compute_provenance"
Cohesion: 0.29
Nodes (7): compute_provenance(), Any, Tag each content_data key as 'user' (from supplied_content) or 'sample'., test_compute_provenance_all_sample(), test_compute_provenance_all_user(), test_compute_provenance_empty_content(), test_compute_provenance_mixed()

### Community 85 - "plan_single_slide"
Cohesion: 0.38
Nodes (7): _filter_supplied_content_for_slide(), plan_single_slide(), Any, Return subset of supplied_content relevant to this slide's key_messages., Plan one slide and return a SlidePlan TypedDict. Can be called directly (e.g.…, Plan ONE slide (receives specific slide via Send() state injection). The…, slide_component_planner_node()

### Community 86 - "_render_house_style"
Cohesion: 0.33
Nodes (6): _fmt_house_style_value(), Render one house-style.yaml value (str / list / dict) as prompt text., Render core/house-style.yaml into a compact prompt block (cached)., _render_house_style(), test_render_house_style_has_core_sections(), test_render_house_style_is_not_a_slide()

### Community 87 - "_mock_outline_output"
Cohesion: 0.60
Nodes (6): _make_structured_llm(), _mock_outline_output(), patch, test_outline_planner_multi_slide(), test_outline_planner_single_slide(), test_outline_planner_with_deck_settings()

## Knowledge Gaps
- **138 isolated node(s):** `$schema`, `version`, `newProjectRoot`, `projectType`, `skipTests` (+133 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 454 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `initial_state()` connect `initial_state` to `state.py`, `test_repairer.py`, `api.py`, `load_case`, `test_planner.py`, `test_evaluator.py`, `test_graph.py`, `test_critic.py`, `test_deck_nodes.py`, `PresentationState`, `slide_component_planner.py`, `test_generator.py`, `test_validator.py`, `test_context_builder.py`, `resolve_theme`, `context_builder.py`, `test_full_pipeline.py`, `validator_node`, `route_after_start`, `_mock_outline_output`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `PresentationState` connect `PresentationState` to `state.py`, `test_repairer.py`, `context_builder.py`, `get_llm`, `load_case`, `validator_node`, `test_evaluator.py`, `test_graph.py`, `test_critic.py`, `test_deck_nodes.py`, `slide_component_planner.py`, `plan_reviewer_node`, `route_after_start`, `test_generator.py`, `plan_single_slide`, `initial_state`, `slide_edit_service.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `audit_layout()` connect `audit_layout` to `slide_edit_service.py`, `validator_node`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `PresentationState` (e.g. with `_build_default_plan()` and `context_builder_node()`) actually correct?**
  _`PresentationState` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `repairer_node()` (e.g. with `PresentationState` and `build_graph()`) actually correct?**
  _`repairer_node()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `build_graph()` (e.g. with `context_builder_node()` and `critic_node()`) actually correct?**
  _`build_graph()` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `version`, `newProjectRoot` to the rest of the system?**
  _138 weakly-connected nodes found - possible documentation gaps or missing edges._