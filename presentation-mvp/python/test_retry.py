"""Exercise the 3-tier retry loop without an API key.

Runs generate.run() with fake xml_providers that return broken XML in
various patterns, then checks the RetryOutcome, tier escalation, stall
detection, and AttemptRecord tracking.

    python python/test_retry.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Force retry budget to 3 for testing (before config is loaded).
os.environ.setdefault("RETRY_BUDGET", "3")

import generate  # noqa: E402
import slide_ir  # noqa: E402
from models import TokenUsage  # noqa: E402

GOOD_XML = (Path(__file__).resolve().parent.parent
            / "pom-knowledge" / "examples" / "text-slide.xml").read_text(encoding="utf-8")

# HTML contamination: <div>/<p> are structural HTML tags the pre-validator catches.
BROKEN_HTML = """<Theme surface="0F172A" accent="3B82F6" textMain="F8FAFC" textMuted="94A3B8" />
<Slide>
  <VStack w="1280" h="720" padding="64" gap="24" backgroundColor="$surface">
    <div><p>Quarterly Business Review</p></div>
    <Text fontSize="22" color="$textMuted">Body copy that should wrap.</Text>
  </VStack>
</Slide>
"""

# Same errors as BROKEN_HTML — triggers stall detection on consecutive retries.
BROKEN_HTML_SAME = """<Theme surface="0F172A" accent="3B82F6" textMain="F8FAFC" textMuted="94A3B8" />
<Slide>
  <VStack w="1280" h="720" padding="64" gap="24" backgroundColor="$surface">
    <div><p>Q3 Operating Review</p></div>
    <Text fontSize="22" color="$textMuted">Different text but same structural errors.</Text>
  </VStack>
</Slide>
"""

# Zero-dimension error: w="0" on Text.
BROKEN_ZERO = """<Theme surface="0F172A" accent="3B82F6" textMain="F8FAFC" textMuted="94A3B8" />
<Slide>
  <VStack w="1280" h="720" padding="64" gap="24" backgroundColor="$surface">
    <Text w="0" fontSize="22" color="$textMuted">Zero width.</Text>
  </VStack>
</Slide>
"""


def _provider_factory(sequence):
    calls = {"n": 0}

    def provider(_system, _user, attempt):
        idx = min(calls["n"], len(sequence) - 1)
        calls["n"] += 1
        return sequence[idx], TokenUsage(input=100, output=50)

    return provider, calls


def _run(sequence, tmp):
    ir = slide_ir.from_request("A Q3 review title slide with a short narrative")
    provider, calls = _provider_factory(sequence)
    eval_path = generate.run(
        ir,
        output_root=Path(tmp),
        dry_run=False,
        xml_provider=provider,
    )
    ev = json.loads(eval_path.read_text(encoding="utf-8"))
    return ev, calls["n"], eval_path.parent


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="pom-retry-v2-")
    failures = []
    try:
        # ── Case 1: broken then good -> recovers at tier 1 (PATCH) ──────────
        print("=" * 60)
        print("Case 1: broken -> good (tier 1 patch recovery)")
        ev, n_calls, run_dir = _run([BROKEN_HTML, GOOD_XML], tmp)
        r = ev["retry"]
        print(f"  attempted={r['attempted']} attempts={r['attempts']} "
              f"succeeded={r['succeeded']} max_tier={r['max_tier_used']} calls={n_calls}")
        if not (r["attempted"] and r["attempts"] == 1 and r["succeeded"] is True):
            failures.append("case1: expected 1 successful retry")
        if r["max_tier_used"] != 1:
            failures.append(f"case1: expected max_tier=1, got {r['max_tier_used']}")
        if not (run_dir / "response-raw-retry1.xml").exists():
            failures.append("case1: missing response-raw-retry1.xml")
        if ev["compilation"]["status"] != "success":
            failures.append("case1: final compile should be success")
        records = r.get("attempt_records", [])
        if len(records) < 2:
            failures.append(f"case1: expected >=2 attempt records, got {len(records)}")
        else:
            if records[1]["tier"] != 1:
                failures.append(f"case1: retry record should be tier 1, got {records[1]['tier']}")

        # ── Case 2: broken every time -> exhausts budget, escalates tiers ───
        print("=" * 60)
        print("Case 2: broken always (tier escalation + budget exhaustion)")
        ev, n_calls, run_dir = _run([BROKEN_HTML, BROKEN_HTML_SAME, BROKEN_HTML, BROKEN_HTML], tmp)
        r = ev["retry"]
        print(f"  attempted={r['attempted']} attempts={r['attempts']} "
              f"succeeded={r['succeeded']} max_tier={r['max_tier_used']} "
              f"stall_count={r['stall_count']} calls={n_calls}")
        if r["attempts"] != 3:
            failures.append(f"case2: expected 3 attempts (budget), got {r['attempts']}")
        if r["succeeded"] is not False:
            failures.append("case2: succeeded should be False")
        if r["max_tier_used"] < 2:
            failures.append(f"case2: expected tier escalation >=2, got {r['max_tier_used']}")
        records = r.get("attempt_records", [])
        if len(records) != 4:  # initial + 3 retries
            failures.append(f"case2: expected 4 attempt records, got {len(records)}")

        # ── Case 3: good first time -> no retry ────────────────────────────
        print("=" * 60)
        print("Case 3: good first time (no retry)")
        ev, n_calls, run_dir = _run([GOOD_XML], tmp)
        r = ev["retry"]
        print(f"  attempted={r['attempted']} attempts={r['attempts']} calls={n_calls}")
        if r["attempted"] or n_calls != 1:
            failures.append("case3: clean output must not trigger a retry")
        records = r.get("attempt_records", [])
        if len(records) != 1:
            failures.append(f"case3: expected 1 attempt record (initial), got {len(records)}")

        # ── Case 4: broken -> different-broken -> good (tier escalation + recovery)
        print("=" * 60)
        print("Case 4: broken -> stall -> recover at tier 2")
        ev, n_calls, run_dir = _run([BROKEN_HTML, BROKEN_HTML_SAME, GOOD_XML], tmp)
        r = ev["retry"]
        print(f"  attempted={r['attempted']} attempts={r['attempts']} "
              f"succeeded={r['succeeded']} max_tier={r['max_tier_used']} calls={n_calls}")
        if not r["succeeded"]:
            failures.append("case4: should have recovered")
        if r["max_tier_used"] < 2:
            failures.append(f"case4: expected escalation to >=tier 2, got {r['max_tier_used']}")

        # ── Case 5: zero-dim error -> good (different error type recovery) ──
        print("=" * 60)
        print("Case 5: zero-dim error -> good (tier 1 patch)")
        ev, n_calls, run_dir = _run([BROKEN_ZERO, GOOD_XML], tmp)
        r = ev["retry"]
        print(f"  attempted={r['attempted']} attempts={r['attempts']} "
              f"succeeded={r['succeeded']} max_tier={r['max_tier_used']} calls={n_calls}")
        if not (r["attempted"] and r["succeeded"]):
            failures.append("case5: should have recovered from zero-dim")

        # Verify the retry prompt included error-specific guidance
        retry_prompt = (run_dir / "prompt-user-retry1.txt").read_text(encoding="utf-8")
        if "YOUR PREVIOUS XML" not in retry_prompt:
            failures.append("case5: retry prompt should include previous XML")
        if "GUIDANCE" not in retry_prompt:
            failures.append("case5: retry prompt should include guidance section")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 60)
    if failures:
        print(f"\nFAIL ({len(failures)} issue(s)):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nall retry cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
