"""Contract-aware pre-validator checks. No API key needed.

    python python/test_prevalidator.py

Verifies that pre_validate(xml, contract) flags hallucinated attributes
(uppercase="true" on <Text>, direction=... on <VStack>) as blocking
UNKNOWN_ATTR issues, and that legitimate attributes — universal box attrs,
dotted object-attrs, everything on a compile-verified example — do NOT trip it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import slide_ir  # noqa: E402
from context_selector import select_context  # noqa: E402
from pre_validator import pre_validate  # noqa: E402


def _codes(result) -> list[str]:
    return [i.code for i in result.issues]


def main() -> int:
    failures: list[str] = []

    # A contract that allows Slide/Theme/VStack/Text/Shape (+ chart/table here).
    ir = slide_ir.from_request(
        "A dense executive slide: title, a KPI row, a revenue chart and a "
        "segment table.",
        components=["title", "kpi_row", "chart", "table"],
    )
    contract = select_context(ir)

    # 1. hallucinated attributes -> blocking UNKNOWN_ATTR
    bad = (config.TESTS_DIR / "malformed" / "uppercase_attr.yaml").read_text(encoding="utf-8")
    r = pre_validate(bad, contract)
    unknown = [i for i in r.issues if i.code == "UNKNOWN_ATTR"]
    flagged = {i.message.split('"')[1] for i in unknown}
    for want in ("uppercase", "letterCase", "direction", "elevation"):
        if want not in flagged:
            failures.append(f"expected UNKNOWN_ATTR for {want!r}; flagged={sorted(flagged)}")
    if unknown and not r.blocking:
        failures.append("UNKNOWN_ATTR issues should make the result blocking")

    # 2. no contract -> no attribute checking (back-compat)
    r_nocontract = pre_validate(bad)
    if any(i.code == "UNKNOWN_ATTR" for i in r_nocontract.issues):
        failures.append("pre_validate without a contract must not raise UNKNOWN_ATTR")

    # 3. a compile-verified example must pass clean under its own contract
    for example, comps in (
        ("mixed-slide.xml", ["title", "kpi_row", "chart", "table"]),
        ("table-slide.xml", ["title", "table"]),
        ("kpi-slide.xml", ["title", "kpi_row"]),
    ):
        xml = (config.KNOWLEDGE_DIR / "examples" / example).read_text(encoding="utf-8")
        c = select_context(slide_ir.from_request("x", components=comps))
        res = pre_validate(xml, c)
        bad_codes = [i for i in res.issues if i.code == "UNKNOWN_ATTR"]
        if bad_codes:
            failures.append(
                f"{example}: false-positive UNKNOWN_ATTR: "
                + "; ".join(i.message for i in bad_codes)
            )

    if failures:
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("pre-validator contract test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
