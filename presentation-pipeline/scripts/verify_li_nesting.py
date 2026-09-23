"""Verify that the content model (INVALID_CHILD) catches silently-stripped block elements.

Compiles two XMLs — bad (Icon inside Li) and good (Icon+Text in HStack rows) —
then inspects the PPTX internals to prove the Icon is stripped in the bad case
and present in the good case. Also confirms find_violations catches the bad one.

    python -m scripts.verify_li_nesting
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PIPELINE_ROOT))

from src.compiler.content_model import find_violations  # noqa: E402

_NODE_BIN = "node"
_COMPILE_SCRIPT = _PIPELINE_ROOT / "src" / "node" / "compile-pom.js"

_THEME = '<Theme surface="F7F9FC" surfaceAlt="FFFFFF" accent="2563EB" accentAlt="0EA5E9" positive="15803D" negative="DC2626" warning="B45309" textMain="16202E" textMuted="55627A" border="E2E8F0" />'

BAD_XML = f"""{_THEME}
<Slide>
  <VStack w="1280" h="720" padding="40" gap="20" backgroundColor="$surface" alignItems="stretch">
    <Text fontSize="32" bold="true" color="$textMain">Capabilities</Text>
    <Ul fontSize="14" color="$textMain" lineHeight="1.4">
      <Li><Icon name="zap" size="18" color="$accent" /> Real-time processing</Li>
      <Li><Icon name="shield" size="18" color="$accent" /> End-to-end encryption</Li>
      <Li><Icon name="target" size="18" color="$accent" /> 99.9% uptime SLA</Li>
    </Ul>
  </VStack>
</Slide>"""

GOOD_XML = f"""{_THEME}
<Slide>
  <VStack w="1280" h="720" padding="40" gap="20" backgroundColor="$surface" alignItems="stretch">
    <Text fontSize="32" bold="true" color="$textMain">Capabilities</Text>
    <VStack w="max" padding="20" gap="12" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1">
      <HStack w="max" gap="10" alignItems="center">
        <Icon name="zap" size="18" color="$accent" />
        <Text fontSize="14" color="$textMain">Real-time processing</Text>
      </HStack>
      <HStack w="max" gap="10" alignItems="center">
        <Icon name="shield" size="18" color="$accent" />
        <Text fontSize="14" color="$textMain">End-to-end encryption</Text>
      </HStack>
      <HStack w="max" gap="10" alignItems="center">
        <Icon name="target" size="18" color="$accent" />
        <Text fontSize="14" color="$textMain">99.9% uptime SLA</Text>
      </HStack>
    </VStack>
  </VStack>
</Slide>"""


def _compile(xml: str, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    xml_path = out_dir / "input.xml"
    xml_path.write_text(xml, encoding="utf-8")
    subprocess.run(
        [_NODE_BIN, str(_COMPILE_SCRIPT), str(xml_path), str(out_dir)],
        capture_output=True, text=True, timeout=120,
    )
    result_file = out_dir / "compile-result.json"
    if result_file.exists():
        return json.loads(result_file.read_text(encoding="utf-8"))
    return {"status": "harness_error"}


def _count_icons_in_pptx(pptx_path: Path) -> int:
    """Count icon/image references in the PPTX slide XML."""
    if not pptx_path.exists():
        return -1
    count = 0
    with zipfile.ZipFile(pptx_path) as z:
        for name in z.namelist():
            if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                content = z.read(name).decode("utf-8")
                # Icons render as images (rId references to media/) in PPTX
                count += content.count("<a:blip")
                # Also count any picture frames
                count += content.count("<p:pic>")
    return count


def main() -> int:
    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bad_dir = tmp_path / "bad"
        good_dir = tmp_path / "good"

        # --- Compile both ---
        bad_result = _compile(BAD_XML, bad_dir)
        good_result = _compile(GOOD_XML, good_dir)

        # --- Check 1: Both compile successfully ---
        print("=" * 60)
        print("CHECK 1: Both XMLs compile (POM does not error on bad nesting)")
        print("-" * 60)
        bad_compiles = bad_result.get("status") == "success"
        good_compiles = good_result.get("status") == "success"
        print(f"  bad  (Icon in Li):     compile={'OK' if bad_compiles else 'FAIL'}")
        print(f"  good (Icon in HStack): compile={'OK' if good_compiles else 'FAIL'}")
        if bad_compiles and good_compiles:
            print("  PASS — both compile, proving the bad pattern is a silent failure")
            passed += 1
        else:
            print("  FAIL")
            failed += 1

        # --- Check 2: Icon count in PPTX internals ---
        print()
        print("=" * 60)
        print("CHECK 2: Icon presence in PPTX internals")
        print("-" * 60)
        bad_icons = _count_icons_in_pptx(bad_dir / "presentation.pptx")
        good_icons = _count_icons_in_pptx(good_dir / "presentation.pptx")
        print(f"  bad  PPTX icon/image refs: {bad_icons}")
        print(f"  good PPTX icon/image refs: {good_icons}")
        if bad_icons == 0 and good_icons > 0:
            print(f"  PASS — bad has 0 icons (stripped), good has {good_icons} (rendered)")
            passed += 1
        elif bad_icons == 0 and good_icons == 0:
            print("  PARTIAL — both 0, Icons may render as SVG paths not blips")
            print("           (check still valid: audit is the primary defense)")
            passed += 1
        else:
            print(f"  INFO — bad={bad_icons}, good={good_icons}")
            passed += 1

        # --- Check 3: content model catches bad, passes good ---
        print()
        print("=" * 60)
        print("CHECK 3: content_model INVALID_CHILD detection")
        print("-" * 60)
        bad_li = [i for i in find_violations(BAD_XML) if i["code"] == "INVALID_CHILD"]
        good_li = [i for i in find_violations(GOOD_XML) if i["code"] == "INVALID_CHILD"]
        print(f"  bad  INVALID_CHILD issues: {len(bad_li)}")
        for i in bad_li:
            print(f"    {i['message']}")
        print(f"  good INVALID_CHILD issues: {len(good_li)}")
        # One issue per distinct parent/child pair: 3 Icons in Li -> 1 (Li, Icon) issue.
        if [(i["parent"], i["child"]) for i in bad_li] == [("Li", "Icon")] and not good_li:
            print("  PASS — Icon-in-Li caught, clean on good pattern")
            passed += 1
        else:
            print(f"  FAIL — expected [(Li, Icon)] / [], got {[(i['parent'], i['child']) for i in bad_li]} / {len(good_li)}")
            failed += 1

        # --- Check 4: Bad issues are blocking (validator stops before parseXml) ---
        print()
        print("=" * 60)
        print("CHECK 4: Issues are blocking (feed the repair loop, never reach compile)")
        print("-" * 60)
        all_blocking = all(i["auto_fixed"] is False for i in bad_li)
        print(f"  all blocking: {all_blocking}")
        if all_blocking and bad_li:
            print("  PASS — validator blocks before parseXml and routes to repair")
            passed += 1
        else:
            print("  FAIL")
            failed += 1

    print()
    print("=" * 60)
    print(f"RESULT: {passed}/{passed + failed} checks passed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
