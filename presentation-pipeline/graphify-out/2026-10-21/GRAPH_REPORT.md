# Graph Report - presentation-pipeline  (2026-09-24)

## Corpus Check
- 105 files · ~355,706 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2134 nodes · 4349 edges · 144 communities (91 shown, 45 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 235 edges (avg confidence: 0.84)
- Token cost: 498,299 input · 0 output

## Community Hubs (Navigation)
- Blueprints & Design Hints
- Fit-Grow Table Sizing (Node)
- FastAPI Backend
- Evaluator & Screenshots
- Layout Audit
- State & Critic
- Roadmap & Eval Runs
- Generator & LLM Client
- API Tests & Edit Sessions
- House Style & Recipes
- Case Loader & Runner
- Frontend API Models
- Repair Guidance Tests
- Graph Routing Tests
- Eval Metric Tests
- Deck Assembly Nodes
- Hint Capabilities & Nesting
- POM XML Reference
- Normalize & Validate
- Slide Edit Service
- Repairers (Compile & Visual)
- Planner Schema
- Content Model Validation
- Eval Runner
- Context Builder Tests
- List & Text Knowledge
- LangGraph Pipeline Core
- Repair Guidance
- Table Fit Tests
- XML Normalizer
- Outline Planner & Settings
- Repairer Node Tests
- Angular App Shell
- Validator Node
- Icon Name Handling
- Plan Editor UI
- Complexity Test Cases
- Full Pipeline Integration
- Questionnaire
- Attribute Selection
- Style Resolver
- Layout Sizing Tests
- Angular Dev Deps
- Angular Runtime Deps
- Angular Schematics
- Generation Service UI
- Eval Metrics
- Graph E2E Tests
- Generation Contract
- Deck Settings Form
- Shape & KPI Tile Knowledge
- Compiler Bridge
- Context Builder Prompt Rendering
- Angular Build Options
- Prompt & Progress UI
- Eval Import
- Planning Architecture Decisions
- POM Node Package
- Table Knowledge
- Slide Component Planner
- Repair & Critic Gates
- Angular Dev Config
- Critic Schemas
- Normalizer Structure Tests
- Slide Replanner Tests
- Deck Test Cases
- Angular Workspace
- Frontend Package
- Chart Knowledge
- Upstream Reference Tests
- Icon Knowledge
- Slide Replanner
- Evaluator & Deck Bugs
- GenOffice Adoption
- Phase-Based Test Cases
- Angular Prod Build
- Pyramid Knowledge
- gj-h1 Case Builder
- Blueprint Selector
- Validation Architecture
- Eval Compare
- Li Nesting Verifier
- House Style Rendering
- Generator Architecture
- Slide Review UI
- Repair Budget Design
- LLM Test Plan Cases
- Diagram Component Specs
- Base Prompt Test Cases
- Angular Architect Targets
- PPTX Merge
- export_icon_names.py
- @hirokisakabe/pom v10.3.0 (External Depe
- Regression case runner (src.runner, test
- LangSmith tracing
- Golden Fixture Regression Testing
- jasmine-core
- karma
- karma-chrome-launcher
- karma-coverage
- karma-jasmine
- tailwindcss
- Angular Frontend Application
- XTSY Quick Commerce Test Output (Layer V
- Chart-on-Dark Workaround
- conftest.py
- Any
- BaseModel
- Test Case Phase System
- DeckState Extended State Model
- Loosely Coupled Editing Architecture
- PipelineTool Base Class
- State Re-Entry Points
- XML as Source of Truth
- Element
- Component
- Component
- Fable 5.1 Market Dashboard Test
- parametrize
- presentation-pipeline
- PresentationState
- PresentationState
- SlidePlan
- PresentationState
- PresentationState
- PresentationState
- PresentationState
- PresentationState
- SlidePlan
- PresentationState
- PresentationState
- Timeline Component Spec
- Pitch Deck Test Case
- Pyramid Strategy Test Case
- Tree Org Chart Test Case
- SlidePlan

## God Nodes (most connected - your core abstractions)
1. `initial_state()` - 82 edges
2. `PresentationState` - 55 edges
3. `POM XML Reference (llm.md)` - 53 edges
4. `audit_layout()` - 51 edges
5. `normalize_xml()` - 48 edges
6. `build_contract()` - 34 edges
7. `build_graph()` - 31 edges
8. `evaluator_node()` - 26 edges
9. `validator_node()` - 24 edges
10. `PlannerSlide` - 22 edges

## Surprising Connections (you probably didn't know these)
- `find_violations()` --implements--> `INVALID_CHILD blocking code`  [EXTRACTED]
  src/compiler/content_model.py → docs/design-hint-architecture.md
- `src/compiler/derived_nodes.py` --conceptually_related_to--> `normalize_xml()`  [EXTRACTED]
  docs/roadmap-derived-components.md → src/compiler/normalizer.py
- `POM-specific prompt rules (colors, margins, enums, Td styling, dark chart wrapper)` --semantically_similar_to--> `XML normalizer`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `Variant Required for glow/outline` --semantically_similar_to--> `Icon`  [INFERRED] [semantically similar]
  src/knowledge/components/icon.yaml → llm.md
- `Glowing Dot on Dark` --semantically_similar_to--> `KPI Tile with Dot Indicator Pattern`  [INFERRED] [semantically similar]
  src/knowledge/components/shape.yaml → llm.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Deck Mode Quality Gaps** — code_review_deck_critic_accounting, code_review_deck_validation_weakness, code_flow_slide_router_node, code_flow_deck_assembler_node [EXTRACTED 1.00]
- **LLM Test Family A Base-Prompt Cases** — tests_llm_test_plan_test_plan, tests_cases_base_competitor_comparison_test_case, tests_cases_base_org_structure_test_case, tests_cases_base_process_overview_test_case, tests_cases_base_quarterly_metrics_test_case [EXTRACTED 1.00]
- **Dual-Budget Repair System** — docs_repair_budget_split_compile_repairer_strategy, docs_repair_budget_split_visual_repairer_strategy, docs_repair_budget_split_visual_repairer_node, docs_repair_budget_split_safety_rules [EXTRACTED 1.00]
- **** — tests_cases_base_revenue_trend_yaml, tests_cases_base_roadmap_yaml, tests_cases_base_strategy_statement_yaml, tests_cases_base_vague_yaml [EXTRACTED 1.00]
- **** — tests_cases_chart_and_narrative_yaml, tests_cases_chart_and_table_yaml, tests_cases_comparison_matrix_yaml, tests_cases_dark_theme_yaml, tests_cases_financial_report_yaml, tests_cases_flowchart_yaml, tests_cases_inline_formatting_yaml [EXTRACTED 1.00]
- **** — tests_cases_deck_qbr_yaml, tests_cases_deck_qbr_data_yaml, tests_cases_deck_board_update_yaml, tests_cases_deck_sales_data_yaml [INFERRED 0.85]
- **Validate-repair retry loop** — architecture_generator, architecture_validator, architecture_repairer, code_flow_route_after_validator, architecture_stall_detection [EXTRACTED 1.00]
- **Deck-mode per-slide loop** — architecture_context_builder, architecture_generator, architecture_validator, code_flow_slide_router_node, code_flow_deck_assembler_node [EXTRACTED 1.00]
- **GenOffice features adopted into the pipeline** — code_flow_questionnaire_node, code_flow_style_resolver_node, code_flow_layout_audit, code_flow_enforce_layout_variety, code_flow_data_provenance, code_flow_api_sse_stream [INFERRED 0.85]
- **Nesting enforcement defense-in-depth** — src_knowledge_core_nodes, src_knowledge_core_hint_capabilities, src_knowledge_core_icon_names, src_compiler_content_model_flatten_text_containers, src_compiler_icons_fix_icon_names, src_compiler_content_model_find_violations [EXTRACTED 1.00]
- **Sizing plan layers A/B/C** — docs_layout_sizing_plan_grammar_layer_grow_minh, docs_layout_sizing_plan_real_font_metrics, docs_layout_sizing_plan_compute_what_pom_cannot, docs_layout_sizing_plan_let_pom_allocate_principle [EXTRACTED 1.00]
- **Eval harness pipeline run -> bundle -> import -> compare** — scripts_eval_run, docs_session_kickoff_eval_bundle, scripts_eval_import, scripts_eval_compare, scripts_eval_metrics [EXTRACTED 1.00]
- **Knowledge YAML components restate llm.md POM reference** — llm_pom_xml_reference, src_knowledge_components_chart_chart_component, src_knowledge_components_icon_icon_component, src_knowledge_components_list_list_component, src_knowledge_components_pyramid_pyramid_component, src_knowledge_components_shape_shape_component, src_knowledge_components_table_table_component, src_knowledge_components_text_text_component [EXTRACTED 1.00]
- **Inline formatting valid in Text, Li and Td** — llm_inline_formatting, llm_text, llm_li, llm_td [EXTRACTED 1.00]
- **Contrast/visibility rules the compiler won't flag** — src_knowledge_components_chart_black_axis_text, src_knowledge_components_pyramid_text_contrast_rule, src_knowledge_components_table_explicit_td_styling [INFERRED 0.75]
- **Card styling system** — src_knowledge_core_design_language_card_recipe, src_knowledge_core_design_language_accent_stripe_card, src_knowledge_core_design_language_rounded_card, src_knowledge_core_hint_capabilities_treatment_accent_border, src_knowledge_core_hint_capabilities_treatment_lift, llm_per_side_border [INFERRED 0.85]
- **Generator prompt references (blueprints, golden examples, design language, hints)** — src_knowledge_core_blueprints_blueprint_library, src_knowledge_core_golden_examples_golden_examples, src_knowledge_core_design_language, src_knowledge_core_hint_capabilities [INFERRED 0.75]
- **Table treatment and styling rules** — src_knowledge_core_hint_capabilities_kind_table, src_knowledge_core_hint_capabilities_treatment_cell_fill, src_knowledge_core_design_language_table_styling, src_knowledge_core_hint_capabilities_composition_rule [INFERRED 0.75]
- **Gate deck eval cases (user prompts 2026-09-23)** — tests_cases_gate_deck_agency_takeover_gate_deck_agency_takeover_case, tests_cases_gate_deck_cheffin_audit_gate_deck_cheffin_audit_case, tests_cases_gate_deck_xtsy_qcomm_gate_deck_xtsy_qcomm_case [EXTRACTED 1.00]
- **Held-out planner routing/disambiguation eval cases** — tests_cases_eval_categorized_list_routing_eval_categorized_list_routing_case, tests_cases_eval_chart_vs_kpi_disambiguation_eval_chart_vs_kpi_disambiguation_case, tests_cases_eval_table_vs_kpi_disambiguation_eval_table_vs_kpi_disambiguation_case [INFERRED 0.85]
- **Core knowledge YAML injected into generator prompt** — src_knowledge_core_house_style_house_style, src_knowledge_core_recipes_recipes, src_knowledge_core_validation_validation_rules, src_knowledge_core_nodes_node_allowlist [INFERRED 0.85]

## Communities (144 total, 45 thin omitted)

### Community 0 - "Blueprints & Design Hints"
Cohesion: 0.06
Nodes (84): alignSelf, borderRadius, Common Attributes (box model), grow (flex-grow ratio), Layer-only attributes (x, y), minW/maxW/minH/maxH, padding / margin dot notation, position / offsets (+76 more)

### Community 1 - "Fit-Grow Table Sizing (Node)"
Cohesion: 0.06
Nodes (73): AGENTS.md agent context, llm.md upstream POM XML reference, Phase 1 grow/minH sizing grammar, Phase 5 Step 3 table sizing, POM compiler @hirokisakabe/pom v10.3.0, render_check offline re-render script, Roadmap: derived components (Phases 0-6), LangGraph presentation pipeline (+65 more)

### Community 2 - "FastAPI Backend"
Cohesion: 0.06
Nodes (72): Enum, FileResponse, get, post, put, _build_event(), _cleanup_old_runs(), ComponentPlanPayload (+64 more)

### Community 3 - "Evaluator & Screenshots"
Cohesion: 0.06
Nodes (65): Backend, _build_step_summary(), _compute_cost(), evaluator_node(), _generate_final_screenshots(), Any, PresentationState, Evaluator agent — mechanical scoring and run manifest. No LLM. Computes: -… (+57 more)

### Community 4 - "Layout Audit"
Cohesion: 0.06
Nodes (64): _compile(), main(), Path, Render + audit a folder of POM XML files — the offline quality feedback loop.…, audit_layout(), _check_band_height_sum(), _check_col_widths(), _check_font_sizes() (+56 more)

### Community 5 - "State & Critic"
Cohesion: 0.07
Nodes (59): compute_critic_score(), _constrain_round2_strategy(), _critic_inner(), critic_node(), Any, Critic agent — visual quality gate after successful compilation. The visual…, Visual quality gate — screenshot-based review using a vision LLM., Deterministic quality score from critic output. Higher is better (max 0). (+51 more)

### Community 6 - "Roadmap & Eval Runs"
Cohesion: 0.06
Nodes (65): Eval harness (eval_run / eval_import / eval_compare / eval_metrics), Eval tables-check (Phase 2 baseline), Golden target gj-h1, Phase 0 quality baseline, Phase 2 deterministic data-shape routing, Two-device workflow (build PC / company test PC), Design hints, nesting and icons architecture, Core nodes fixed, derived components composed around them (+57 more)

### Community 7 - "Generator & LLM Client"
Cohesion: 0.06
Nodes (55): AzureChatOpenAI, ChatOpenAI, ElicitorOutput, check_and_elicit(), _elicitor_inner(), elicitor_node(), Any, PresentationState (+47 more)

### Community 8 - "API Tests & Edit Sessions"
Cohesion: 0.07
Nodes (49): OutlinePlannerOutput, OutlineSlide, BaseModel, Pydantic models for the outline planner's structured output. The outline…, Rich outline entry for one slide — enough context for slide_component_planner., Complete deck outline from the outline planner., Any, Outline replanner — regenerates a single outline slide from user feedback. Pre-… (+41 more)

### Community 9 - "House Style & Recipes"
Cohesion: 0.05
Nodes (55): Few-Shot Over Rules Lesson, Outline Planner Rewording Backfire, Group Composition Post-Mortem, Prompt Dilution Failure, Sample Slide Output (slides(2)), Color Discipline ($tokens, no #), Data Node Sizing Rules, Design Variety Rule (+47 more)

### Community 10 - "Case Loader & Runner"
Cohesion: 0.07
Nodes (42): LogRecord, _format_table(), main(), Any, CLI runner — execute test cases and print a summary table. Usage: python -m…, Format results as an aligned ASCII table., Run test cases and return summary rows., run_cases() (+34 more)

### Community 11 - "Frontend API Models"
Cohesion: 0.09
Nodes (26): EditHistoryEntry, AmountOfText, AppView, ComponentKind, DeckSettingsSchema, EditSessionStatus, ElicitationQuestion, ElicitResponse (+18 more)

### Community 12 - "Repair Guidance Tests"
Cohesion: 0.08
Nodes (40): _cap_xml(), _collect_problems(), Keep head + tail of XML so root setup and closing tags are visible., Collect error strings from normalize_result, compile_result, and critic_result., build_error_guidance(), cap_diag_msg(), is_stalled(), Strip enum listings and hard-cap length so no diagnostic bloats the prompt. (+32 more)

### Community 13 - "Graph Routing Tests"
Cohesion: 0.10
Nodes (35): Route to planning pipeline, questionnaire, or skip directly to generation., route_after_critic(), route_after_slide_router(), route_after_start(), route_after_validator(), _mock_visual_critic_pass(), _multi_slide_state(), Tests for the LangGraph pipeline with stub agents. (+27 more)

### Community 14 - "Eval Metric Tests"
Cohesion: 0.07
Nodes (27): fixture, invented_numbers(), _numbers(), pattern_match(), Text boxes whose wrapped text (~0.5 em per character, 1.2 line height) needs at…, Numbers with ≥2 digits, thousands separators dropped ("10,332" → "10332")., Numbers shown on the slide (text, chart values, diagram labels) that appear…, Multiset overlap of card patterns: sum(min) / sum(max). 1.0 = same mix. (+19 more)

### Community 15 - "Deck Assembly Nodes"
Cohesion: 0.10
Nodes (32): deck_assembler_node(), _extract_slide_block(), _extract_theme(), Any, Path, Extract the <Theme .../> element from XML., Extract the <Slide>...</Slide> block from XML., Merge per-slide PPTXs at the ZIP level. Returns compile_result or None. (+24 more)

### Community 16 - "Hint Capabilities & Nesting"
Cohesion: 0.09
Nodes (26): Defense-in-depth nesting enforcement, hint_scopes(), _kind(), load_capabilities(), planner_capabilities_section(), Any, Design-hint capabilities — what a visual-intent may ask for, per component…, One line per kind: the treatment intents it supports, plus what it must never… (+18 more)

### Community 17 - "POM XML Reference"
Cohesion: 0.12
Nodes (31): backgroundGradient, Build Diagnostics, Chart, ChartDataPoint, ChartSeries, Child Element Tag Reference, Col, Common Node Attributes (+23 more)

### Community 18 - "Normalize & Validate"
Cohesion: 0.12
Nodes (29): assemble_deck_xml(), Deck multi-slide nodes — slide_router and deck_assembler. slide_router: saves…, Combine per-slide XML into one normalized multi-slide POM document. Extracts…, ensure_single_theme(), normalize_xml(), pre_validate(), Remove every <Theme> element (self-closing, multiline, or paired) from xml., Guarantee exactly one top-level <Theme>. Strips any <Theme> the LLM emitted… (+21 more)

### Community 19 - "Slide Edit Service"
Cohesion: 0.11
Nodes (23): _call_edit_llm(), _call_repair_llm(), edit_slide_xml(), Any, Path, Slide edit service — LLM-powered XML editing with mini repair loop. Takes user…, Fix compile errors with the shared tier-1 patch prompt. Reuses the main…, Apply a user's NL edit to a slide XML, validate, and repair if needed. Returns… (+15 more)

### Community 20 - "Repairers (Compile & Visual)"
Cohesion: 0.13
Nodes (28): build_patch_prompts(), _build_repair_context(), _call_llm_and_return(), _choose_strategy(), _get_compile_diags(), _get_pre_issues(), _plan_to_outline_slide(), Any (+20 more)

### Community 21 - "Planner Schema"
Cohesion: 0.17
Nodes (27): PlannerComponent, PlannerSlide, BaseModel, Pydantic models for the per-slide planner's structured LLM output. PlannerSlide…, Plan for a single slide., One component the slide should contain, with its own content data., compute_provenance(), Any (+19 more)

### Community 22 - "Content Model Validation"
Cohesion: 0.12
Nodes (25): Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.…, content_model(), find_violations(), flatten_text_containers(), nesting_compile_failure(), Any, POM content model — which children each node may contain. Single source of…, Collapse <Td>/<Li> bodies that contain layout/leaf nodes into plain text. Only… (+17 more)

### Community 23 - "Eval Runner"
Cohesion: 0.17
Nodes (26): aggregate(), brief_of(), _copy_slides(), evaluate_case(), evaluate_fixtures(), _git_commit(), main(), make_bundle() (+18 more)

### Community 24 - "Context Builder Tests"
Cohesion: 0.12
Nodes (26): _build_default_plan(), context_builder_node(), _detect_components_from_text(), Select POM nodes needed for the given component kinds., Extract component kinds by scanning text for keywords., Build a SlidePlan from test_case components, intent detection, or fallback., LangGraph node: build contract from slide_plans[current_slide_index]., _select_nodes() (+18 more)

### Community 25 - "List & Text Knowledge"
Cohesion: 0.11
Nodes (25): Inline Formatting Tags (B/I/A/U/S/Sub/Sup/Mark/Span), Number + Small Unit KPI Numeral, Li, Ol (Numbered List), Span, Ul (Bullet List), Capitalized POM Tags (not HTML), No Nested Ul in Li (flat lists) (+17 more)

### Community 26 - "LangGraph Pipeline Core"
Cohesion: 0.16
Nodes (24): Send, build_graph(), _elicitation_wait_node(), fan_out_slide_plans(), placeholder_node(), Any, LangGraph pipeline definition. Hierarchical planning topology: START →…, If elicitation is needed and no answers yet, suspend; else proceed. (+16 more)

### Community 27 - "Repair Guidance"
Cohesion: 0.13
Nodes (24): error_signatures(), _extract_attr_from_error(), _extract_nodes_from_errors(), _extract_tag_from_error(), _find_node_attrs(), _format_attrs(), _load_knowledge_yaml(), needs_regeneration() (+16 more)

### Community 28 - "Table Fit Tests"
Cohesion: 0.15
Nodes (23): Px of table rows past their frame, summed over the slide's tables: POM flex-…, table_spill(), _compile(), parametrize, Path, Phase 5 Step 3 — fit-grow sizes a Table without h from its text (LLM-free, real…, POM's Td default is 18 px, bigger than the 14 px body text: fit-grow writes 14…, A blank cell (the normalizer fills empty <Td> with a space) is counted; filled… (+15 more)

### Community 29 - "XML Normalizer"
Cohesion: 0.11
Nodes (22): Match, _drop_attr_conflicts(), _expand_border_shorthand(), _fix_pyramid_block(), _fix_pyramids(), _fix_structure(), _pad_table_columns(), _perceived_brightness() (+14 more)

### Community 30 - "Outline Planner & Settings"
Cohesion: 0.16
Nodes (20): OutlinePlannerOutput, _get_constraints(), outline_planner_node(), Any, Outline planner agent — produces the deck skeleton (replaces planner.py). Takes…, Parse DeckSettings dict → constraints dict for prompt injection., Plan the deck outline using an LLM with structured output., DeckSettings (+12 more)

### Community 31 - "Repairer Node Tests"
Cohesion: 0.23
Nodes (22): Choose a repair strategy, build the prompt, call the LLM, update state., repairer_node(), _make_state(), _mock_llm(), _mock_replan(), patch, Set up mocks for the REGENERATE path (plan_single_slide + build_contract)., Regression: a recurring compiler diagnostic must be recognised as a stall. (+14 more)

### Community 32 - "Angular App Shell"
Cohesion: 0.12
Nodes (11): AppComponent, Component, appConfig, ElicitationFormComponent, Component, LayoutComponent, Component, ProgressViewComponent (+3 more)

### Community 33 - "Validator Node"
Cohesion: 0.17
Nodes (21): normalize_and_compile(), Any, Path, Normalize + compile check. Returns (ok, compile_result). Used by the visual…, Run the normalize → validate → compile pipeline on current_xml., validator_node(), initial_state(), Any (+13 more)

### Community 34 - "Icon Name Handling"
Cohesion: 0.17
Nodes (19): canonical_icon_name(), fix_icon_names(), Icon names — keep every <Icon name> inside POM's real icon set. Source of…, Lucide slug spelling: kebab-case, lowercase., Returns (xml, renamed [(old, new)], removed [name]). Other markup is untouched., valid_icon_names(), parametrize, skipif (+11 more)

### Community 35 - "Plan Editor UI"
Cohesion: 0.13
Nodes (4): emptyOutlineSlide(), PlanEditorComponent, Component, OutlineSlide

### Community 36 - "Complexity Test Cases"
Cohesion: 0.12
Nodes (19): Complexity Spectrum Testing, Weight Hierarchy Design Pattern, KPI Row Test Case, Matrix Prioritization Test Case, Maximal Density Test Case, Minimal Statement Test Case, Mixed Chart-Matrix Test Case, Mixed Executive Slide Test Case (+11 more)

### Community 37 - "Full Pipeline Integration"
Cohesion: 0.16
Nodes (17): PlanReviewerOutput, PlanReviewIssue, BaseModel, Pydantic models for the plan reviewer agent's structured output., _make_gen_llm(), _make_screenshot_mock(), parametrize, patch (+9 more)

### Community 38 - "Questionnaire"
Cohesion: 0.17
Nodes (17): _ask(), _load_palette_names(), Any, questionnaire_node(), Pre-generation questionnaire — collects audience/style/focus context. Presents…, Collect audience context via interactive CLI questions., Return [(name, tone), ...] from palettes.yaml, light first then dark., Print numbered menu and collect user choice. Returns the selected option. (+9 more)

### Community 39 - "Attribute Selection"
Cohesion: 0.18
Nodes (18): _load_yaml(), Build per-node attribute lists for only the nodes we selected., Select only notes relevant to the components in this slide. When has_grammar is…, _select_attributes(), _select_notes(), Icon gets its node-specific attributes plus size attrs., shadow and backgroundGradient are in common box attrs for layout/content nodes., test_attributes_chart() (+10 more)

### Community 40 - "Style Resolver"
Cohesion: 0.20
Nodes (16): _load_yaml(), Any, Style resolver — loosely-coupled theme resolution. Public API:…, Resolve a theme name to a full theme dict. Returns: {name, mode, is_dark,…, LangGraph node: resolve theme and write to state., resolve_theme(), style_resolver_node(), Tests for the style resolver — theme resolution utility and graph node. (+8 more)

### Community 41 - "Layout Sizing Tests"
Cohesion: 0.16
Nodes (17): _compile(), parametrize, Path, Phase 1 sizing grammar — LLM-free: the hand-written fixtures in…, Blueprint reference_xml + golden examples — the whole slides the generator is…, Every recipe in core/recipes.yaml as the only region of a slide (comment lines…, The band list the prompt shows ([grow=N]) and the reference XML agree., _recipe_slides() (+9 more)

### Community 42 - "Angular Dev Deps"
Cohesion: 0.12
Nodes (17): @angular/cli, @angular/compiler-cli, @angular-devkit/build-angular, autoprefixer, devDependencies, @angular/cli, @angular/compiler-cli, @angular-devkit/build-angular (+9 more)

### Community 43 - "Angular Runtime Deps"
Cohesion: 0.12
Nodes (17): @angular/common, @angular/compiler, @angular/core, @angular/forms, @angular/platform-browser, @angular/router, dependencies, @angular/common (+9 more)

### Community 44 - "Angular Schematics"
Cohesion: 0.12
Nodes (17): schematics, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests (+9 more)

### Community 45 - "Generation Service UI"
Cohesion: 0.19
Nodes (4): GenerateRequest, ProgressEvent, GenerationService, Injectable

### Community 46 - "Eval Metrics"
Cohesion: 0.18
Nodes (16): card_metrics(), empty_cells(), _inside(), _is_dark(), _pattern(), Element, Path, LLM-free slide metrics read from a compiled single-slide .pptx. POM writes… (+8 more)

### Community 47 - "Graph E2E Tests"
Cohesion: 0.16
Nodes (15): compile_graph(), Return a compiled, runnable graph., _mock_screenshot_batch(), _MockBatch, _MockSlide, patch, End-to-end: the graph runs to completion with mocked LLM + compiler., End-to-end: graph runs with pre-provided slide_plans (skips planning phase). (+7 more)

### Community 48 - "Generation Contract"
Cohesion: 0.22
Nodes (16): build_contract(), _clean_list(), Any, Build a generation contract for one slide from its plan. Args: slide_plan: The…, _estimate_tokens(), _make_plan(), Rough token estimate: ~4 chars per token for English., 6 components: grammar + recipes + shrink checklist. (+8 more)

### Community 49 - "Deck Settings Form"
Cohesion: 0.19
Nodes (5): DeckSettingsFormComponent, Component, DeckSettings, DeckSettingsField, DeckSettingsFieldOption

### Community 50 - "Shape & KPI Tile Knowledge"
Cohesion: 0.16
Nodes (15): Arrow Connector, ARROW_REF_NOT_FOUND / NOT_CONNECTABLE, Image, KPI Tile with Dot Indicator Pattern, Leaf Rotation (rotate), Shape, Text, Text Effects (glow/outline) (+7 more)

### Community 51 - "Compiler Bridge"
Cohesion: 0.22
Nodes (13): RuntimeError, compile_xml(), CompilerError, _parse_result(), Any, Path, Subprocess bridge to compile-pom.js (src/node/). The Node script writes…, Run parseXml-only validation (no PPTX generation). Returns a CompileResult dict… (+5 more)

### Community 52 - "Context Builder Prompt Rendering"
Cohesion: 0.15
Nodes (14): _all_recipes(), _build_node_attributes(), _build_node_hierarchy(), _load_golden_examples(), Context builder agent — assembles knowledge base into a generation contract.…, Render a compact parent -> children map for the nodes on this slide. Extracts…, node name -> node-specific attributes from nodes.yaml., Load core/golden-examples.yaml (cached). (+6 more)

### Community 53 - "Angular Build Options"
Cohesion: 0.19
Nodes (14): options, assets, browser, index, outputPath, polyfills, scripts, styles (+6 more)

### Community 54 - "Prompt & Progress UI"
Cohesion: 0.19
Nodes (9): PromptFormComponent, PIPELINE_PHASES, PipelinePhase, PROGRESS_RANGES, SLIDE_COUNT_TO_THRESHOLD, STEP_LABELS, THEME_PALETTES, CriticMode (+1 more)

### Community 55 - "Eval Import"
Cohesion: 0.25
Nodes (13): import_bundle(), main(), pick_reviews(), Path, Import an emailed eval bundle on the build device. python -m…, (case folder, slide index): failed slides first, then lowest card fill., Recompute the pptx-based metrics with the current eval_metrics (deterministic…, Extract, render, and merge into docs/eval/<label>/ — cases from earlier bundles… (+5 more)

### Community 56 - "Planning Architecture Decisions"
Cohesion: 0.20
Nodes (12): Layout archetype system (d2b75b6), Context Builder node (mechanical), Planner node (LLM), Data provenance (user/sample), _enforce_layout_variety, Layout Variety Enforcement Discarded by Context Builder, Component-based planning (no archetypes), Component vocabulary (14 kinds) (+4 more)

### Community 57 - "POM Node Package"
Cohesion: 0.17
Nodes (11): @hirokisakabe/pom, dependencies, @hirokisakabe/pom, description, main, name, private, scripts (+3 more)

### Community 58 - "Table Knowledge"
Cohesion: 0.21
Nodes (12): Td, Tr, Col, Col width (not w) Exception, Every Td Needs backgroundColor + color, First Tr as Header (no Th), Ragged Rows Pitfall, Right-align Numeric Columns (+4 more)

### Community 59 - "Slide Component Planner"
Cohesion: 0.29
Nodes (11): _filter_supplied_content_for_slide(), plan_single_slide(), Any, Slide component planner — plans ONE slide in detail (fan-out target). Called…, Return subset of supplied_content relevant to this slide's key_messages., Plan one slide and return a SlidePlan TypedDict. Can be called directly (e.g.…, Plan all slides sequentially in a single node (SERIALIZE_SLIDES=True path)., Plan ONE slide (receives specific slide via Send() state injection). The… (+3 more)

### Community 60 - "Repair & Critic Gates"
Cohesion: 0.22
Nodes (11): Known pre-existing unit-test failures (4), Visual critic quality gate, Repair guidance (error -> fix instruction), Repairer node (escalating repair), Stall detection (error-signature overlap), PATCH / REGENERATE repair strategy, route_after_validator, Fail-Open Visual Critic on Fragile Path (+3 more)

### Community 61 - "Angular Dev Config"
Cohesion: 0.18
Nodes (11): serve, development, buildTarget, extractLicenses, optimization, sourceMap, proxyConfig, builder (+3 more)

### Community 62 - "Critic Schemas"
Cohesion: 0.24
Nodes (10): CriticIssue, CriticOutput, BaseModel, Pydantic models for the critic's structured LLM output. Used with…, One issue found by the critic., Complete critic review output., One issue found by the visual critic — includes repair context., Complete visual critic review output — drives the repair loop. (+2 more)

### Community 63 - "Normalizer Structure Tests"
Cohesion: 0.27
Nodes (10): parametrize, skipif, Deterministic structure fixes in normalize_xml — each input below failed POM…, All cases as one deck (one node spawn): before normalize each fails, after it…, _slide(), test_attr_markup_is_stripped_and_bare_lt_escaped(), test_border_shorthand_becomes_per_side_borders(), test_every_fixed_case_compiles() (+2 more)

### Community 64 - "Slide Replanner Tests"
Cohesion: 0.33
Nodes (9): patch, Tests for the slide replanner's two-tier gate., Feedback that only mentions kinds already on the slide never triggers a replan., _slide_plan(), test_resolve_slide_plan_empty_theme_info_returns_empty_contract(), test_tier0_no_new_kind_skips_replan(), test_tier0_removal_feedback_skips_replan(), test_tier2_new_kind_triggers_replan() (+1 more)

### Community 65 - "Deck Test Cases"
Cohesion: 0.22
Nodes (10): Family B — Deck Tests, Supplied Data Test Pattern, Deck Board Update Test Case, Deck Minimal 2-Slide Test Case, Deck Product Launch Data Test Case, Deck Product Launch Test Case, Deck QBR Data Test Case, Deck QBR Test Case (+2 more)

### Community 66 - "Angular Workspace"
Cohesion: 0.20
Nodes (9): prefix, projectType, root, sourceRoot, newProjectRoot, projects, frontend, $schema (+1 more)

### Community 67 - "Frontend Package"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, ng, start, test, watch (+1 more)

### Community 68 - "Chart Knowledge"
Cohesion: 0.24
Nodes (10): Theme (Design Tokens), $token Color Reference, Black Axis Text Constraint, chartColors Literal Hex Rule, Chart Component Knowledge (chart.yaml), $chartSurface Wrapper Card, Chart Requires Explicit Pixel h, Full Palette for Distinguishable Bars (+2 more)

### Community 69 - "Upstream Reference Tests"
Cohesion: 0.22
Nodes (8): _llm_md_examples(), parametrize, skipif, llm.md (POM's own reference) is the audit source for our knowledge — not a…, All examples compiled as one deck (one node spawn); diagnostics name the…, test_every_llm_md_example_compiles_after_normalize(), test_table_cell_border_zero_is_valid_and_kept(), test_zero_strokes_removed_as_a_group()

### Community 70 - "Icon Knowledge"
Cohesion: 0.28
Nodes (9): Icon, Lucide Icon Library, Svg, core/icon-names.txt, Icon Component Knowledge (icon.yaml), Recommended Business Icon Names, Icon Self-Closing Leaf, Use size not w/h (+1 more)

### Community 71 - "Slide Replanner"
Cohesion: 0.33
Nodes (8): _merge_content_data(), Any, Slide replanner — decides whether an edit needs a richer SlidePlan. Feedback on…, Keep original values for existing keys; only take new keys from the replan. The…, Convert an existing SlidePlan to a minimal OutlineSlide for re-planning.…, Return (possibly-updated slide_plan, generation contract) for an edit. Degrades…, resolve_slide_plan(), _slide_plan_to_outline_slide()

### Community 72 - "Evaluator & Deck Bugs"
Cohesion: 0.25
Nodes (8): Evaluator node (scoring + manifest), run-manifest.json, deck_assembler_node, route_after_critic, slide_router_node, Deck Mode Critic Result Lost (HIGH Bug), Assembled Deck Gets Weaker Validation (PARTLY ADDRESSED), Model pricing (gpt-4.1 family)

### Community 73 - "GenOffice Adoption"
Cohesion: 0.25
Nodes (8): questionnaire_node, route_after_start, style_resolver_node, Core hook narrative anchor, GenOffice (genspark-ai) slides-skill, Phase 7 implementation order (7.1-7.8), Pre-generation questionnaire, Dedicated style resolver / style skill

### Community 74 - "Phase-Based Test Cases"
Cohesion: 0.32
Nodes (8): Phase-Based Test System, Chart and Narrative Test Case, Chart and Table Test Case, Comparison Matrix Test Case, Dark Theme Test Case, Financial Report Test Case, Flowchart Test Case, Inline Formatting Test Case

### Community 75 - "Angular Prod Build"
Cohesion: 0.25
Nodes (8): build, builder, configurations, defaultConfiguration, production, budgets, buildTarget, outputHashing

### Community 76 - "Pyramid Knowledge"
Cohesion: 0.32
Nodes (8): Pyramid, PyramidLevel, Pyramid direction up/down, Pyramid fontSize Scaling by Level Count, Pyramid Height Formula (52 x levels + 20), Pyramid Component Knowledge (pyramid.yaml), Per-level textColor Contrast Rule, w=max Grows Height Pitfall

### Community 77 - "gj-h1 Case Builder"
Cohesion: 0.32
Nodes (7): build_case(), main(), Element, Regenerate tests/cases/gj-h1-regen.yaml from the golden gj-h1 deck (DECIDE…, slide_content(), _text(), test_gj_h1_case_matches_golden_deck()

### Community 78 - "Blueprint Selector"
Cohesion: 0.39
Nodes (7): _load_blueprints(), Any, Blueprint selector — deterministic matching of slide plans to blueprints. No…, Score a blueprint against the slide plan. Higher = better match., Pick the best blueprint for a slide plan. Returns the full blueprint dict (with…, _score_blueprint(), select_blueprint()

### Community 79 - "Validation Architecture"
Cohesion: 0.29
Nodes (7): Design hints, nesting and icons, Compiler bridge (Python subprocess -> Node), Validator node (normalize -> parseXml -> buildPptx), XML normalizer, audit_layout (layout_audit.py), Speaker Notes Captured Then Thrown Away (HIGH Bug), Post-generation layout audit

### Community 80 - "Eval Compare"
Cohesion: 0.43
Nodes (6): compare(), _delta(), main(), _per_case(), Compare two evals: headline metrics and per-case first-pass / fill. python -m…, Case name → first-pass share, mean fill and golden match, pooled over repeats.

### Community 81 - "Li Nesting Verifier"
Cohesion: 0.48
Nodes (6): _compile(), _count_icons_in_pptx(), main(), Path, Verify that the content model (INVALID_CHILD) catches silently-stripped block…, Count icon/image references in the PPTX slide XML.

### Community 82 - "House Style Rendering"
Cohesion: 0.29
Nodes (7): _fmt_house_style_value(), Render one house-style.yaml value (str / list / dict) as prompt text., Render core/house-style.yaml into a compact prompt block (cached)., _render_house_style(), test_render_house_style_has_core_sections(), test_render_house_style_is_not_a_slide(), test_render_house_style_teaches_grow_not_pixel_budgets()

### Community 83 - "Generator Architecture"
Cohesion: 0.33
Nodes (6): Generation contract, Generator node (LLM), Tiered prompt assembly (minimal/standard/dense), Maximal-Content Truncation Causing Repair Drift, POM-specific prompt rules (colors, margins, enums, Td styling, dark chart wrapper), Speaker notes

### Community 85 - "Repair Budget Design"
Cohesion: 0.33
Nodes (6): Compile Repairer Strategy Decision, Repair Budget Split Design, Repair Safety Rules, Separate Budgets with Safe Discard, Visual Repairer Node, Visual Repairer Strategy Decision

### Community 86 - "LLM Test Plan Cases"
Cohesion: 0.33
Nodes (6): Tree Component (POM), Test Case: Competitor Comparison, Test Case: Org Structure, Test Case: Process Overview, Test Case: Quarterly Metrics, LLM Test Plan (Planner & Generator)

### Community 87 - "Diagram Component Specs"
Cohesion: 0.60
Nodes (5): YAML knowledge base (src/knowledge), Drawing Component Spec (Layer/Line/Arrow/Svg), Flow Component Spec (Flowchart), Matrix Component Spec (2x2 Grid), ProcessArrow Component Spec

### Community 88 - "Base Prompt Test Cases"
Cohesion: 0.40
Nodes (5): Family A — Base Prompt Tests, Base Revenue Trend Test Case, Base Roadmap Test Case, Base Strategy Statement Test Case, Base Vague Test Case

### Community 89 - "Angular Architect Targets"
Cohesion: 0.40
Nodes (5): extract-i18n, test, builder, architect, builder

### Community 90 - "PPTX Merge"
Cohesion: 0.40
Nodes (4): merge_pptx_files(), Path, ZIP-level merge of single-slide POM PPTX files. Each POM-compiled PPTX has…, Merge single-slide PPTX files into one multi-slide PPTX. Uses the first file as…

### Community 92 - "@hirokisakabe/pom v10.3.0 (External Depe"
Cohesion: 0.67
Nodes (3): compile-pom.js (POM Compiler Wrapper), @hirokisakabe/pom v10.3.0 (External Dependency), presentation-mvp-compiler (npm package)

## Ambiguous Edges - Review These
- `Layout archetype system (d2b75b6)` → `Component-based planning (no archetypes)`  [AMBIGUOUS]
  AGENTS.md · relation: conceptually_related_to

## Knowledge Gaps
- **195 isolated node(s):** `PipelinePhase`, `EditHistoryEntry`, `AmountOfText`, `ComponentKind`, `PlanReviewIssue` (+190 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 693 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Layout archetype system (d2b75b6)` and `Component-based planning (no archetypes)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `initial_state()` connect `Validator Node` to `FastAPI Backend`, `Evaluator & Screenshots`, `State & Critic`, `Generator & LLM Client`, `Case Loader & Runner`, `Repair Guidance Tests`, `Graph Routing Tests`, `Normalize & Validate`, `Planner Schema`, `Content Model Validation`, `Eval Runner`, `Context Builder Tests`, `LangGraph Pipeline Core`, `Outline Planner & Settings`, `Repairer Node Tests`, `Full Pipeline Integration`, `Questionnaire`, `Style Resolver`, `Graph E2E Tests`, `Generation Contract`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `knowledge/core/hint-capabilities.yaml` connect `Blueprints & Design Hints` to `Hint Capabilities & Nesting`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `PresentationState` (e.g. with `_build_default_plan()` and `context_builder_node()`) actually correct?**
  _`PresentationState` has 38 INFERRED edges - model-reasoned connections that need verification._
- **What connects `PipelinePhase`, `EditHistoryEntry`, `AmountOfText` to the rest of the system?**
  _195 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Blueprints & Design Hints` be split into smaller, more focused modules?**
  _Cohesion score 0.05669050051072523 - nodes in this community are weakly interconnected._
- **Should `Fit-Grow Table Sizing (Node)` be split into smaller, more focused modules?**
  _Cohesion score 0.05647517039922103 - nodes in this community are weakly interconnected._