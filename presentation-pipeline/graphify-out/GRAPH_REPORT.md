# Graph Report - presentation-pipeline  (2026-09-19)

## Corpus Check
- 10 files · ~110,384 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1439 nodes · 2958 edges · 104 communities (71 shown, 25 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 121 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- **C0**: API Endpoints & Models
- **C1**: Validator & Compiler Client
- **C2**: Critic Schema Types
- **C3**: Render Check Scripts
- **C4**: Evaluator Agent
- **C5**: Frontend Result View
- **C6**: Deck XML Assembler
- **C7**: Questionnaire & Planner Wiring
- **C8**: Repair Strategy Selection
- **C9**: API Test Mocks
- **C10**: Screenshot Backend
- **C11**: Critic & Pipeline State
- **C12**: Elicitor Agent
- **C13**: Repairer Execution Loop
- **C14**: CLI Runner
- **C15**: Docs & Postmortem Notes
- **C16**: Critic Unit Tests
- **C17**: Planner Schema
- **C18**: Test Case Loader
- **C19**: Repairer & Component Planner
- **C20**: Graph Routing Tests
- **C21**: POM Knowledge & House Style
- **C22**: Angular App Shell
- **C23**: Plan Editor Component
- **C24**: Context Builder Detection
- **C25**: Generator Agent
- **C26**: Slide Replanner
- **C27**: Repair Guidance Engine
- **C28**: Advanced Test Cases
- **C29**: Graph Entry & State Init
- **C30**: Outline Planner Schema
- **C31**: LLM Client Wiring
- **C32**: Context Builder Attributes
- **C33**: Pipeline Graph Tests
- **C34**: Frontend Dev Dependencies
- **C35**: Angular Core Dependencies
- **C36**: Context Builder Core
- **C37**: Architecture Documentation
- **C38**: Angular Schematics Config
- **C39**: Questionnaire Node
- **C40**: Style & Theme Resolver
- **C41**: Frontend UI Components
- **C42**: Deck Settings Form
- **C43**: Generation Service
- **C44**: Contract Build & Tokens
- **C45**: Settings Mapper
- **C46**: Knowledge & POM Wrapper
- **C47**: Angular Build Options
- **C48**: Integration Tests
- **C49**: Architecture Flow Docs
- **C50**: Repair Diagnostics
- **C51**: Node Package Config
- **C52**: Deck Test Cases
- **C53**: Angular Serve Config
- **C54**: Slide Review Component
- **C55**: Architecture Repair Docs
- **C56**: Component Knowledge Files
- **C57**: Angular Project Config
- **C58**: Frontend Package Scripts
- **C59**: Context Builder Node
- **C60**: Phase Test Cases
- **C61**: Angular Production Build
- **C62**: Base Test Family
- **C63**: POM Compiler Node
- **C64**: Screenshot Node Tools
- **C65**: Planner Unit Tests
- **C66**: Angular i18n & Test
- **C67**: Plan Reviewer Schema
- **C68**: Group Composition Postmortem
- **C69**: Regeneration Detection
- **C70**: API Mock Objects
- **C71**: Outline Slide Repair
- **C72**: Golden Test Fixtures
- **C73**: Jasmine Core
- **C74**: Karma Runner
- **C75**: Karma Chrome Launcher
- **C76**: Karma Coverage
- **C77**: Karma Jasmine
- **C78**: Tailwind CSS
- **C79**: Frontend Index HTML
- **C80**: House Style Layout Rules
- **C81**: Test Conftest Fixtures
- **C82**: Test Case Phases
- **C83**: Editing Deck State
- **C84**: Loosely Coupled Editing
- **C85**: Pipeline Tool Docs
- **C86**: Reentry Points Docs
- **C88**: Prompt Form Component
- **C90**: Fable Dashboard Test
- **C91**: Package Metadata
- **C92**: Python Dependencies
- **C93**: Context Builder Types
- **C95**: Common Attributes
- **C98**: Pitch Deck Case
- **C99**: Pyramid Strategy Case
- **C100**: Tree Org Chart Case

## God Nodes (most connected - your core abstractions)
1. `initial_state()` - 86 edges
2. `PresentationState` - 56 edges
3. `repairer_node()` - 34 edges
4. `audit_layout()` - 33 edges
5. `build_contract()` - 27 edges
6. `evaluator_node()` - 26 edges
7. `build_graph()` - 26 edges
8. `PlannerSlide` - 22 edges
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
- **Knowledge Base Drives XML Generation** — architecture_knowledge_base, src_knowledge_core_house_style_grammar, src_knowledge_core_house_style_recipes, architecture_context_builder, flow_generation_contract, architecture_generator [EXTRACTED 1.00]
- **LLM Test Family A Base-Prompt Cases** — tests_llm_test_plan_test_plan, tests_cases_base_competitor_comparison_test_case, tests_cases_base_org_structure_test_case, tests_cases_base_overstuffed_test_case, tests_cases_base_process_overview_test_case, tests_cases_base_quarterly_metrics_test_case [EXTRACTED 1.00]
- **LLM Pipeline Steps (Hierarchical Planning)** — models_elicitor_step, models_outline_planner_step, models_slide_component_planner_step, models_generator_step, models_critic_step, models_repairer_step, models_visual_critic_step, models_slide_editor_step [EXTRACTED 1.00]
- **Dual-Budget Repair System** — docs_repair_budget_split_compile_repairer_strategy, docs_repair_budget_split_visual_repairer_strategy, docs_repair_budget_split_visual_repairer_node, docs_repair_budget_split_safety_rules [EXTRACTED 1.00]
- **** — tests_cases_base_revenue_trend_yaml, tests_cases_base_risks_yaml, tests_cases_base_roadmap_yaml, tests_cases_base_strategy_statement_yaml, tests_cases_base_vague_yaml [EXTRACTED 1.00]
- **** — tests_cases_chart_and_narrative_yaml, tests_cases_chart_and_table_yaml, tests_cases_comparison_matrix_yaml, tests_cases_dark_theme_yaml, tests_cases_financial_report_yaml, tests_cases_flowchart_yaml, tests_cases_inline_formatting_yaml [EXTRACTED 1.00]
- **** — tests_cases_deck_qbr_yaml, tests_cases_deck_qbr_data_yaml, tests_cases_deck_board_update_yaml, tests_cases_deck_sales_enablement_yaml, tests_cases_deck_sales_data_yaml [INFERRED 0.85]

## Communities (104 total, 25 thin omitted)

### Community 0 - "API Endpoints & Models"
Cohesion: 0.05
Nodes (76): Enum, FileResponse, get, post, put, edit_slide_xml(), Apply a user's NL edit to a slide XML, validate, and repair if needed. Returns…, _build_event() (+68 more)

### Community 1 - "Validator & Compiler Client"
Cohesion: 0.06
Nodes (56): RuntimeError, normalize_and_compile(), Any, Path, Normalize + compile check. Returns (ok, compile_result). Used by the visual…, Run the normalize → validate → compile pipeline on current_xml., validator_node(), compile_xml() (+48 more)

### Community 2 - "Critic Schema Types"
Cohesion: 0.06
Nodes (41): CriticIssue, CriticOutput, BaseModel, Pydantic models for the critic's structured LLM output. Used with…, One issue found by the critic., Complete critic review output., One issue found by the visual critic — includes repair context., Complete visual critic review output — drives the repair loop. (+33 more)

### Community 3 - "Render Check Scripts"
Cohesion: 0.08
Nodes (46): Element, _compile(), _find_soffice(), main(), Path, Render + audit a folder of POM XML files — the offline quality feedback loop.…, _to_pdf(), audit_layout() (+38 more)

### Community 4 - "Evaluator Agent"
Cohesion: 0.10
Nodes (40): _build_step_summary(), _compute_cost(), evaluator_node(), _generate_final_screenshots(), Any, Evaluator agent — mechanical scoring and run manifest. No LLM. Computes: -…, Generate screenshots from the final assembled PPTX. Always (re)renders from…, Write run-manifest.json to output/runs/{run_id}/. (+32 more)

### Community 5 - "Frontend Result View"
Cohesion: 0.10
Nodes (24): AmountOfText, AppView, ComponentKind, DeckSettingsSchema, EditSessionStatus, ElicitationQuestion, ElicitResponse, EvaluationSummary (+16 more)

### Community 6 - "Deck XML Assembler"
Cohesion: 0.11
Nodes (32): assemble_deck_xml(), deck_assembler_node(), _extract_slide_block(), _extract_theme(), Any, Extract the <Theme .../> element from XML., Extract the <Slide>...</Slide> block from XML., Combine all completed slide XMLs into one multi-slide POM document and compile. (+24 more)

### Community 7 - "Questionnaire & Planner Wiring"
Cohesion: 0.11
Nodes (29): Pre-generation questionnaire — collects audience/style/focus context. Presents…, Plan all slides sequentially in a single node (SERIALIZE_SLIDES=True path)., Plan ONE slide (receives specific slide via Send() state injection). The…, slide_component_planner_node(), slide_plan_serial_node(), Style resolver — loosely-coupled theme resolution. Public API:…, Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.…, build_graph() (+21 more)

### Community 8 - "Repair Strategy Selection"
Cohesion: 0.09
Nodes (32): _build_repair_context(), _cap_xml(), _choose_strategy(), Build error context for the slide component planner during REGENERATE., Pick PATCH or REGENERATE for this attempt. The loop is "PATCH, REGENERATE…, Keep head + tail of XML so root setup and closing tags are visible., build_error_guidance(), is_stalled() (+24 more)

### Community 9 - "API Test Mocks"
Cohesion: 0.13
Nodes (27): SlideEditResult, _make_elicitor_llm(), _make_gen_llm(), _make_outline_llm(), _make_plan_reviewer_llm(), _make_slide_component_llm(), _make_sse_generate_request(), _parse_sse_events() (+19 more)

### Community 10 - "Screenshot Backend"
Cohesion: 0.13
Nodes (28): Backend, _check_screenshot_backend(), _kill_new_powerpnt_processes(), _kill_pids(), _list_powerpnt_pids(), PPTX-to-PNG screenshot service. Primary: Node.js script (screenshot-pom.js)…, Persist a failure record to disk. Log lines get missed; a file doesn't., PIDs of currently running POWERPNT.EXE processes (Windows only). (+20 more)

### Community 11 - "Critic & Pipeline State"
Cohesion: 0.14
Nodes (26): Critic agent — visual quality gate after successful compilation. The visual…, Take screenshot and run visual critic. Returns (issues, screenshot_path, usage,…, _run_visual_review(), AttemptRecord, CompileResult, ComponentPlan, CriticResult, DeckPlan (+18 more)

### Community 12 - "Elicitor Agent"
Cohesion: 0.12
Nodes (22): check_and_elicit(), elicitor_node(), Any, Elicitor agent — detects vague queries and generates clarifying questions.…, Check if context is sufficient and return clarifying questions if not. Pure LLM…, Graph node: run elicitor and write results to state. If elicitation_answers are…, ElicitationQuestion, ElicitorOutput (+14 more)

### Community 13 - "Repairer Execution Loop"
Cohesion: 0.19
Nodes (27): _call_llm_and_return(), _get_compile_diags(), _get_pre_issues(), Any, Call the repairer LLM and build the return dict (used by PATCH)., Choose a repair strategy, build the prompt, call the LLM, update state., repairer_node(), _make_state() (+19 more)

### Community 14 - "CLI Runner"
Cohesion: 0.12
Nodes (22): LogRecord, _format_table(), main(), Any, CLI runner — execute test cases and print a summary table. Usage: python -m…, Format results as an aligned ASCII table., Run test cases and return summary rows., run_cases() (+14 more)

### Community 15 - "Docs & Postmortem Notes"
Cohesion: 0.09
Nodes (24): Compile Repairer Strategy Decision, Repair Budget Split Design, Repair Safety Rules, Separate Budgets with Safe Discard, Visual Repairer Node, Visual Repairer Strategy Decision, Outline Planner Rewording Backfire, Critic Step Config (+16 more)

### Community 16 - "Critic Unit Tests"
Cohesion: 0.24
Nodes (21): critic_node(), Any, Visual quality gate — screenshot-based review using a vision LLM., _make_state(), _mock_batch(), _mock_visual_result(), _MockBatch, _MockSlide (+13 more)

### Community 17 - "Planner Schema"
Cohesion: 0.24
Nodes (20): PlannerComponent, PlannerSlide, BaseModel, Pydantic models for the per-slide planner's structured LLM output. PlannerSlide…, Plan for a single slide., One component the slide should contain, with its own content data., _planner_slide_to_state(), Convert PlannerSlide Pydantic model to SlidePlan TypedDict. (+12 more)

### Community 18 - "Test Case Loader"
Cohesion: 0.18
Nodes (20): case_to_state(), load_all_cases(), load_case(), Any, Path, YAML test case loader. Loads test case definitions from tests/cases/*.yaml and…, Load a single test case by name (without .yaml extension)., Load all YAML test cases from the cases directory. (+12 more)

### Community 19 - "Repairer & Component Planner"
Cohesion: 0.15
Nodes (18): build_patch_prompts(), Repairer agent — two repair strategies. PATCH: feed back failing XML + errors +…, Build the (system, user) prompts for a PATCH (in-place fix) repair. Shared by…, _filter_supplied_content_for_slide(), plan_single_slide(), Any, Slide component planner — plans ONE slide in detail (fan-out target). Called…, Return subset of supplied_content relevant to this slide's key_messages. (+10 more)

### Community 20 - "Graph Routing Tests"
Cohesion: 0.17
Nodes (20): route_after_critic(), route_after_slide_router(), _mock_visual_critic_pass(), _multi_slide_state(), Tests for the LangGraph pipeline with stub agents., Return a clean-pass 3-tuple matching run_visual_critic's signature., Create a state with 2 slide_plans (multi-slide mode)., test_graph_builds() (+12 more)

### Community 21 - "POM Knowledge & House Style"
Cohesion: 0.14
Nodes (20): POM XML Declarative Markup, XML as Source of Truth, XTSY Quick Commerce Test Output (Layer Variant), XTSY Quick Commerce Test Output, Color Discipline ($token Colors, No # Prefix), House Layout Grammar (Compositional Spec), Height Budget Rule (720px Overflow Prevention), Reusable Recipes (surface_card, hero_panel, etc.) (+12 more)

### Community 22 - "Angular App Shell"
Cohesion: 0.12
Nodes (11): AppComponent, Component, appConfig, ElicitationFormComponent, Component, LayoutComponent, Component, ProgressViewComponent (+3 more)

### Community 23 - "Plan Editor Component"
Cohesion: 0.13
Nodes (4): emptyOutlineSlide(), PlanEditorComponent, Component, OutlineSlide

### Community 24 - "Context Builder Detection"
Cohesion: 0.17
Nodes (19): _detect_components_from_text(), Select POM nodes needed for the given component kinds., Extract component kinds by scanning text for keywords., _select_nodes(), Tests for the context builder agent., Icon is a base node — always present regardless of component kinds., test_detect_components_chart(), test_detect_components_multiple() (+11 more)

### Community 25 - "Generator Agent"
Cohesion: 0.24
Nodes (19): generator_node(), Any, Render system + user prompts from the contract and slide plan., Generate POM XML via LLM using tiered prompts from the contract., _render_prompts(), _make_state(), patch, Tests for the generator agent with mocked LLM responses. (+11 more)

### Community 26 - "Slide Replanner"
Cohesion: 0.20
Nodes (18): _merge_content_data(), Any, Slide replanner — decides whether an edit needs a richer SlidePlan. Feedback on…, Keep original values for existing keys; only take new keys from the replan. The…, Convert an existing SlidePlan to a minimal OutlineSlide for re-planning.…, Return (possibly-updated slide_plan, generation contract) for an edit. Degrades…, resolve_slide_plan(), _slide_plan_to_outline_slide() (+10 more)

### Community 27 - "Repair Guidance Engine"
Cohesion: 0.17
Nodes (19): error_signatures(), _extract_attr_from_error(), _extract_nodes_from_errors(), _extract_tag_from_error(), _find_node_attrs(), _format_attrs(), _load_knowledge_yaml(), Any (+11 more)

### Community 28 - "Advanced Test Cases"
Cohesion: 0.12
Nodes (19): Complexity Spectrum Testing, Weight Hierarchy Design Pattern, KPI Row Test Case, Matrix Prioritization Test Case, Maximal Density Test Case, Minimal Statement Test Case, Mixed Chart-Matrix Test Case, Mixed Executive Slide Test Case (+11 more)

### Community 29 - "Graph Entry & State Init"
Cohesion: 0.16
Nodes (19): Send, Route to planning pipeline, questionnaire, or skip directly to generation., route_after_start(), route_after_validator(), initial_state(), Any, Create a fully-initialized starting state for the graph., A user-edited outline (e.g. via PUT /plan/{run_id}/outline) skips elicitor +… (+11 more)

### Community 30 - "Outline Planner Schema"
Cohesion: 0.19
Nodes (16): OutlinePlannerOutput, OutlineSlide, BaseModel, Pydantic models for the outline planner's structured output. The outline…, Rich outline entry for one slide — enough context for slide_component_planner., Complete deck outline from the outline planner., Any, Outline replanner — regenerates a single outline slide from user feedback. Pre-… (+8 more)

### Community 31 - "LLM Client Wiring"
Cohesion: 0.18
Nodes (15): AzureChatOpenAI, ChatOpenAI, _call_deck_repair_llm(), Deck multi-slide nodes — slide_router and deck_assembler. slide_router: saves…, Fix compile errors in the assembled multi-slide document, preserving all…, Generator agent — produces POM XML from the plan + contract + data. Uses tiered…, extract_usage(), get_llm() (+7 more)

### Community 32 - "Context Builder Attributes"
Cohesion: 0.18
Nodes (18): _load_yaml(), Build per-node attribute lists for only the nodes we selected., Select only notes relevant to the components in this slide. When has_grammar is…, _select_attributes(), _select_notes(), Icon gets its node-specific attributes plus size attrs., shadow and backgroundGradient are in common box attrs for layout/content nodes., test_attributes_chart() (+10 more)

### Community 33 - "Pipeline Graph Tests"
Cohesion: 0.15
Nodes (16): _run_pipeline_sync(), compile_graph(), Return a compiled, runnable graph., _mock_screenshot_batch(), _MockBatch, _MockSlide, patch, End-to-end: the graph runs to completion with mocked LLM + compiler. (+8 more)

### Community 34 - "Frontend Dev Dependencies"
Cohesion: 0.12
Nodes (17): @angular/cli, @angular/compiler-cli, @angular-devkit/build-angular, autoprefixer, devDependencies, @angular/cli, @angular/compiler-cli, @angular-devkit/build-angular (+9 more)

### Community 35 - "Angular Core Dependencies"
Cohesion: 0.12
Nodes (17): @angular/common, @angular/compiler, @angular/core, @angular/forms, @angular/platform-browser, @angular/router, dependencies, @angular/common (+9 more)

### Community 36 - "Context Builder Core"
Cohesion: 0.14
Nodes (16): Any, _all_recipes(), _build_node_attributes(), _build_node_hierarchy(), _clean_list(), _fmt_house_style_value(), Context builder agent — assembles knowledge base into a generation contract.…, Render a compact parent -> children map for the nodes on this slide. Extracts… (+8 more)

### Community 37 - "Architecture Documentation"
Cohesion: 0.15
Nodes (17): Node.js Compiler Bridge (Subprocess), Visual Critic Node (Vision LLM Quality Gate), Evaluator Node (Scoring + Manifest), LangGraph Presentation Pipeline, PresentationState TypedDict, Validator Node (3-Stage Mechanical Check), XML Normalizer (Pre-Compile Cleanup), HTTP + SSE API Entry Point (+9 more)

### Community 38 - "Angular Schematics Config"
Cohesion: 0.12
Nodes (17): schematics, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests (+9 more)

### Community 39 - "Questionnaire Node"
Cohesion: 0.17
Nodes (16): _ask(), _load_palette_names(), Any, questionnaire_node(), Collect audience context via interactive CLI questions., Return [(name, tone), ...] from palettes.yaml, light first then dark., Print numbered menu and collect user choice. Returns the selected option., Map the slide-count answer to a planner target slide count. (+8 more)

### Community 40 - "Style & Theme Resolver"
Cohesion: 0.22
Nodes (15): _load_yaml(), Any, Resolve a theme name to a full theme dict. Returns: {name, mode, is_dark,…, LangGraph node: resolve theme and write to state., resolve_theme(), style_resolver_node(), Tests for the style resolver — theme resolution utility and graph node., test_resolve_chart_colors() (+7 more)

### Community 41 - "Frontend UI Components"
Cohesion: 0.17
Nodes (10): Component, PromptFormComponent, PIPELINE_PHASES, PipelinePhase, PROGRESS_RANGES, SLIDE_COUNT_TO_THRESHOLD, STEP_LABELS, THEME_PALETTES (+2 more)

### Community 42 - "Deck Settings Form"
Cohesion: 0.19
Nodes (5): DeckSettingsFormComponent, Component, DeckSettings, DeckSettingsField, DeckSettingsFieldOption

### Community 43 - "Generation Service"
Cohesion: 0.22
Nodes (3): ProgressEvent, GenerationService, Injectable

### Community 44 - "Contract Build & Tokens"
Cohesion: 0.24
Nodes (15): build_contract(), Build a generation contract for one slide from its plan. Args: slide_plan: The…, _estimate_tokens(), _make_plan(), SlidePlan, Rough token estimate: ~4 chars per token for English., Maximal-density (6 components): grammar + recipes + shrink checklist., _render_system_prompt() (+7 more)

### Community 45 - "Settings Mapper"
Cohesion: 0.17
Nodes (14): compute_provenance(), DeckSettings, Any, BaseModel, DeckSettings — Gamma-style pre-generation form model and constraint mapping.…, Convert DeckSettings to a flat dict of planner constraints., Tag each content_data key as 'user' (from supplied_content) or 'sample'., settings_to_constraints() (+6 more)

### Community 46 - "Knowledge & POM Wrapper"
Cohesion: 0.14
Nodes (15): Table Component (POM), Tree Component (POM), Design Language Patterns, POM Document Structure, Chart-on-Dark Workaround, Theme Palette Library, compile-pom.js (POM Compiler Wrapper), @hirokisakabe/pom v10.3.0 (External Dependency) (+7 more)

### Community 47 - "Angular Build Options"
Cohesion: 0.19
Nodes (14): options, assets, browser, index, outputPath, polyfills, scripts, styles (+6 more)

### Community 48 - "Integration Tests"
Cohesion: 0.23
Nodes (13): parametrize, _make_gen_llm(), _make_screenshot_mock(), patch, Integration tests — run the full pipeline for each YAML test case. All LLM…, Pipeline runs through the full hierarchical planning pipeline., Pipeline retries on compile failure and eventually passes., Mock generator LLM that returns valid POM XML. (+5 more)

### Community 49 - "Architecture Flow Docs"
Cohesion: 0.17
Nodes (13): Context Builder Node (Mechanical), Planner Node (LLM Structured Output), Questionnaire Node (Interactive), Style Resolver Node (Theme Resolution), Layout Variety Enforcement Discarded by Context Builder, 14-Kind Component Vocabulary, Generation Contract (Knowledge Base Assembly), Component-to-POM-Node Selection Mapping (+5 more)

### Community 50 - "Repair Diagnostics"
Cohesion: 0.15
Nodes (13): _collect_problems(), Collect error strings from normalize_result, compile_result, and critic_result., cap_diag_msg(), Strip enum listings and hard-cap length so no diagnostic bloats the prompt., The Lucide icon-name INVALID_VALUE message must not pass through raw., Single-value 'expected: <tag>' in parse errors must NOT be stripped., INVALID_VALUE enum listing must not inflate the problems list., test_cap_diag_msg_preserves_parse_error_context() (+5 more)

### Community 51 - "Node Package Config"
Cohesion: 0.17
Nodes (11): @hirokisakabe/pom, dependencies, @hirokisakabe/pom, description, main, name, private, scripts (+3 more)

### Community 52 - "Deck Test Cases"
Cohesion: 0.22
Nodes (11): Family B — Deck Tests, Supplied Data Test Pattern, Deck Board Update Test Case, Deck Minimal 2-Slide Test Case, Deck Product Launch Data Test Case, Deck Product Launch Test Case, Deck QBR Data Test Case, Deck QBR Test Case (+3 more)

### Community 53 - "Angular Serve Config"
Cohesion: 0.18
Nodes (11): serve, development, buildTarget, extractLicenses, optimization, sourceMap, proxyConfig, builder (+3 more)

### Community 54 - "Slide Review Component"
Cohesion: 0.18
Nodes (5): EditHistoryEntry, SlideReviewComponent, Component, SlideEditResponse, SlideInfoReview

### Community 55 - "Architecture Repair Docs"
Cohesion: 0.22
Nodes (10): Generator Node (LLM XML Generation), Repair Guidance (Error-to-Fix Mapping), Repairer Node (PATCH/REGENERATE Strategy), Generate-Validate-Repair Retry Loop, Stall Detection (Error Signature Overlap), Tiered Jinja2 Prompt System, Conditional Routing Functions, Maximal-Content Truncation Causing Repair Drift (+2 more)

### Community 56 - "Component Knowledge Files"
Cohesion: 0.24
Nodes (10): YAML Knowledge Base, Chart Component Spec, Dark Theme Chart Axis Bug Workaround, Drawing Component Spec (Layer/Line/Arrow/Svg), Flow Component Spec (Flowchart), Ul/Ol/Li List Component Spec, Matrix Component Spec (2x2 Grid), ProcessArrow Component Spec (+2 more)

### Community 57 - "Angular Project Config"
Cohesion: 0.20
Nodes (9): prefix, projectType, root, sourceRoot, newProjectRoot, projects, frontend, $schema (+1 more)

### Community 58 - "Frontend Package Scripts"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, ng, start, test, watch (+1 more)

### Community 59 - "Context Builder Node"
Cohesion: 0.22
Nodes (10): PresentationState, _build_default_plan(), context_builder_node(), SlidePlan, Build a SlidePlan from test_case components, intent detection, or fallback., LangGraph node: build contract from slide_plans[current_slide_index]., test_context_builder_node_empty_plans(), test_context_builder_node_runs() (+2 more)

### Community 60 - "Phase Test Cases"
Cohesion: 0.32
Nodes (8): Phase-Based Test System, Chart and Narrative Test Case, Chart and Table Test Case, Comparison Matrix Test Case, Dark Theme Test Case, Financial Report Test Case, Flowchart Test Case, Inline Formatting Test Case

### Community 61 - "Angular Production Build"
Cohesion: 0.25
Nodes (8): build, builder, configurations, defaultConfiguration, production, budgets, buildTarget, outputHashing

### Community 62 - "Base Test Family"
Cohesion: 0.33
Nodes (6): Family A — Base Prompt Tests, Base Revenue Trend Test Case, Base Risks Test Case, Base Roadmap Test Case, Base Strategy Statement Test Case, Base Vague Test Case

### Community 63 - "POM Compiler Node"
Cohesion: 0.53
Nodes (5): classifyError(), compile(), printSummary(), SLIDE_SIZE, validate()

### Community 64 - "Screenshot Node Tools"
Cohesion: 0.60
Nodes (5): findExecutable(), findImageMagick(), findSoffice(), isRealImageMagick(), main()

### Community 65 - "Planner Unit Tests"
Cohesion: 0.60
Nodes (6): _make_structured_llm(), _mock_outline_output(), patch, test_outline_planner_multi_slide(), test_outline_planner_single_slide(), test_outline_planner_with_deck_settings()

### Community 66 - "Angular i18n & Test"
Cohesion: 0.40
Nodes (5): extract-i18n, test, builder, architect, builder

### Community 67 - "Plan Reviewer Schema"
Cohesion: 0.50
Nodes (4): PlanReviewerOutput, PlanReviewIssue, BaseModel, Pydantic models for the plan reviewer agent's structured output.

### Community 68 - "Group Composition Postmortem"
Cohesion: 0.50
Nodes (4): Few-Shot Over Rules Lesson, Group Composition Post-Mortem, Prompt Dilution Failure, Sample Slide Output (slides(2))

### Community 69 - "Regeneration Detection"
Cohesion: 0.50
Nodes (4): needs_regeneration(), True when the errors are structural — an in-place PATCH is unlikely to fix them…, test_needs_regeneration_local_errors_false(), test_needs_regeneration_structural()

### Community 71 - "Outline Slide Repair"
Cohesion: 0.67
Nodes (3): _plan_to_outline_slide(), Convert a SlidePlan back to a minimal OutlineSlide dict for re-planning., test_plan_to_outline_slide()

## Knowledge Gaps
- **154 isolated node(s):** `PipelinePhase`, `EditHistoryEntry`, `AmountOfText`, `ComponentKind`, `PlanReviewIssue` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 492 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `initial_state()` connect `Community 29` to `Community 0`, `Community 1`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 11`, `Community 13`, `Community 16`, `Community 17`, `Community 18`, `Community 20`, `Community 25`, `Community 33`, `Community 39`, `Community 40`, `Community 48`, `Community 50`, `Community 65`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `PresentationState` connect `Community 7` to `Community 1`, `Community 4`, `Community 6`, `Community 39`, `Community 40`, `Community 11`, `Community 12`, `Community 13`, `Community 16`, `Community 50`, `Community 19`, `Community 20`, `Community 18`, `Community 25`, `Community 29`, `Community 31`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `audit_layout()` connect `Community 3` to `Community 1`, `Community 7`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `PresentationState` (e.g. with `critic_node()` and `_run_visual_review()`) actually correct?**
  _`PresentationState` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `repairer_node()` (e.g. with `PresentationState` and `build_graph()`) actually correct?**
  _`repairer_node()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `PipelinePhase`, `EditHistoryEntry`, `AmountOfText` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05328005328005328 - nodes in this community are weakly interconnected._