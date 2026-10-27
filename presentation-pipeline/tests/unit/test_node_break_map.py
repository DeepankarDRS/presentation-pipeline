"""The node break map's break points stay where they were measured (2026-10-21).

docs/eval/node-break-map/: every diagram swept over item count, label length, direction and
placement, compiled with POM + fit-grow, scored on what is drawn (scripts/node_break_map.py).
This test compiles a small slice of that grid (TEST_SLICE: each series at the count it holds at
and the count after it) and fails when a break point moves — a POM upgrade or a fit-grow change
that makes a diagram break earlier or hold longer shows up here, not in a deck. It also fails when
capacity.yaml promises a diagram more items per direction than the measured band holds, unless
the disagreement is recorded (with its reason) in the fixture while the user decides.
Re-measure after a deliberate change: `python -m scripts.node_break_map --kinds <kind>` then
`python -m scripts.node_break_map --write-points`.
"""

import shutil
from pathlib import Path

import pytest
import yaml

from scripts import node_break_map as bm

_ROOT = Path(__file__).resolve().parents[2]
_POM = _ROOT / "src" / "node" / "node_modules" / "@hirokisakabe" / "pom"
_needs_pom = pytest.mark.skipif(not _POM.exists() or not shutil.which("node"), reason="POM/node not installed")
_CAPACITY = yaml.safe_load((_ROOT / "src" / "knowledge" / "core" / "capacity.yaml").read_text(encoding="utf-8"))


def _points() -> dict:
    return yaml.safe_load(bm.POINTS.read_text(encoding="utf-8"))


def _key(p: dict) -> str:
    return f"{p['kind']} {p['placement']} {p['direction']} {p['labels']} {p['style']} {p['variant'] or '-'}"


def test_fixture_covers_the_slice():
    got = {_key(p) for p in _points()["series"]}
    want = {_key(dict(zip(("kind", "placement", "direction", "labels", "style", "variant"), s))) for s in bm.TEST_SLICE}
    assert got == want


@_needs_pom
def test_break_points_hold(tmp_path):
    points = _points()["series"]
    cases = [c for p in points for c in bm.slice_cases(p)]
    built = bm.compile_cases(cases, tmp_path, jobs=4, modes=("fit",))
    rows = {(r["id"]): r for r in bm.evaluate(cases, built, tmp_path)}
    moved = []
    for p in points:
        got = {c.count: bm.breaks(rows[c.id]) for c in bm.slice_cases(p)}
        n = p["holds_up_to"]
        if n is None:
            if not got[p["swept"][0]]:
                moved.append(f"{_key(p)}: recorded as breaking at {p['swept'][0]}, now holds")
            continue
        if got[n]:
            moved.append(f"{_key(p)}: recorded to hold {n}, now breaks ({', '.join(got[n])})")
        if n + 1 in got and not got[n + 1]:
            moved.append(f"{_key(p)}: recorded to break at {n + 1} ({p['first_break']}), now holds")
    assert not moved, "break points moved (re-measure and update the map if deliberate):\n" + "\n".join(moved)


def test_capacity_never_promises_more_than_the_band_holds():
    data = _points()
    accepted = data.get("capacity_disagreements") or {}
    over = []
    for kind, labels in bm.CAPACITY_LABELS.items():
        for direction, cap in _CAPACITY[kind]["max_items"].items():
            band = [p for p in data["series"] if (p["kind"], p["placement"], p["direction"], p["labels"], p["style"])
                    == (kind, "band", direction, labels, "default")]
            assert band, f"no band series for {kind} {direction} {labels}"
            n = band[0]["holds_up_to"] or 0
            key = f"{kind}.{direction}"
            if cap > n and key not in accepted:
                over.append(f"{key}: capacity {cap}, the band holds {n} ({labels} labels, {band[0]['first_break']})")
            if key in accepted and cap <= n:
                over.append(f"{key}: listed as a disagreement but capacity {cap} <= measured {n}; remove it")
    assert not over, "\n".join(over)
