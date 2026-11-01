"""Palette contrast review: every resolved theme's colour pairs against WCAG / the house targets (free, no LLM).

Checks the <Theme> each palette resolves to (authored + derived + chartN tokens):

  text   4.5:1   textMain, textMuted, *Text roles, onAccent, onPanelDark, chartInk on the fills they sit on
  accent 3.0:1   accent / accentAlt / positive / negative / warning as large text or marks on surface + surfaceAlt
  chart  2.0:1   chartN on chartSurface (the code's CHART_MIN; WCAG non-text asks 3.0, reported too)
  border 1.4:1   border on surface + surfaceAlt (the code's BORDER_MIN)
  meaning        accent too close to negative / positive (Lab dE < 15): a focus number reads as good / bad

Then (--slide) the layout audit's LOW_CONTRAST on one slide re-coloured into every theme.

    python -m scripts.palette_contrast
    python -m scripts.palette_contrast --only mbb-blue mbb-red --slide tests/fixtures/golden/gj-h1-deck/02-h1-snapshot.xml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.agents.style_resolver import resolve_theme, theme_names  # noqa: E402
from src.compiler.palette_tokens import contrast  # noqa: E402
from src.compiler.theme_swap import _lab, swap_theme, theme_tokens  # noqa: E402

_THEME_RE = re.compile(r"<Theme\b[^>]*/>")
_NEW = {"mbb-blue", "mbb-blue-dark", "perceptis", "perceptis-dark",
        "mbb-green", "mbb-green-dark", "mbb-red", "mbb-red-dark"}


def _de(a: str, b: str) -> float:
    return sum((x - y) ** 2 for x, y in zip(_lab(a), _lab(b))) ** 0.5


def pairs(t: dict[str, str]) -> list[tuple[str, str, str, float]]:
    """(kind, fg token, bg token, minimum) for every pair the house style draws."""
    out = []
    bases = ["surface", "surfaceAlt"]
    for fg in ("textMain", "textMuted"):
        out += [("text", fg, bg, 4.5) for bg in bases]
    for role in ("accent", "positive", "negative", "warning"):
        out += [("text", f"{role}Text", bg, 4.5) for bg in bases + [f"{role}Soft"]]
    out += [("text", "textMain", f"{r}Soft", 4.5) for r in ("accent", "positive", "negative", "warning")]
    out += [("text", "onAccent", "accent", 4.5), ("text", "onPanelDark", "panelDark", 4.5)]
    if "chartSurface" in t:
        out += [("text", "chartInk", "chartSurface", 4.5)]
    for fg in ("accent", "accentAlt", "positive", "negative", "warning"):
        out += [("accent", fg, bg, 3.0) for bg in bases]
    chart_bg = "chartSurface" if "chartSurface" in t else "surfaceAlt"
    out += [("chart", k, chart_bg, 2.0) for k in sorted(t) if re.fullmatch(r"chart\d", k)]
    out += [("border", "border", bg, 1.4) for bg in bases]
    return out


def review(name: str) -> tuple[list[str], list[str]]:
    """(failures, notes) for one palette."""
    t = theme_tokens(resolve_theme(name)["element"])
    fails, notes = [], []
    for kind, fg, bg, need in pairs(t):
        if fg not in t or bg not in t:
            continue
        r = contrast(t[fg], t[bg])
        if r < need:
            fails.append(f"{kind:6} {fg} {t[fg]} on {bg} {t[bg]}: {r:.2f} < {need}")
        elif kind == "chart" and r < 3.0:
            notes.append(f"chart  {fg} {t[fg]} on {bg}: {r:.2f} (passes 2.0, under WCAG non-text 3.0)")
        elif kind == "accent" and fg == "accent" and r < 4.5:
            notes.append(f"accent {t['accent']} on {bg}: {r:.2f} - large text / marks only; small text must use $accentText")
    for role in ("negative", "positive"):
        d = _de(t["accent"], t[role])
        if d < 15:
            fails.append(f"meaning accent {t['accent']} vs {role} {t[role]}: dE {d:.1f} < 15 (focus reads as {role})")
    return fails, notes


def slide_audit(slide: Path, names: list[str]) -> dict[str, list[str]]:
    from src.compiler.layout_audit import audit_layout

    raw = slide.read_text(encoding="utf-8")
    old = _THEME_RE.search(raw).group(0)
    out = {}
    for n in names:
        th = resolve_theme(n)
        xml = th["element"] + "\n" + swap_theme(raw, old, th["element"], th["is_dark"]).xml
        out[n] = [w.get("message", "") for w in audit_layout(xml) if w.get("code") == "LOW_CONTRAST"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--slide", type=Path,
                    default=_ROOT / "tests" / "fixtures" / "golden" / "gj-h1-deck" / "02-h1-snapshot.xml")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")     # slide text has ₹ / → (cp1252 console)
    names = args.only or theme_names()

    total = 0
    for n in names:
        fails, notes = review(n)
        total += len(fails)
        tag = " [new]" if n in _NEW else ""
        print(f"\n## {n}{tag}: {'PASS' if not fails else f'{len(fails)} FAIL'}")
        for f in fails:
            print("  FAIL", f)
        for x in notes:
            print("  note", x)
    print(f"\nToken pairs: {total} failures over {len(names)} palettes")

    print("\n## LOW_CONTRAST on", args.slide.name)
    for n, msgs in slide_audit(args.slide, names).items():
        print(f"  {n:18} {len(msgs)}" + ("" if not msgs else "  " + " | ".join(m[:110] for m in msgs[:4])))


if __name__ == "__main__":
    main()
