from apps.recommendations.services.v1.intent_patterns import (
    INTENT_PATTERNS,
    PlanIntentFeatures,
    message_for,
    pattern_matches,
)


def test_registry_has_exactly_the_approved_keys():
    assert set(INTENT_PATTERNS) == {
        "cheap",
        "value",
        "spec_heavy",
        "premium",
        "exploring",
    }


def test_registry_has_no_text_specific_pattern():
    assert all("text_specific" not in key for key in INTENT_PATTERNS)


def test_real_pattern_predicates():
    assert pattern_matches("cheap", PlanIntentFeatures(price_pct=0.2))
    assert pattern_matches(
        "value", PlanIntentFeatures(price_pct=0.2, spec_pct=0.5)
    )
    assert pattern_matches("spec_heavy", PlanIntentFeatures(spec_pct=0.8))
    assert pattern_matches(
        "premium", PlanIntentFeatures(price_pct=0.8, spec_pct=0.8)
    )


def test_patterns_do_not_match_when_required_features_are_missing():
    assert not pattern_matches("cheap", PlanIntentFeatures())
    assert not pattern_matches("value", PlanIntentFeatures(price_pct=0.2))
    assert not pattern_matches("premium", PlanIntentFeatures(spec_pct=0.9))


def test_messages_are_questions_from_configuration():
    message = message_for("value", "positive")
    assert message.endswith("؟")
    assert message != "value"


def test_exploring_message_is_a_question():
    assert message_for("exploring").endswith("؟")
