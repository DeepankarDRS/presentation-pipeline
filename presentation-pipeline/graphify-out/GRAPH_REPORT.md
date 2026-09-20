# Graph Report - presentation-pipeline  (2026-09-20)

## Corpus Check
- 27 files · ~111,869 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1502 nodes · 2956 edges · 107 communities (62 shown, 37 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 105 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Context Builder & Prompts
- API Layer & Endpoints
- Validator & Normalizer
- Outline Planner & API Tests
- Architecture & Knowledge Components
- Planner & Settings Mapper
- Critic & Visual Critic
- Design Language & Recipes
- Deck Assembly & PPTX Merge
- Frontend Services & Models
- Evaluator & Cost Tracking
- Layout Audit Tests
- Repair Guidance & Strategy
- Elicitor & LLM Client
- Slide Edit Service
- LangGraph Pipeline & Routing
- Screenshot & COM Backend
- State Models & Outline Schema
- Runner & Logging Config
- Generator & Render Prompts
- Layout Audit Checks
- Repairer Core Logic
- Repairer Node & Stall Tests
- Case Loader & Test Utils
- Frontend Src App
- Src Agents Slide
- Frontend Src App
- Src Compiler Repair
- Concept Complexity Spectrum
- Src Agents Questionnaire
- Src Graph Route
- Src Agents Style
- Src Api Run
- Angular Cli
- Angular Common
- Frontend Angular Frontend
- Frontend Src App
- Frontend Src App
- Send
- Frontend Angular Build
- Frontend Src App
- Parametrize
- Src Agents Validator
- Src Knowledge Components
- Hirokisakabe Pom
- Src Agents Slide
- Concept Family B
- Frontend Angular Architect
- Frontend Angular
- Frontend Package
- Src Agents Context
- Src Agents Repairer
- Concept Phase Test
- Frontend Angular Architect
- Scripts Verify Li
- Component
- Concept Family A
- Src Node Compile
- Frontend Angular Architect
- Scripts Render Check
- Src Knowledge Core
- Src Knowledge Core
- Src Knowledge Core
- Concept Golden Fixtures
- Frontend Package Devdependencies
- Frontend Package Devdependencies
- Frontend Package Devdependencies
- Frontend Package Devdependencies
- Frontend Package Devdependencies
- Frontend Package Devdependencies
- Frontend Readme Angular
- Src Knowledge Core
- Src Knowledge Core
- Tests Conftest
- Tests Unit Test
- Tests Unit Test
- Any
- Concept Test Case
- Editing Architecture Deck
- Editing Architecture Loosely
- Editing Architecture Pipeline
- Editing Architecture Reentry
- Frontend Src App
- Frontend Src App
- Otherpc Test Fable
- Pkg Presentation Pipeline
- Presentationstate
- Requirements Python Dependencies
- Src Agents Planner
- Src Knowledge Core
- Src Knowledge Core
- Src Knowledge Core
- Src Knowledge Core
- Src Knowledge Core
- Src Knowledge Core
- Src Knowledge Core
- Tests Cases Pitch
- Tests Cases Pyramid
- Tests Cases Tree

## God Nodes (most connected - your core abstractions)
1. `initial_state()` - 68 edges
2. `audit_layout()` - 45 edges
3. `build_graph()` - 30 edges
4. `evaluator_node()` - 28 edges
5. `build_contract()` - 27 edges
6. `PlannerSlide` - 22 edges
7. `repairer_node()` - 21 edges
8. `validator_node()` - 21 edges
9. `GenerationService` - 20 edges
10. `ApiService` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Generation Contract (Knowledge Base Assembly)` --semantically_similar_to--> `Context Builder Node (Mechanical)`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `Two-Strategy Repair (PATCH/REGENERATE)` --semantically_similar_to--> `Repairer Node (PATCH/REGENERATE Strategy)`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `Repair Safety Rules` --semantically_similar_to--> `POM Validation Rules`  [INFERRED] [semantically similar]
  docs/repair-budget-split.md → src/knowledge/core/validation.yaml
- `Pre-Generation Clarification Questions` --semantically_similar_to--> `Questionnaire Node (Interactive)`  [INFERRED] [semantically similar]
  GENOFFICE_FEATURE_ADOPTION.md → CODE_FLOW.md
- `Dedicated Style Skill (LLM Style Generation)` --semantically_similar_to--> `Style Resolver Node (Theme Resolution)`  [INFERRED] [semantically similar]
  GENOFFICE_FEATURE_ADOPTION.md → CODE_FLOW.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Deck Mode Quality Gaps** — code_review_deck_critic_accounting, code_review_deck_validation_weakness, code_flow_slide_router_node, code_flow_deck_assembler_node [EXTRACTED 1.00]
- **Generate-Validate-Repair Feedback Loop** — architecture_generator, architecture_validator, architecture_repairer, architecture_retry_loop, architecture_stall_detection, code_flow_routing_logic [EXTRACTED 1.00]
- **Knowledge Base Drives XML Generation** — architecture_knowledge_base, architecture_context_builder, flow_generation_contract, architecture_generator [EXTRACTED 1.00]
- **LLM Test Family A Base-Prompt Cases** — tests_llm_test_plan_test_plan, tests_cases_base_competitor_comparison_test_case, tests_cases_base_org_structure_test_case, tests_cases_base_overstuffed_test_case, tests_cases_base_process_overview_test_case, tests_cases_base_quarterly_metrics_test_case [EXTRACTED 1.00]
- **LLM Pipeline Steps (Hierarchical Planning)** — models_elicitor_step, models_outline_planner_step, models_slide_component_planner_step, models_generator_step, models_critic_step, models_repairer_step, models_visual_critic_step, models_slide_editor_step [EXTRACTED 1.00]
- **Dual-Budget Repair System** — docs_repair_budget_split_compile_repairer_strategy, docs_repair_budget_split_visual_repairer_strategy, docs_repair_budget_split_visual_repairer_node, docs_repair_budget_split_safety_rules [EXTRACTED 1.00]
- **** — tests_cases_base_revenue_trend_yaml, tests_cases_base_risks_yaml, tests_cases_base_roadmap_yaml, tests_cases_base_strategy_statement_yaml, tests_cases_base_vague_yaml [EXTRACTED 1.00]
- **** — tests_cases_chart_and_narrative_yaml, tests_cases_chart_and_table_yaml, tests_cases_comparison_matrix_yaml, tests_cases_dark_theme_yaml, tests_cases_financial_report_yaml, tests_cases_flowchart_yaml, tests_cases_inline_formatting_yaml [EXTRACTED 1.00]
- **** — tests_cases_deck_qbr_yaml, tests_cases_deck_qbr_data_yaml, tests_cases_deck_board_update_yaml, tests_cases_deck_sales_enablement_yaml, tests_cases_deck_sales_data_yaml [INFERRED 0.85]
- **House Style Layout System** — src_knowledge_core_house_style_frame, src_knowledge_core_house_style_sizing_vocabulary, src_knowledge_core_house_style_height_budget, src_knowledge_core_house_style_composition [EXTRACTED 1.00]
- **Design Language Visual System** — src_knowledge_core_design_language_visual_hierarchy, src_knowledge_core_design_language_color_usage, src_knowledge_core_design_language_spacing, src_knowledge_core_design_language_card_recipe [EXTRACTED 1.00]
- **Rigid Component Recipe Collection** — src_knowledge_core_recipes_chart_card, src_knowledge_core_recipes_table_card, src_knowledge_core_recipes_timeline, src_knowledge_core_recipes_matrix, src_knowledge_core_recipes_process_arrow, src_knowledge_core_recipes_flow, src_knowledge_core_recipes_pyramid, src_knowledge_core_recipes_tree [INFERRED 0.95]

## Communities (107 total, 37 thin omitted)

### Community 0 - "Context Builder & Prompts"
Cohesion: 0.05
Nodes (77): _all_recipes(), build_contract(), _build_default_plan(), _build_node_attributes(), _build_node_hierarchy(), _clean_list(), context_builder_node(), _detect_components_from_text() (+69 more)

### Community 1 - "API Layer & Endpoints"
Cohesion: 0.06
Nodes (72): Enum, FileResponse, get, post, put, _build_event(), _cleanup_old_runs(), ComponentPlanPayload (+64 more)

### Community 2 - "Validator & Normalizer"
Cohesion: 0.07
Nodes (55): RuntimeError, Any, Path, PresentationState, Run the normalize → validate → compile pipeline on current_xml., validator_node(), compile_xml(), CompilerError (+47 more)

### Community 3 - "Outline Planner & API Tests"
Cohesion: 0.07
Nodes (47): OutlinePlannerOutput, OutlineSlide, BaseModel, Pydantic models for the outline planner's structured output. The outline…, Rich outline entry for one slide — enough context for slide_component_planner., Complete deck outline from the outline planner., Any, Outline replanner — regenerates a single outline slide from user feedback. Pre-… (+39 more)

### Community 4 - "Architecture & Knowledge Components"
Cohesion: 0.05
Nodes (54): Node.js Compiler Bridge (Subprocess), Context Builder Node (Mechanical), Visual Critic Node (Vision LLM Quality Gate), Evaluator Node (Scoring + Manifest), Generator Node (LLM XML Generation), YAML Knowledge Base, LangGraph Presentation Pipeline, Planner Node (LLM Structured Output) (+46 more)

### Community 5 - "Planner & Settings Mapper"
Cohesion: 0.08
Nodes (50): BaseModel, _get_constraints(), outline_planner_node(), Any, Parse DeckSettings dict → constraints dict for prompt injection., Plan the deck outline using an LLM with structured output., PlanReviewerOutput, PlanReviewIssue (+42 more)

### Community 6 - "Critic & Visual Critic"
Cohesion: 0.09
Nodes (46): _critic_inner(), critic_node(), Any, PresentationState, Critic agent — visual quality gate after successful compilation. The visual…, Take screenshot and run visual critic. Returns (issues, screenshot_path, usage,…, Visual quality gate — screenshot-based review using a vision LLM., _run_visual_review() (+38 more)

### Community 7 - "Design Language & Recipes"
Cohesion: 0.05
Nodes (48): Compile Repairer Strategy Decision, Repair Budget Split Design, Repair Safety Rules, Separate Budgets with Safe Discard, Visual Repairer Node, Visual Repairer Strategy Decision, Few-Shot Over Rules Lesson, Outline Planner Rewording Backfire (+40 more)

### Community 8 - "Deck Assembly & PPTX Merge"
Cohesion: 0.09
Nodes (40): assemble_deck_xml(), deck_assembler_node(), _extract_slide_block(), _extract_theme(), Any, Path, PresentationState, Deck multi-slide nodes — slide_router and deck_assembler. slide_router: saves… (+32 more)

### Community 9 - "Frontend Services & Models"
Cohesion: 0.09
Nodes (26): EditHistoryEntry, AmountOfText, AppView, ComponentKind, DeckSettingsSchema, EditSessionStatus, ElicitationQuestion, ElicitResponse (+18 more)

### Community 10 - "Evaluator & Cost Tracking"
Cohesion: 0.11
Nodes (39): _build_step_summary(), _compute_cost(), evaluator_node(), _generate_final_screenshots(), Any, PresentationState, Evaluator agent — mechanical scoring and run manifest. No LLM. Computes: -…, Generate screenshots from the final assembled PPTX. Always (re)renders from… (+31 more)

### Community 11 - "Layout Audit Tests"
Cohesion: 0.10
Nodes (34): audit_layout(), Parse POM XML and check spatial/layout constraints. Returns a list of issue…, Tests for the layout audit — mechanical spatial checks on POM XML., Mixed-width table: specified cols under budget, auto-fill cols present., All-auto table: no widths specified, nothing to check., Icon inside Li is silently stripped by POM — audit must catch it., Valid inline tags inside Li should not trigger LI_INVALID_CHILD., HStack-root layout with a VStack column whose heights exceed 720. (+26 more)

### Community 12 - "Repair Guidance & Strategy"
Cohesion: 0.10
Nodes (32): build_error_guidance(), cap_diag_msg(), is_stalled(), needs_regeneration(), Strip enum listings and hard-cap length so no diagnostic bloats the prompt., Build targeted repair guidance from errors. Returns formatted string., True if >=threshold of current errors were also in the previous attempt., True when the errors are structural — an in-place PATCH is unlikely to fix them… (+24 more)

### Community 13 - "Elicitor & LLM Client"
Cohesion: 0.09
Nodes (28): AzureChatOpenAI, ChatOpenAI, ElicitorOutput, check_and_elicit(), _elicitor_inner(), elicitor_node(), Any, PresentationState (+20 more)

### Community 14 - "Slide Edit Service"
Cohesion: 0.11
Nodes (23): _call_edit_llm(), _call_repair_llm(), edit_slide_xml(), Any, Path, Slide edit service — LLM-powered XML editing with mini repair loop. Takes user…, Fix compile errors with the shared tier-1 patch prompt. Reuses the main…, Apply a user's NL edit to a slide XML, validate, and repair if needed. Returns… (+15 more)

### Community 15 - "LangGraph Pipeline & Routing"
Cohesion: 0.12
Nodes (28): build_graph(), _elicitation_wait_node(), placeholder_node(), Any, PresentationState, LangGraph pipeline definition. Hierarchical planning topology: START →…, If elicitation is needed and no answers yet, suspend; else proceed., Sort assembled_slide_plans by slide_index and write slide_plans. (+20 more)

### Community 16 - "Screenshot & COM Backend"
Cohesion: 0.14
Nodes (26): Backend, _check_screenshot_backend(), _kill_new_powerpnt_processes(), _kill_pids(), _list_powerpnt_pids(), PPTX-to-PNG screenshot service. Uses PowerPoint COM automation via comtypes…, Render each slide in a PPTX to PNG via PowerPoint COM. Always returns a result…, Detect whether the PowerPoint COM backend is available. (+18 more)

### Community 17 - "State Models & Outline Schema"
Cohesion: 0.15
Nodes (24): Outline planner agent — produces the deck skeleton (replaces planner.py). Takes…, AttemptRecord, CompileResult, ComponentPlan, CriticResult, DeckPlan, OutlinePlan, OutlineSlide (+16 more)

### Community 18 - "Runner & Logging Config"
Cohesion: 0.12
Nodes (22): LogRecord, _format_table(), main(), Any, CLI runner — execute test cases and print a summary table. Usage: python -m…, Format results as an aligned ASCII table., Run test cases and return summary rows., run_cases() (+14 more)

### Community 19 - "Generator & Render Prompts"
Cohesion: 0.20
Nodes (22): _generator_inner(), generator_node(), Any, PresentationState, Generator agent — produces POM XML from the plan + contract + data. Uses tiered…, Render system + user prompts from the contract and slide plan., Generate POM XML via LLM using tiered prompts from the contract., _render_prompts() (+14 more)

### Community 20 - "Layout Audit Checks"
Cohesion: 0.14
Nodes (22): Element, _check_band_height_sum(), _check_col_widths(), _check_font_sizes(), _check_hstack_column_heights(), _check_li_children(), _check_missing_dims(), _check_nesting() (+14 more)

### Community 21 - "Repairer Core Logic"
Cohesion: 0.15
Nodes (22): _build_repair_context(), _call_llm_and_return(), _choose_strategy(), _collect_problems(), _get_compile_diags(), _get_pre_issues(), _plan_to_outline_slide(), Any (+14 more)

### Community 22 - "Repairer Node & Stall Tests"
Cohesion: 0.23
Nodes (22): Choose a repair strategy, build the prompt, call the LLM, update state., repairer_node(), _make_state(), _mock_llm(), _mock_replan(), patch, Set up mocks for the REGENERATE path (plan_single_slide + build_contract)., Regression: a recurring compiler diagnostic must be recognised as a stall. (+14 more)

### Community 23 - "Case Loader & Test Utils"
Cohesion: 0.18
Nodes (20): case_to_state(), load_all_cases(), load_case(), Any, Path, YAML test case loader. Loads test case definitions from tests/cases/*.yaml and…, Load a single test case by name (without .yaml extension)., Load all YAML test cases from the cases directory. (+12 more)

### Community 24 - "Frontend Src App"
Cohesion: 0.12
Nodes (11): AppComponent, Component, appConfig, ElicitationFormComponent, Component, LayoutComponent, Component, ProgressViewComponent (+3 more)

### Community 25 - "Src Agents Slide"
Cohesion: 0.20
Nodes (19): _merge_content_data(), Any, Slide replanner — decides whether an edit needs a richer SlidePlan. Feedback on…, Keep original values for existing keys; only take new keys from the replan. The…, Convert an existing SlidePlan to a minimal OutlineSlide for re-planning.…, Return (possibly-updated slide_plan, generation contract) for an edit. Degrades…, resolve_slide_plan(), _slide_plan_to_outline_slide() (+11 more)

### Community 26 - "Frontend Src App"
Cohesion: 0.13
Nodes (4): emptyOutlineSlide(), PlanEditorComponent, Component, OutlineSlide

### Community 27 - "Src Compiler Repair"
Cohesion: 0.17
Nodes (19): error_signatures(), _extract_attr_from_error(), _extract_nodes_from_errors(), _extract_tag_from_error(), _find_node_attrs(), _format_attrs(), _load_knowledge_yaml(), Any (+11 more)

### Community 28 - "Concept Complexity Spectrum"
Cohesion: 0.12
Nodes (19): Complexity Spectrum Testing, Weight Hierarchy Design Pattern, KPI Row Test Case, Matrix Prioritization Test Case, Maximal Density Test Case, Minimal Statement Test Case, Mixed Chart-Matrix Test Case, Mixed Executive Slide Test Case (+11 more)

### Community 29 - "Src Agents Questionnaire"
Cohesion: 0.17
Nodes (17): _ask(), _load_palette_names(), Any, questionnaire_node(), Pre-generation questionnaire — collects audience/style/focus context. Presents…, Collect audience context via interactive CLI questions., Return [(name, tone), ...] from palettes.yaml, light first then dark., Print numbered menu and collect user choice. Returns the selected option. (+9 more)

### Community 30 - "Src Graph Route"
Cohesion: 0.19
Nodes (18): route_after_critic(), route_after_slide_router(), _mock_visual_critic_pass(), _multi_slide_state(), Tests for the LangGraph pipeline with stub agents., Return a clean-pass 3-tuple matching run_visual_critic's signature., Create a state with 2 slide_plans (multi-slide mode)., test_route_after_critic_fail() (+10 more)

### Community 31 - "Src Agents Style"
Cohesion: 0.20
Nodes (16): _load_yaml(), Any, Style resolver — loosely-coupled theme resolution. Public API:…, Resolve a theme name to a full theme dict. Returns: {name, mode, is_dark,…, LangGraph node: resolve theme and write to state., resolve_theme(), style_resolver_node(), Tests for the style resolver — theme resolution utility and graph node. (+8 more)

### Community 32 - "Src Api Run"
Cohesion: 0.15
Nodes (16): _run_pipeline_sync(), compile_graph(), Return a compiled, runnable graph., _mock_screenshot_batch(), _MockBatch, _MockSlide, patch, End-to-end: the graph runs to completion with mocked LLM + compiler. (+8 more)

### Community 33 - "Angular Cli"
Cohesion: 0.12
Nodes (17): @angular/cli, @angular/compiler-cli, @angular-devkit/build-angular, autoprefixer, devDependencies, @angular/cli, @angular/compiler-cli, @angular-devkit/build-angular (+9 more)

### Community 34 - "Angular Common"
Cohesion: 0.12
Nodes (17): @angular/common, @angular/compiler, @angular/core, @angular/forms, @angular/platform-browser, @angular/router, dependencies, @angular/common (+9 more)

### Community 35 - "Frontend Angular Frontend"
Cohesion: 0.12
Nodes (17): schematics, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests (+9 more)

### Community 36 - "Frontend Src App"
Cohesion: 0.19
Nodes (4): GenerateRequest, ProgressEvent, GenerationService, Injectable

### Community 37 - "Frontend Src App"
Cohesion: 0.19
Nodes (5): DeckSettingsFormComponent, Component, DeckSettings, DeckSettingsField, DeckSettingsFieldOption

### Community 38 - "Send"
Cohesion: 0.19
Nodes (15): Send, fan_out_slide_plans(), Fan-out to one slide_component_planner per outline slide., Route to planning pipeline, questionnaire, or skip directly to generation., route_after_start(), initial_state(), Any, Create a fully-initialized starting state for the graph. (+7 more)

### Community 39 - "Frontend Angular Build"
Cohesion: 0.19
Nodes (14): options, assets, browser, index, outputPath, polyfills, scripts, styles (+6 more)

### Community 40 - "Frontend Src App"
Cohesion: 0.19
Nodes (9): PromptFormComponent, PIPELINE_PHASES, PipelinePhase, PROGRESS_RANGES, SLIDE_COUNT_TO_THRESHOLD, STEP_LABELS, THEME_PALETTES, CriticMode (+1 more)

### Community 41 - "Parametrize"
Cohesion: 0.23
Nodes (13): parametrize, _make_gen_llm(), _make_screenshot_mock(), patch, Integration tests — run the full pipeline for each YAML test case. All LLM…, Pipeline runs through the full hierarchical planning pipeline., Pipeline retries on compile failure and eventually passes., Mock generator LLM that returns valid POM XML. (+5 more)

### Community 42 - "Src Agents Validator"
Cohesion: 0.21
Nodes (12): normalize_and_compile(), Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.…, Normalize + compile check. Returns (ok, compile_result). Used by the visual…, _build_visual_problems(), _do_patch(), _do_regenerate(), Any, Visual repairer — one-shot repair after visual critic failure. Respects the… (+4 more)

### Community 43 - "Src Knowledge Components"
Cohesion: 0.15
Nodes (13): Tree Component (POM), POM Document Structure, Chart-on-Dark Workaround, Theme Palette Library, compile-pom.js (POM Compiler Wrapper), @hirokisakabe/pom v10.3.0 (External Dependency), presentation-mvp-compiler (npm package), Test Case: Competitor Comparison (+5 more)

### Community 44 - "Hirokisakabe Pom"
Cohesion: 0.17
Nodes (11): @hirokisakabe/pom, dependencies, @hirokisakabe/pom, description, main, name, private, scripts (+3 more)

### Community 45 - "Src Agents Slide"
Cohesion: 0.27
Nodes (11): _filter_supplied_content_for_slide(), plan_single_slide(), Any, PresentationState, Slide component planner — plans ONE slide in detail (fan-out target). Called…, Return subset of supplied_content relevant to this slide's key_messages., Plan one slide and return a SlidePlan TypedDict. Can be called directly (e.g.…, Plan all slides sequentially in a single node (SERIALIZE_SLIDES=True path). (+3 more)

### Community 46 - "Concept Family B"
Cohesion: 0.22
Nodes (11): Family B — Deck Tests, Supplied Data Test Pattern, Deck Board Update Test Case, Deck Minimal 2-Slide Test Case, Deck Product Launch Data Test Case, Deck Product Launch Test Case, Deck QBR Data Test Case, Deck QBR Test Case (+3 more)

### Community 47 - "Frontend Angular Architect"
Cohesion: 0.18
Nodes (11): serve, development, buildTarget, extractLicenses, optimization, sourceMap, proxyConfig, builder (+3 more)

### Community 48 - "Frontend Angular"
Cohesion: 0.20
Nodes (9): prefix, projectType, root, sourceRoot, newProjectRoot, projects, frontend, $schema (+1 more)

### Community 49 - "Frontend Package"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, ng, start, test, watch (+1 more)

### Community 50 - "Src Agents Context"
Cohesion: 0.29
Nodes (7): Context builder agent — assembles knowledge base into a generation contract.…, _plan_reviewer_inner(), plan_reviewer_node(), Any, PresentationState, Plan reviewer agent — evaluates assembled deck plan quality. Runs after all…, Review the assembled slide plans and emit a confidence score.

### Community 51 - "Src Agents Repairer"
Cohesion: 0.22
Nodes (9): build_patch_prompts(), _cap_xml(), Build the (system, user) prompts for a PATCH (in-place fix) repair. Shared by…, Keep head + tail of XML so root setup and closing tags are visible., build_patch_prompts must cap failing_xml before rendering., test_build_patch_prompts(), test_cap_xml_applied_in_build_patch_prompts(), test_cap_xml_short_unchanged() (+1 more)

### Community 52 - "Concept Phase Test"
Cohesion: 0.32
Nodes (8): Phase-Based Test System, Chart and Narrative Test Case, Chart and Table Test Case, Comparison Matrix Test Case, Dark Theme Test Case, Financial Report Test Case, Flowchart Test Case, Inline Formatting Test Case

### Community 53 - "Frontend Angular Architect"
Cohesion: 0.25
Nodes (8): build, builder, configurations, defaultConfiguration, production, budgets, buildTarget, outputHashing

### Community 54 - "Scripts Verify Li"
Cohesion: 0.48
Nodes (6): _compile(), _count_icons_in_pptx(), main(), Path, Verify that LI_INVALID_CHILD audit catches silently-stripped block elements.…, Count icon/image references in the PPTX slide XML.

### Community 56 - "Concept Family A"
Cohesion: 0.33
Nodes (6): Family A — Base Prompt Tests, Base Revenue Trend Test Case, Base Risks Test Case, Base Roadmap Test Case, Base Strategy Statement Test Case, Base Vague Test Case

### Community 57 - "Src Node Compile"
Cohesion: 0.53
Nodes (5): classifyError(), compile(), printSummary(), SLIDE_SIZE, validate()

### Community 58 - "Frontend Angular Architect"
Cohesion: 0.40
Nodes (5): extract-i18n, test, builder, architect, builder

### Community 59 - "Scripts Render Check"
Cohesion: 0.60
Nodes (4): _compile(), main(), Path, Render + audit a folder of POM XML files — the offline quality feedback loop.…

### Community 60 - "Src Knowledge Core"
Cohesion: 0.50
Nodes (4): Card Recipe, Accent Card Recipe, Surface Card Recipe, Callout Recipe

### Community 61 - "Src Knowledge Core"
Cohesion: 0.50
Nodes (4): Visual Hierarchy, Micro Pair Recipe, Type Ramp, KPI Row Recipe

### Community 62 - "Src Knowledge Core"
Cohesion: 0.67
Nodes (3): Spacing Scale, Composition Grammar, Sizing Vocabulary

## Knowledge Gaps
- **157 isolated node(s):** `PipelinePhase`, `AmountOfText`, `ComponentKind`, `PlanReviewIssue`, `RunStatusValue` (+152 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 525 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `audit_layout()` connect `Layout Audit Tests` to `Validator & Normalizer`, `Src Agents Validator`, `Tests Unit Test`, `Tests Unit Test`, `Layout Audit Checks`, `Scripts Verify Li`, `Scripts Render Check`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `initial_state()` connect `Send` to `Src Api Run`, `API Layer & Endpoints`, `Validator & Normalizer`, `Planner & Settings Mapper`, `Critic & Visual Critic`, `Parametrize`, `Evaluator & Cost Tracking`, `LangGraph Pipeline & Routing`, `State Models & Outline Schema`, `Generator & Render Prompts`, `Case Loader & Test Utils`, `Src Agents Questionnaire`, `Src Graph Route`, `Src Agents Style`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `validator_node()` connect `Validator & Normalizer` to `Src Agents Context`, `Layout Audit Tests`, `Src Agents Validator`, `LangGraph Pipeline & Routing`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `build_graph()` (e.g. with `context_builder_node()` and `critic_node()`) actually correct?**
  _`build_graph()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `PipelinePhase`, `AmountOfText`, `ComponentKind` to the rest of the system?**
  _157 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Context Builder & Prompts` be split into smaller, more focused modules?**
  _Cohesion score 0.05194805194805195 - nodes in this community are weakly interconnected._
- **Should `API Layer & Endpoints` be split into smaller, more focused modules?**
  _Cohesion score 0.055905220288781934 - nodes in this community are weakly interconnected._