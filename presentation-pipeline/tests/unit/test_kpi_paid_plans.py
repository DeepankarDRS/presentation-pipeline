"""kpi_paid --plans: arm B on a planner run's plan, matched to each saved slide by its KPI labels (free)."""

from scripts.kpi_paid import fresh_plan


def kpi(cid, labels, idx):
    return {"slide_index": idx, "components": [
        {"component_id": cid, "kind": "kpi_row", "content_data": {"kpi_labels": labels, "kpi_values": ["1"] * len(labels)}}]}


ITEM = {"case": "deck-qbr-data", "slide": 1, "plan": kpi("kpi_metrics", ["ARR", "NRR", "Gross Margin"], 1)}


def test_the_slide_sharing_the_most_kpi_labels_is_taken_from_the_same_repeat():
    runs = [{"case": "deck-qbr-data", "repeat": 1, "slide_plans": [kpi("a", ["ARR"], 1), kpi("b", ["ARR", "NRR"], 2)]},
            {"case": "deck-qbr-data", "repeat": 2, "slide_plans": [kpi("c", ["arr", "nrr", "gross margin"], 3)]}]
    assert fresh_plan(runs, ITEM, 1)["components"][0]["component_id"] == "b"
    assert fresh_plan(runs, ITEM, 2)["components"][0]["component_id"] == "c"
    assert fresh_plan(runs, ITEM, 3)["components"][0]["component_id"] == "b"   # no repeat 3: r1


def test_a_tie_keeps_the_same_slide_index_and_no_shared_label_is_none():
    runs = [{"case": "deck-qbr-data", "repeat": 1, "slide_plans": [kpi("x", ["ARR"], 0), kpi("y", ["ARR"], 1)]}]
    assert fresh_plan(runs, ITEM, 1)["components"][0]["component_id"] == "y"
    assert fresh_plan([{"case": "deck-qbr-data", "repeat": 1, "slide_plans": [kpi("z", ["Churn"], 1)]}], ITEM, 1) is None
    assert fresh_plan([], ITEM, 1) is None
