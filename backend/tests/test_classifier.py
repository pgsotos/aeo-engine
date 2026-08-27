"""Tests for the classifier (pure function, no external deps)."""

from aeo_engine.classifier import classify_response
from aeo_engine.models import Classification


def test_linear_is_direct_winner_when_recommended_first() -> None:
    """Linear recommended first with strong language → DIRECT_WINNER."""
    text = (
        "I recommend Linear as the best project management tool. "
        "It has a clean interface, fast keyboard shortcuts, and great "
        "GitHub integration. While Jira is more feature-rich, Linear "
        "is the top choice for modern software teams."
    )
    result = classify_response(text, "Linear")
    assert result.classification == Classification.DIRECT_WINNER
    assert result.mention_count >= 2
    assert result.first_mention_position is not None


def test_linear_is_alternative_when_mentioned_second() -> None:
    """Linear mentioned but not as primary → ALTERNATIVE_MENTION."""
    text = (
        "Jira is the best project management tool for large teams. "
        "Linear is a solid alternative if you want something simpler, "
        "but Jira has more integrations and enterprise features."
    )
    result = classify_response(text, "Linear")
    assert result.classification == Classification.ALTERNATIVE_MENTION
    assert result.mention_count >= 1


def test_linear_is_omitted_when_not_mentioned() -> None:
    """Linear not mentioned at all → OMITTED."""
    text = (
        "Jira is the best project management tool. It has extensive "
        "integrations, enterprise features, and a large ecosystem."
    )
    result = classify_response(text, "Linear")
    assert result.classification == Classification.OMITTED
    assert result.mention_count == 0
    assert result.first_mention_position is None


def test_classifier_is_case_insensitive() -> None:
    """Classification should work regardless of brand casing."""
    text = "I think linear is the best option for your team."
    result = classify_response(text, "Linear")
    assert result.classification == Classification.DIRECT_WINNER


def test_classifier_handles_empty_response() -> None:
    """Empty response → OMITTED for any brand."""
    result = classify_response("", "Linear")
    assert result.classification == Classification.OMITTED


def test_classifier_handles_list_mention() -> None:
    """Brand mentioned in a list without recommendation → ALTERNATIVE."""
    text = (
        "There are several good project management tools: Jira, Linear, "
        "Asana, Monday, and Notion. Each has its own strengths."
    )
    result = classify_response(text, "Linear")
    assert result.classification == Classification.ALTERNATIVE_MENTION
    assert result.mention_count == 1
