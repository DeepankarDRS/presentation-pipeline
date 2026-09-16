# Graph Report - presentation-pipeline  (2026-09-16)

## Corpus Check
- 178 files · ~103,487 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1373 nodes · 3037 edges · 81 communities (59 shown, 14 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 161 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 71
- Community 75
- Community 76
- Community 77

## God Nodes (most connected - your core abstractions)
1. `initial_state()` - 90 edges
2. `PresentationState` - 61 edges
3. `audit_layout()` - 36 edges
4. `repairer_node()` - 35 edges
5. `build_graph()` - 32 edges
6. `get_llm()` - 29 edges
7. `evaluator_node()` - 28 edges
8. `critic_node()` - 27 edges
9. `_make_state()` - 26 edges
10. `build_contract()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `POM Pipeline Architecture Overview` --semantically_similar_to--> `LangGraph Presentation Pipeline`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `test_pipeline_with_hierarchical_planner()` --uses--> `OutlineSlide`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/outline_planner_schema.py
- `test_pipeline_with_hierarchical_planner()` --uses--> `OutlinePlannerOutput`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/outline_planner_schema.py
- `test_refine_plan_passes_feedback_to_planner()` --uses--> `OutlinePlannerOutput`  [INFERRED]
  tests/unit/test_api.py → src/agents/outline_planner_schema.py
- `test_refine_plan_returns_revised_plan()` --uses--> `OutlinePlannerOutput`  [INFERRED]
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

## Communities (81 total, 14 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (83): _build_default_plan(), Build a SlidePlan from test_case components, intent detection, or fallback., _get_constraints(), outline_planner_node(), Any, Parse DeckSettings dict → constraints dict for prompt injection., Plan the deck outline using an LLM with structured output., OutlinePlannerOutput (+75 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (82): _collect_kinds(), Walk the component tree and collect all leaf kinds (skipping 'group')., build_patch_prompts(), _choose_strategy(), _collect_problems(), _get_compile_diags(), _get_pre_issues(), Any (+74 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (73): Enum, FileResponse, get, post, put, _build_event(), _cleanup_old_runs(), ComponentPlanPayload (+65 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (62): AzureChatOpenAI, ChatOpenAI, parametrize, Critic agent — AI quality gate after successful compilation. Checks what the…, Take screenshot and run visual critic. Returns (issues, screenshot_path, usage)., Run the AI quality check and return (issues, usage)., _run_ai_check(), _run_visual_review() (+54 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (52): Element, _compile(), _find_soffice(), main(), Path, Render + audit a folder of POM XML files — the offline quality feedback loop.…, _to_pdf(), audit_layout() (+44 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (45): RuntimeError, OutlineSlide, BaseModel, Pydantic models for the outline planner's structured output. The outline…, Rich outline entry for one slide — enough context for slide_component_planner., Any, Outline replanner — regenerates a single outline slide from user feedback. Pre-…, Regenerate one OutlineSlide's content per user feedback, preserving its… (+37 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (44): LogRecord, Run the pipeline end-to-end and return the final state., run(), _format_table(), main(), Any, CLI runner — execute test cases and print a summary table. Usage: python -m…, Format results as an aligned ASCII table. (+36 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (46): critic_node(), _format_issues_for_display(), _manual_checkpoint(), Any, Format critic issues for CLI display., Present issues to user, ask Accept/Reject/Edit. Returns CriticResult., AI quality gate: text check + visual review + optional manual checkpoint., Render system + user prompts for the critic LLM call. (+38 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (38): _build_step_summary(), _compute_cost(), evaluator_node(), _generate_final_screenshots(), Any, Evaluator agent — mechanical scoring and run manifest. No LLM. Computes: -…, Generate screenshots from the final assembled PPTX. Always (re)renders from…, Write run-manifest.json to output/runs/{run_id}/. (+30 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (23): AmountOfText, AppView, ComponentKind, DeckSettingsSchema, EditSessionStatus, ElicitationQuestion, EvaluationSummary, EventType (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (33): Route to planning pipeline, questionnaire, or skip directly to generation., route_after_critic(), route_after_start(), route_after_validator(), initial_state(), Any, Create a fully-initialized starting state for the graph., _multi_slide_state() (+25 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (28): Backend, _check_screenshot_backend(), _kill_new_powerpnt_processes(), _kill_pids(), _list_powerpnt_pids(), PPTX-to-PNG screenshot service. Primary: Node.js script (screenshot-pom.js)…, Persist a failure record to disk. Log lines get missed; a file doesn't., PIDs of currently running POWERPNT.EXE processes (Windows only). (+20 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (19): _call_edit_llm(), _call_repair_llm(), edit_slide_xml(), Any, Apply a user's NL edit to a slide XML, validate, and repair if needed. Returns…, Attempt screenshot, retrying once on failure. Returns path or None. A failure…, Call the LLM to apply the user's edit instruction to the XML., Fix compile errors with the shared tier-1 patch prompt. Reuses the main… (+11 more)

### Community 13 - "Community 13"
Cohesion: 0.10
Nodes (26): Table Component (POM), Text Component (POM), Timeline Component (POM), Tree Component (POM), Common Box/Layout Attributes, Design Language Patterns, POM Document Structure, Group Rendering Rules (+18 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (11): DeckSettingsFormComponent, Component, PromptFormComponent, Component, SLIDE_COUNT_TO_THRESHOLD, THEME_PALETTES, CriticMode, DeckSettings (+3 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (24): _call_deck_repair_llm(), deck_assembler_node(), Any, Combine all completed slide XMLs into one multi-slide POM document and compile., Fix compile errors in the assembled multi-slide document, preserving all…, Save current slide result and advance to next slide index., slide_router_node(), patch (+16 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (22): Send, build_graph(), _elicitation_wait_node(), fan_out_slide_plans(), Any, LangGraph pipeline definition. Hierarchical planning topology: START →…, If elicitation is needed and no answers yet, suspend; else proceed., Fan-out to one slide_component_planner per outline slide. (+14 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (21): assemble_deck_xml(), _extract_slide_block(), _extract_theme(), Deck multi-slide nodes — slide_router and deck_assembler. slide_router: saves…, Extract the <Theme .../> element from XML., Extract the <Slide>...</Slide> block from XML., Combine per-slide XML into one normalized multi-slide POM document. Extracts…, ensure_single_theme() (+13 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (4): emptyOutlineSlide(), PlanEditorComponent, Component, OutlineSlide

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (19): _detect_components_from_text(), Select POM nodes needed for the given component kinds., Extract component kinds by scanning text for keywords., _select_nodes(), Tests for the context builder agent., Icon is a base node — always present regardless of component kinds., test_detect_components_chart(), test_detect_components_multiple() (+11 more)

### Community 20 - "Community 20"
Cohesion: 0.24
Nodes (19): generator_node(), Any, Render system + user prompts from the contract and slide plan., Generate POM XML via LLM using tiered prompts from the contract., _render_prompts(), _make_state(), patch, Tests for the generator agent with mocked LLM responses. (+11 more)

### Community 21 - "Community 21"
Cohesion: 0.20
Nodes (18): _merge_content_data(), Any, Slide replanner — decides whether an edit needs a richer SlidePlan. Feedback on…, Keep original values for existing keys; only take new keys from the replan. The…, Convert an existing SlidePlan to a minimal OutlineSlide for re-planning.…, Return (possibly-updated slide_plan, generation contract) for an edit. Degrades…, resolve_slide_plan(), _slide_plan_to_outline_slide() (+10 more)

### Community 22 - "Community 22"
Cohesion: 0.11
Nodes (19): @angular/common, @angular/compiler, @angular/core, @angular/forms, @angular/platform-browser, @angular/router, dependencies, @angular/common (+11 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (19): Complexity Spectrum Testing, Weight Hierarchy Design Pattern, KPI Row Test Case, Matrix Prioritization Test Case, Maximal Density Test Case, Minimal Statement Test Case, Mixed Chart-Matrix Test Case, Mixed Executive Slide Test Case (+11 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (17): _ask(), _load_palette_names(), Any, questionnaire_node(), Pre-generation questionnaire — collects audience/style/focus context. Presents…, Collect audience context via interactive CLI questions., Return [(name, tone), ...] from palettes.yaml, light first then dark., Print numbered menu and collect user choice. Returns the selected option. (+9 more)

### Community 25 - "Community 25"
Cohesion: 0.19
Nodes (18): normalize_xml(), pre_validate(), Any, Normalize raw LLM XML output: strip fences, fix colors, remove br/hr. Returns…, Full normalize + regex-based detection fallback for when parseXml is…, Tests for the validator agent. Unit tests mock the compiler; integration tests…, test_normalize_clean_xml_passes(), test_normalize_fixes_border_accent() (+10 more)

### Community 26 - "Community 26"
Cohesion: 0.18
Nodes (18): _load_yaml(), Build per-node attribute lists for only the nodes we selected., Select only notes relevant to the components in this slide. When has_grammar is…, _select_attributes(), _select_notes(), Icon gets its node-specific attributes plus size attrs., shadow and backgroundGradient are in common box attrs for layout/content nodes., test_attributes_chart() (+10 more)

### Community 27 - "Community 27"
Cohesion: 0.20
Nodes (14): Slide edit service — LLM-powered XML editing with mini repair loop. Takes user…, Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.…, compile_xml(), CompilerError, _parse_result(), Any, Path, Subprocess bridge to compile-pom.js (src/node/). The Node script writes… (+6 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (16): _load_yaml(), Any, Style resolver — loosely-coupled theme resolution. Public API:…, Resolve a theme name to a full theme dict. Returns: {name, mode, is_dark,…, LangGraph node: resolve theme and write to state., resolve_theme(), style_resolver_node(), Tests for the style resolver — theme resolution utility and graph node. (+8 more)

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (17): @angular/cli, @angular-devkit/build-angular, autoprefixer, devDependencies, @angular/cli, @angular-devkit/build-angular, autoprefixer, karma-chrome-launcher (+9 more)

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (17): schematics, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests (+9 more)

### Community 31 - "Community 31"
Cohesion: 0.15
Nodes (9): AppComponent, Component, appConfig, ElicitationFormComponent, Component, LayoutComponent, Component, ResultViewComponent (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.23
Nodes (16): build_contract(), _clean_list(), Any, Build a generation contract for one slide from its plan. Args: slide_plan: The…, _estimate_tokens(), _make_plan(), Rough token estimate: ~4 chars per token for English., Maximal-density (6 components): grammar + recipes + shrink checklist. (+8 more)

### Community 33 - "Community 33"
Cohesion: 0.22
Nodes (3): ProgressEvent, GenerationService, Injectable

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (14): _all_recipes(), _build_node_attributes(), _build_node_hierarchy(), _fmt_house_style_value(), Context builder agent — assembles knowledge base into a generation contract.…, Render a compact parent -> children map for the nodes on this slide. Extracts…, node name -> node-specific attributes from nodes.yaml., Render one house-style.yaml value (str / list / dict) as prompt text. (+6 more)

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (14): compile_graph(), Return a compiled, runnable graph., _mock_critic_llm(), patch, End-to-end: the graph runs to completion with mocked LLM + compiler., Return a mock LLM that passes through with_structured_output for the critic., End-to-end: graph runs with pre-provided slide_plans (skips planning phase)., Multi-slide: 2 pre-loaded slides, both compile, deck assembles. (+6 more)

### Community 36 - "Community 36"
Cohesion: 0.17
Nodes (13): LangGraph Presentation Pipeline, POM XML Markup Language, PresentationState TypedDict, Generate-Validate-Repair Retry Loop, DeckState Extended State Model, Loosely Coupled Editing Architecture, XML as Source of Truth, POM Pipeline Architecture Overview (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.21
Nodes (13): options, assets, browser, index, outputPath, polyfills, scripts, styles (+5 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (11): @hirokisakabe/pom, dependencies, @hirokisakabe/pom, description, main, name, private, scripts (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.26
Nodes (12): Any, Run the normalize → validate → compile pipeline on current_xml., validator_node(), patch, test_validator_compile_error_not_retryable(), test_validator_empty_xml(), test_validator_empty_xml_has_layout_issues_key(), test_validator_falls_back_to_pre_validate() (+4 more)

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (11): Evaluator Node (Mechanical), API Path (FastAPI + SSE), Deck Assembler Node, Questionnaire Node, Slide Router Node (Deck Mode), Line-by-Line Code and State Flow, Style Resolver Node, Pipeline Critical Review (+3 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (11): Family B — Deck Tests, Supplied Data Test Pattern, Deck Board Update Test Case, Deck Minimal 2-Slide Test Case, Deck Product Launch Data Test Case, Deck Product Launch Test Case, Deck QBR Data Test Case, Deck QBR Test Case (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (11): serve, development, buildTarget, extractLicenses, optimization, sourceMap, proxyConfig, builder (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (5): EditHistoryEntry, SlideReviewComponent, Component, SlideEditResponse, SlideInfoReview

### Community 44 - "Community 44"
Cohesion: 0.20
Nodes (9): prefix, projectType, root, sourceRoot, newProjectRoot, projects, frontend, $schema (+1 more)

### Community 45 - "Community 45"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, ng, start, test, watch (+1 more)

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (7): ProgressViewComponent, Component, PIPELINE_PHASES, PipelinePhase, PROGRESS_RANGES, STEP_LABELS, ThemePalette

### Community 47 - "Community 47"
Cohesion: 0.25
Nodes (9): Critic Node (LLM), Repair Guidance System, Repairer Node (LLM), Stall Detection Mechanism, Fail-Open Critic Risk, GPT-4.1 Model, Hierarchical Planning Pipeline Steps, LLM Model Configuration (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.25
Nodes (8): Node.js Compiler Bridge, POM Compiler v10.3.0 (@hirokisakabe/pom), Validator Node (Mechanical), XML Normalizer, Speaker Notes Lost in Pipeline, Layout Audit Post-Generation, Chart Component Spec, Dark Theme Chart Axis Bug Workaround

### Community 49 - "Community 49"
Cohesion: 0.32
Nodes (8): YAML Knowledge Base, Drawing Component Spec (Layer/Line/Arrow/Svg), Flow Component Spec (Flowchart), List Component Spec (Ul/Ol/Li), Matrix Component Spec (2x2 Grid), ProcessArrow Component Spec, Pyramid Component Spec, Shape Component Spec

### Community 50 - "Community 50"
Cohesion: 0.32
Nodes (8): Phase-Based Test System, Chart and Narrative Test Case, Chart and Table Test Case, Comparison Matrix Test Case, Dark Theme Test Case, Financial Report Test Case, Flowchart Test Case, Inline Formatting Test Case

### Community 51 - "Community 51"
Cohesion: 0.25
Nodes (8): build, builder, configurations, defaultConfiguration, production, budgets, buildTarget, outputHashing

### Community 52 - "Community 52"
Cohesion: 0.40
Nodes (6): Context Builder Node, Generation Contract, Generator Node (LLM), Tiered Prompt Assembly, Layout Variety Enforcement Discarded, PipelineTool Base Class

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (6): Family A — Base Prompt Tests, Base Revenue Trend Test Case, Base Risks Test Case, Base Roadmap Test Case, Base Strategy Statement Test Case, Base Vague Test Case

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (6): context_builder_node(), LangGraph node: build contract from slide_plans[current_slide_index]., test_context_builder_node_empty_plans(), test_context_builder_node_runs(), test_context_builder_uses_intent_detection(), test_context_builder_uses_test_case_components()

### Community 55 - "Community 55"
Cohesion: 0.53
Nodes (5): classifyError(), compile(), printSummary(), SLIDE_SIZE, validate()

### Community 56 - "Community 56"
Cohesion: 0.60
Nodes (5): findExecutable(), findImageMagick(), findSoffice(), isRealImageMagick(), main()

### Community 57 - "Community 57"
Cohesion: 0.40
Nodes (5): Planner Node (LLM), 14-Kind Component Vocabulary, Core Hook Narrative Anchor, Data Source Provenance, Slide Type Taxonomy

### Community 58 - "Community 58"
Cohesion: 0.40
Nodes (5): extract-i18n, test, builder, architect, builder

## Knowledge Gaps
- **134 isolated node(s):** `$schema`, `version`, `newProjectRoot`, `projectType`, `skipTests` (+129 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 454 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `initial_state()` connect `Community 10` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 35`, `Community 6`, `Community 7`, `Community 8`, `Community 39`, `Community 15`, `Community 16`, `Community 19`, `Community 20`, `Community 54`, `Community 24`, `Community 25`, `Community 28`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `PresentationState` connect `Community 16` to `Community 0`, `Community 1`, `Community 34`, `Community 3`, `Community 6`, `Community 7`, `Community 8`, `Community 39`, `Community 10`, `Community 15`, `Community 17`, `Community 20`, `Community 54`, `Community 24`, `Community 27`, `Community 28`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `get_llm()` connect `Community 3` to `Community 0`, `Community 1`, `Community 5`, `Community 12`, `Community 15`, `Community 17`, `Community 20`, `Community 27`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `PresentationState` (e.g. with `_build_default_plan()` and `context_builder_node()`) actually correct?**
  _`PresentationState` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `repairer_node()` (e.g. with `PresentationState` and `build_graph()`) actually correct?**
  _`repairer_node()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `build_graph()` (e.g. with `context_builder_node()` and `critic_node()`) actually correct?**
  _`build_graph()` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `version`, `newProjectRoot` to the rest of the system?**
  _134 weakly-connected nodes found - possible documentation gaps or missing edges._