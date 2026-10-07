"""Visual critic vs code (2026-10-07): code owns size / spacing / fill (fit-grow), the critic owns
what code cannot measure and confirms borderline geometry warnings on the screenshot."""

from src.agents.critic import critic_layout_issues
from src.agents.visual_critic import _jinja_env, code_owned


def test_size_and_space_issues_are_code_owned():
    assert code_owned("Large empty band under the table", "give the table card grow=2")
    assert code_owned("KPI numbers are oversized", "reduce fontSize to 40")
    assert code_owned("Cards are under-filled", "increase padding")


def test_visible_defects_stay_with_the_critic():
    assert not code_owned("Table text is clipped at the card edge", "reduce fontSize")
    assert not code_owned("Labels overlap the chart", "add a gap")
    assert not code_owned("Kicker missing above the title", "insert a Text node")


def test_critic_sees_geometry_warnings_not_errors_or_fill():
    issues = [
        {"code": "GEOM_COLLISION", "tier": "warning", "message": "6px"},
        {"code": "GEOM_SPILL", "tier": "error", "message": "96px"},
        {"code": "GEOM_CARD_EMPTY", "tier": "info", "message": "28%"},
        {"code": "LOW_CONTRAST", "tier": "warning", "message": "accent text"},
        {"code": "BAND_HEIGHT_SUM", "message": "bands too tall"},
    ]
    assert [i["code"] for i in critic_layout_issues(issues)] == ["GEOM_COLLISION", "BAND_HEIGHT_SUM"]


def test_prompt_hands_size_to_code():
    system = _jinja_env.get_template("system.j2").render(slide_type="content")
    assert "CODE-OWNED" in system
    assert 'grow="2"' not in system
