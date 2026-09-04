"""Theme library + resolver checks. No API key needed.

    python python/test_theme.py

Verifies: every palette in the library clears the WCAG contrast targets;
resolve() applies overrides, honours legacy dark/light aliases, falls back on
an unknown name, and falls back wholesale on an unreadable custom palette;
theme_element() emits chartSurface/chartInk only for dark palettes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import theme as theme_lib  # noqa: E402


def main() -> int:
    failures: list[str] = []
    names = theme_lib.available()
    print(f"palettes: {len(names)} -> {', '.join(names)}")

    # 1. every library palette passes its own contrast checks
    for name in names:
        rt = theme_lib.resolve(name)
        if rt.fell_back:
            failures.append(f"{name}: unexpectedly fell back to default")
        warns = theme_lib.verify(rt)
        if warns:
            failures.append(f"{name}: contrast warnings: {warns}")
        # dark palettes must define the chart-card tokens; light must not emit them
        el = theme_lib.theme_element(rt)
        if rt.is_dark and ("chartSurface" not in el or "chartInk" not in el):
            failures.append(f"{name}: dark palette missing chartSurface/chartInk")
        if not rt.is_dark and "chartSurface" in el:
            failures.append(f"{name}: light palette should not emit chartSurface")
        if len(rt.chart_colors) < 2:
            failures.append(f"{name}: needs >= 2 chartColors")

    # 2. legacy aliases
    if theme_lib.resolve("dark").name != "graphite-dark":
        failures.append("alias 'dark' should resolve to graphite-dark")
    if theme_lib.resolve("light").name != theme_lib.default_name():
        failures.append("alias 'light' should resolve to the default palette")

    # 3. unknown name -> fallback + warning
    unk = theme_lib.resolve("no-such-palette")
    if not unk.fell_back or unk.name != theme_lib.default_name():
        failures.append("unknown palette should fall back to default")
    if not any("unknown theme" in w for w in unk.warnings):
        failures.append("unknown palette should emit a warning")

    # 4. token override
    ov = theme_lib.resolve("corporate-slate", {"accent": "#FF0000"})
    if ov.tokens["accent"] != "FF0000":
        failures.append("override should set accent to FF0000 (hash stripped)")

    # 5. unreadable custom palette -> wholesale fallback
    broken = theme_lib.resolve("corporate-slate", {"textMain": "F9F9F9"})
    if not broken.fell_back:
        failures.append("unreadable body text should trigger wholesale fallback")

    # 6. chartColors override
    cc = theme_lib.resolve("corporate-slate", {"chartColors": ["111111", "222222"]})
    if cc.chart_colors != ["111111", "222222"]:
        failures.append(f"chartColors override ignored: {cc.chart_colors}")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\ntheme test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
