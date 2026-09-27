"""Planning v2 (Test 1 in docs/architecture-north-star.md).

brief → index_brief (code) → plan_storyline (LLM) ⇄ check_storyline (code)
      → design_slide × N (LLM + code check, parallel) → to_slide_plans (code adapter)

Numbers are never retyped between stages: the LLM refers to blocks of the brief by id,
code fills parsed tables and charts, and code checks every number against the brief.
Runs as its own graph; src/graph.py and src/state.py are untouched until M2.
"""
