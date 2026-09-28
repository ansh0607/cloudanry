from backend.services.confidence import compute_confidence


def test_no_signals_stays_at_base():
    result = compute_confidence([], [])
    assert result["confidence_score"] == 50.0
    assert result["score_breakdown"][0]["step"] == "base"


def test_supporting_signals_increase_score():
    result = compute_confidence(
        [{"description": "GPS matches", "strength": 80}], []
    )
    assert result["confidence_score"] > 50.0
    assert result["confidence_score"] <= 100.0


def test_adversarial_signals_decrease_score():
    result = compute_confidence(
        [], [{"description": "duplicate detected", "severity": "high"}]
    )
    assert result["confidence_score"] < 50.0
    assert result["confidence_score"] >= 0.0


def test_breakdown_is_itemized_and_adds_up():
    result = compute_confidence(
        [{"description": "a", "strength": 60}, {"description": "b", "strength": 40}],
        [{"description": "c", "severity": "medium"}],
    )
    steps = [s["step"] for s in result["score_breakdown"]]
    assert steps == ["base", "supporting", "supporting", "adversarial", "final"]
    base = next(s for s in result["score_breakdown"] if s["step"] == "base")
    supporting = [s for s in result["score_breakdown"] if s["step"] == "supporting"]
    adversarial = [s for s in result["score_breakdown"] if s["step"] == "adversarial"]
    total = base["delta"] + sum(s["delta"] for s in supporting) - sum(-s["delta"] for s in adversarial)
    assert round(total, 1) == result["confidence_score"]


def test_high_severity_deducts_more_than_low():
    high = compute_confidence([], [{"description": "x", "severity": "high"}])
    low = compute_confidence([], [{"description": "x", "severity": "low"}])
    assert high["confidence_score"] < low["confidence_score"]


def test_score_clamped_to_0_100():
    many_high = [{"description": f"s{i}", "severity": "high"} for i in range(10)]
    result = compute_confidence([], many_high)
    assert result["confidence_score"] == 0.0
    many_strong = [{"description": f"s{i}", "strength": 100} for i in range(10)]
    result2 = compute_confidence(many_strong, [])
    assert result2["confidence_score"] <= 100.0


def test_deterministic_same_inputs_same_score():
    args = ([{"description": "a", "strength": 70}], [{"description": "b", "severity": "low"}])
    assert compute_confidence(*args)["confidence_score"] == compute_confidence(*args)["confidence_score"]
