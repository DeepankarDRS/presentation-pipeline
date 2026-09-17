# Graph Report - presentation-pipeline  (2026-09-17)

## Corpus Check
- 103 files · ~92,646 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1360 nodes · 3010 edges · 85 communities (63 shown, 14 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 155 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a444e668`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_planner.py
- test_repairer.py
- api.py
- get_llm
- audit_layout
- test_api.py
- load_case
- test_critic.py
- test_evaluator.py
- api.models.ts
- test_graph.py
- repair_guidance.py
- edit_slide_xml
- House Style Layout Grammar
- DeckSettingsFormComponent
- test_deck_nodes.py
- graph.py
- PresentationState
- PlanEditorComponent
- test_context_builder.py
- state.py
- _make_state
- dependencies
- Mixed Executive Slide Test Case
- questionnaire_node
- test_validator.py
- _load_yaml
- set_context
- resolve_theme
- devDependencies
- schematics
- app.component.ts
- build_contract
- GenerationService
- context_builder.py
- _mock_critic_llm
- LangGraph Presentation Pipeline
- options
- node/package.json
- test_full_pipeline.py
- Line-by-Line Code and State Flow
- Family B — Deck Tests
- development
- slide-review.component.ts
- frontend
- frontend/package.json
- theme.constants.ts
- Generator Node (LLM)
- post
- YAML Knowledge Base
- Phase-Based Test System
- build
- initial_state
- Family A — Base Prompt Tests
- BaseModel
- compile-pom.js
- screenshot-pom.js
- Planner Node (LLM)
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
- LLM Test Plan (Planner & Generator)
- Any
- _load_edit_session
- regenerate_outline_slide_endpoint

## God Nodes (most connected - your core abstractions)
1. `initial_state()` - 90 edges
2. `PresentationState` - 61 edges
3. `repairer_node()` - 35 edges
4. `audit_layout()` - 33 edges
5. `build_graph()` - 32 edges
6. `get_llm()` - 29 edges
7. `evaluator_node()` - 28 edges
8. `critic_node()` - 27 edges
9. `_make_state()` - 26 edges
10. `build_contract()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `POM Pipeline Architecture Overview` --semantically_similar_to--> `LangGraph Presentation Pipeline`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `test_pipeline_with_hierarchical_planner()` --uses--> `ElicitorOutput`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/elicitor_schema.py
- `test_pipeline_with_hierarchical_planner()` --uses--> `OutlineSlide`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/outline_planner_schema.py
- `test_pipeline_with_hierarchical_planner()` --uses--> `OutlinePlannerOutput`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/outline_planner_schema.py
- `test_pipeline_with_hierarchical_planner()` --uses--> `PlanReviewerOutput`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/plan_reviewer_schema.py

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

## Communities (85 total, 14 thin omitted)

### Community 0 - "test_planner.py"
Cohesion: 0.06
Nodes (75): _get_constraints(), outline_planner_node(), Any, Outline planner agent — produces the deck skeleton (replaces planner.py). Takes…, Parse DeckSettings dict → constraints dict for prompt injection., Plan the deck outline using an LLM with structured output., PlannerComponent, PlannerSlide (+67 more)

### Community 1 - "test_repairer.py"
Cohesion: 0.12
Nodes (27): _choose_strategy(), _collect_problems(), Pick PATCH or REGENERATE for this attempt. The loop is "PATCH once; if it still…, Collect error strings from normalize_result, compile_result, and critic_result., build_error_guidance(), is_stalled(), Build targeted repair guidance from errors. Returns formatted string., True if >=threshold of current errors were also in the previous attempt. (+19 more)

### Community 2 - "api.py"
Cohesion: 0.12
Nodes (23): Enum, FileResponse, get, _build_event(), CriticMode, deck_settings_schema(), download_pptx(), _format_sse() (+15 more)

### Community 3 - "get_llm"
Cohesion: 0.13
Nodes (23): AzureChatOpenAI, ChatOpenAI, check_and_elicit(), elicitor_node(), Any, Elicitor agent — detects vague queries and generates clarifying questions.…, Check if context is sufficient and return clarifying questions if not. Pure LLM…, Graph node: run elicitor and write results to state. If elicitation_answers are… (+15 more)

### Community 4 - "audit_layout"
Cohesion: 0.08
Nodes (46): Element, _compile(), _find_soffice(), main(), Path, Render + audit a folder of POM XML files — the offline quality feedback loop.…, _to_pdf(), audit_layout() (+38 more)

### Community 5 - "test_api.py"
Cohesion: 0.07
Nodes (52): ElicitationQuestion, ElicitorOutput, BaseModel, Pydantic models for the elicitor agent's structured output., OutlinePlannerOutput, OutlineSlide, BaseModel, Pydantic models for the outline planner's structured output. The outline… (+44 more)

### Community 6 - "load_case"
Cohesion: 0.18
Nodes (20): case_to_state(), load_all_cases(), load_case(), Any, Path, YAML test case loader. Loads test case definitions from tests/cases/*.yaml and…, Load a single test case by name (without .yaml extension)., Load all YAML test cases from the cases directory. (+12 more)

### Community 7 - "test_critic.py"
Cohesion: 0.09
Nodes (59): critic_node(), _format_issues_for_display(), _manual_checkpoint(), Any, Critic agent — AI quality gate after successful compilation. Checks what the…, Format critic issues for CLI display., Present issues to user, ask Accept/Reject/Edit. Returns CriticResult., Take screenshot and run visual critic. Returns (issues, screenshot_path, usage). (+51 more)

### Community 8 - "test_evaluator.py"
Cohesion: 0.06
Nodes (66): Backend, _build_step_summary(), _compute_cost(), evaluator_node(), _generate_final_screenshots(), Any, Evaluator agent — mechanical scoring and run manifest. No LLM. Computes: -…, Generate screenshots from the final assembled PPTX. Always (re)renders from… (+58 more)

### Community 9 - "api.models.ts"
Cohesion: 0.10
Nodes (23): AmountOfText, AppView, ComponentKind, DeckSettingsSchema, EditSessionStatus, ElicitationQuestion, EvaluationSummary, EventType (+15 more)

### Community 10 - "test_graph.py"
Cohesion: 0.13
Nodes (30): build_graph(), Construct the presentation pipeline graph (uncompiled)., route_after_critic(), route_after_repairer(), route_after_slide_router(), route_after_validator(), _slide_done_target(), StateGraph (+22 more)

### Community 11 - "repair_guidance.py"
Cohesion: 0.16
Nodes (20): error_signatures(), _extract_attr_from_error(), _extract_nodes_from_errors(), _extract_tag_from_error(), _find_node_attrs(), _format_attrs(), _load_knowledge_yaml(), needs_regeneration() (+12 more)

### Community 12 - "edit_slide_xml"
Cohesion: 0.12
Nodes (19): _call_edit_llm(), _call_repair_llm(), edit_slide_xml(), Any, Apply a user's NL edit to a slide XML, validate, and repair if needed. Returns…, Attempt screenshot, retrying once on failure. Returns path or None. A failure…, Call the LLM to apply the user's edit instruction to the XML., Fix compile errors with the shared tier-1 patch prompt. Reuses the main… (+11 more)

### Community 13 - "House Style Layout Grammar"
Cohesion: 0.16
Nodes (14): Text Component (POM), Common Box/Layout Attributes, Design Language Patterns, POM Document Structure, Group Rendering Rules, Height Budget System, House Style Layout Grammar, Weight Allocation System (+6 more)

### Community 14 - "DeckSettingsFormComponent"
Cohesion: 0.11
Nodes (11): DeckSettingsFormComponent, Component, PromptFormComponent, Component, SLIDE_COUNT_TO_THRESHOLD, THEME_PALETTES, CriticMode, DeckSettings (+3 more)

### Community 15 - "test_deck_nodes.py"
Cohesion: 0.11
Nodes (32): assemble_deck_xml(), deck_assembler_node(), _extract_slide_block(), _extract_theme(), Any, Extract the <Theme .../> element from XML., Extract the <Slide>...</Slide> block from XML., Combine all completed slide XMLs into one multi-slide POM document and compile. (+24 more)

### Community 16 - "graph.py"
Cohesion: 0.13
Nodes (21): _elicitation_wait_node(), Any, LangGraph pipeline definition. Hierarchical planning topology: START →…, If elicitation is needed and no answers yet, suspend; else proceed., Sort assembled_slide_plans by slide_index and write slide_plans., After plan review, always proceed to style_resolver (issues are advisory)., Placeholder node — pipeline suspends here when elicitation is needed. In…, Run the pipeline end-to-end and return the final state. (+13 more)

### Community 17 - "PresentationState"
Cohesion: 0.18
Nodes (21): _call_deck_repair_llm(), Deck multi-slide nodes — slide_router and deck_assembler. slide_router: saves…, Fix compile errors in the assembled multi-slide document, preserving all…, build_patch_prompts(), _get_compile_diags(), _get_pre_issues(), Any, Repairer agent — two repair strategies. PATCH: feed back failing XML + errors +… (+13 more)

### Community 18 - "PlanEditorComponent"
Cohesion: 0.13
Nodes (4): emptyOutlineSlide(), PlanEditorComponent, Component, OutlineSlide

### Community 19 - "test_context_builder.py"
Cohesion: 0.12
Nodes (27): _build_default_plan(), context_builder_node(), _detect_components_from_text(), Select POM nodes needed for the given component kinds., Extract component kinds by scanning text for keywords., Build a SlidePlan from test_case components, intent detection, or fallback., LangGraph node: build contract from slide_plans[current_slide_index]., _select_nodes() (+19 more)

### Community 20 - "state.py"
Cohesion: 0.09
Nodes (42): generator_node(), Any, Generator agent — produces POM XML from the plan + contract + data. Uses tiered…, Render system + user prompts from the contract and slide plan., Generate POM XML via LLM using tiered prompts from the contract., _render_prompts(), AttemptRecord, CompileResult (+34 more)

### Community 21 - "_make_state"
Cohesion: 0.22
Nodes (18): Pick the best verified example XML to seed a REGENERATE, or "" if none fits., _select_template(), _make_state(), _mock_llm(), patch, test_repairer_flags_noop_patch(), test_repairer_flags_truncation(), test_repairer_no_stall_when_errors_change() (+10 more)

### Community 22 - "dependencies"
Cohesion: 0.11
Nodes (19): @angular/common, @angular/compiler, @angular/core, @angular/forms, @angular/platform-browser, @angular/router, dependencies, @angular/common (+11 more)

### Community 23 - "Mixed Executive Slide Test Case"
Cohesion: 0.12
Nodes (19): Complexity Spectrum Testing, Weight Hierarchy Design Pattern, KPI Row Test Case, Matrix Prioritization Test Case, Maximal Density Test Case, Minimal Statement Test Case, Mixed Chart-Matrix Test Case, Mixed Executive Slide Test Case (+11 more)

### Community 24 - "questionnaire_node"
Cohesion: 0.17
Nodes (17): _ask(), _load_palette_names(), Any, questionnaire_node(), Pre-generation questionnaire — collects audience/style/focus context. Presents…, Collect audience context via interactive CLI questions., Return [(name, tone), ...] from palettes.yaml, light first then dark., Print numbered menu and collect user choice. Returns the selected option. (+9 more)

### Community 25 - "test_validator.py"
Cohesion: 0.07
Nodes (55): RuntimeError, Slide edit service — LLM-powered XML editing with mini repair loop. Takes user…, Any, Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.…, Run the normalize → validate → compile pipeline on current_xml., validator_node(), compile_xml(), CompilerError (+47 more)

### Community 26 - "_load_yaml"
Cohesion: 0.18
Nodes (18): _load_yaml(), Build per-node attribute lists for only the nodes we selected., Select only notes relevant to the components in this slide. When has_grammar is…, _select_attributes(), _select_notes(), Icon gets its node-specific attributes plus size attrs., shadow and backgroundGradient are in common box attrs for layout/content nodes., test_attributes_chart() (+10 more)

### Community 27 - "set_context"
Cohesion: 0.21
Nodes (13): LogRecord, ContextFilter, Structured logging with contextvars for run_id, step, and model. Usage: from…, Set one or more context variables for structured log output., Injects run_id, step, model from contextvars into log records., set_context(), Tests for the contextvars logging utility., test_context_filter_defaults() (+5 more)

### Community 28 - "resolve_theme"
Cohesion: 0.20
Nodes (16): _load_yaml(), Any, Style resolver — loosely-coupled theme resolution. Public API:…, Resolve a theme name to a full theme dict. Returns: {name, mode, is_dark,…, LangGraph node: resolve theme and write to state., resolve_theme(), style_resolver_node(), Tests for the style resolver — theme resolution utility and graph node. (+8 more)

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
Cohesion: 0.26
Nodes (14): build_contract(), Build a generation contract for one slide from its plan. Args: slide_plan: The…, _estimate_tokens(), _make_plan(), Rough token estimate: ~4 chars per token for English., Maximal-density (6 components): grammar + recipes + shrink checklist., _render_system_prompt(), test_build_contract_maximal() (+6 more)

### Community 33 - "GenerationService"
Cohesion: 0.22
Nodes (3): ProgressEvent, GenerationService, Injectable

### Community 34 - "context_builder.py"
Cohesion: 0.14
Nodes (16): _all_recipes(), _build_node_attributes(), _build_node_hierarchy(), _clean_list(), _fmt_house_style_value(), Any, Context builder agent — assembles knowledge base into a generation contract.…, Render a compact parent -> children map for the nodes on this slide. Extracts… (+8 more)

### Community 35 - "_mock_critic_llm"
Cohesion: 0.24
Nodes (11): _mock_critic_llm(), patch, End-to-end: the graph runs to completion with mocked LLM + compiler., Return a mock LLM that passes through with_structured_output for the critic., End-to-end: graph runs with pre-provided slide_plans (skips planning phase)., Multi-slide: 2 pre-loaded slides, both compile, deck assembles., 8-slide deck completes without hitting the recursion limit., test_8_slide_deck_no_recursion_error() (+3 more)

### Community 36 - "LangGraph Presentation Pipeline"
Cohesion: 0.18
Nodes (11): LangGraph Presentation Pipeline, POM XML Markup Language, PresentationState TypedDict, Generate-Validate-Repair Retry Loop, DeckState Extended State Model, Loosely Coupled Editing Architecture, XML as Source of Truth, POM Pipeline Architecture Overview (+3 more)

### Community 37 - "options"
Cohesion: 0.21
Nodes (13): options, assets, browser, index, outputPath, polyfills, scripts, styles (+5 more)

### Community 38 - "node/package.json"
Cohesion: 0.17
Nodes (11): @hirokisakabe/pom, dependencies, @hirokisakabe/pom, description, main, name, private, scripts (+3 more)

### Community 39 - "test_full_pipeline.py"
Cohesion: 0.22
Nodes (15): parametrize, compile_graph(), Return a compiled, runnable graph., _make_critic_llm(), _make_gen_llm(), patch, Integration tests — run the full pipeline for each YAML test case. All LLM…, Pipeline runs through the full hierarchical planning pipeline. (+7 more)

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

### Community 47 - "Generator Node (LLM)"
Cohesion: 0.17
Nodes (15): Critic Node (LLM), Generator Node (LLM), Repair Guidance System, Repairer Node (LLM), Stall Detection Mechanism, Tiered Prompt Assembly, Validator Node (Mechanical), XML Normalizer (+7 more)

### Community 48 - "post"
Cohesion: 0.15
Nodes (15): post, _cleanup_old_runs(), create_outline(), elicit(), ElicitRequest, finalize_deck(), FinalizeResponse, generate() (+7 more)

### Community 49 - "YAML Knowledge Base"
Cohesion: 0.20
Nodes (12): Node.js Compiler Bridge, YAML Knowledge Base, POM Compiler v10.3.0 (@hirokisakabe/pom), Chart Component Spec, Dark Theme Chart Axis Bug Workaround, Drawing Component Spec (Layer/Line/Arrow/Svg), Flow Component Spec (Flowchart), List Component Spec (Ul/Ol/Li) (+4 more)

### Community 50 - "Phase-Based Test System"
Cohesion: 0.32
Nodes (8): Phase-Based Test System, Chart and Narrative Test Case, Chart and Table Test Case, Comparison Matrix Test Case, Dark Theme Test Case, Financial Report Test Case, Flowchart Test Case, Inline Formatting Test Case

### Community 51 - "build"
Cohesion: 0.25
Nodes (8): build, builder, configurations, defaultConfiguration, production, budgets, buildTarget, outputHashing

### Community 52 - "initial_state"
Cohesion: 0.19
Nodes (15): Send, fan_out_slide_plans(), Fan-out to one slide_component_planner per outline slide., Route to planning pipeline, questionnaire, or skip directly to generation., route_after_start(), initial_state(), Any, Create a fully-initialized starting state for the graph. (+7 more)

### Community 53 - "Family A — Base Prompt Tests"
Cohesion: 0.33
Nodes (6): Family A — Base Prompt Tests, Base Revenue Trend Test Case, Base Risks Test Case, Base Roadmap Test Case, Base Strategy Statement Test Case, Base Vague Test Case

### Community 54 - "BaseModel"
Cohesion: 0.16
Nodes (15): ComponentPlanPayload, create_edit_session(), edit_slide(), EditRecord, EditSessionResponse, ElicitAnswerRequest, GenerateRequest, BaseModel (+7 more)

### Community 55 - "compile-pom.js"
Cohesion: 0.53
Nodes (5): classifyError(), compile(), printSummary(), SLIDE_SIZE, validate()

### Community 56 - "screenshot-pom.js"
Cohesion: 0.60
Nodes (5): findExecutable(), findImageMagick(), findSoffice(), isRealImageMagick(), main()

### Community 57 - "Planner Node (LLM)"
Cohesion: 0.25
Nodes (8): Context Builder Node, Generation Contract, Planner Node (LLM), Layout Variety Enforcement Discarded, 14-Kind Component Vocabulary, Core Hook Narrative Anchor, Data Source Provenance, Slide Type Taxonomy

### Community 58 - "architect"
Cohesion: 0.40
Nodes (5): extract-i18n, test, builder, architect, builder

### Community 81 - "LLM Test Plan (Planner & Generator)"
Cohesion: 0.19
Nodes (13): Pipeline Critical Review, Table Component (POM), Timeline Component (POM), Tree Component (POM), POM Node Allowlist (Phase Registry), POM Validation Rules & Forbidden Tags, Test Case: Architecture Diagram (Phase D), Test Case: Competitor Comparison (+5 more)

### Community 82 - "Any"
Cohesion: 0.22
Nodes (13): put, GenerateFromPlanRequest, _merge_state(), _payload_to_slide_plans(), Any, Store a user-edited outline for use in the next generation call. The edited…, Run the plan reviewer on a set of slide plans (for standalone plan review)., refine_plan() (+5 more)

### Community 83 - "_load_edit_session"
Cohesion: 0.33
Nodes (6): EditSession, EditSlideState, _load_edit_session(), _persist_slides_json(), Load edit session from slides.json on disk., Update slides.json on disk after an edit.

### Community 84 - "regenerate_outline_slide_endpoint"
Cohesion: 0.67
Nodes (3): Regenerate one outline slide's content from user feedback. Stateless — no…, regenerate_outline_slide_endpoint(), RegenerateOutlineSlideRequest

## Knowledge Gaps
- **133 isolated node(s):** `$schema`, `version`, `newProjectRoot`, `projectType`, `skipTests` (+128 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 448 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `initial_state()` connect `initial_state` to `test_planner.py`, `test_repairer.py`, `api.py`, `load_case`, `test_critic.py`, `test_evaluator.py`, `test_graph.py`, `test_deck_nodes.py`, `graph.py`, `PresentationState`, `test_context_builder.py`, `state.py`, `_make_state`, `questionnaire_node`, `test_validator.py`, `resolve_theme`, `_mock_critic_llm`, `test_full_pipeline.py`, `post`, `BaseModel`, `Any`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `PresentationState` connect `PresentationState` to `test_planner.py`, `test_repairer.py`, `context_builder.py`, `get_llm`, `load_case`, `test_critic.py`, `test_evaluator.py`, `test_graph.py`, `test_deck_nodes.py`, `graph.py`, `test_context_builder.py`, `state.py`, `_make_state`, `initial_state`, `questionnaire_node`, `test_validator.py`, `resolve_theme`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `audit_layout()` connect `audit_layout` to `test_validator.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `PresentationState` (e.g. with `_build_default_plan()` and `context_builder_node()`) actually correct?**
  _`PresentationState` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `repairer_node()` (e.g. with `PresentationState` and `build_graph()`) actually correct?**
  _`repairer_node()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `build_graph()` (e.g. with `context_builder_node()` and `critic_node()`) actually correct?**
  _`build_graph()` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `version`, `newProjectRoot` to the rest of the system?**
  _133 weakly-connected nodes found - possible documentation gaps or missing edges._