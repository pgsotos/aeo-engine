"""Tests for the Gemini client (unit tests, no real API calls)."""

from unittest.mock import MagicMock, patch

import pytest

from aeo_engine.gemini import _clean_categories, call_gemini


@pytest.mark.asyncio
async def test_call_gemini_returns_response() -> None:
    """Mock the Gemini API and verify the response shape."""
    mock_response = MagicMock()
    mock_response.text = "Linear is the best project management tool."

    with patch("aeo_engine.gemini._get_client") as mock_get:
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response

        mock_client = MagicMock()
        mock_client.chats.create.return_value = mock_chat
        mock_get.return_value = mock_client

        result = await call_gemini(
            prompt="What is the best PM tool?",
            evaluation_id="eval-1",
            prompt_id="direct-01",
            run_index=1,
        )

        assert result.raw_text == "Linear is the best project management tool."
        assert result.evaluation_id == "eval-1"
        assert result.prompt_id == "direct-01"
        assert result.run_index == 1
        assert result.model_id == "gemini-3.6-flash"

        # Verify Chat API was used, not Models API
        mock_client.chats.create.assert_called_once()
        mock_chat.send_message.assert_called_once_with("What is the best PM tool?")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Truncation artifact "Select the" and other meta-language tokens are dropped.
        (
            "Select the project management tools, issue tracking, please",
            ["issue tracking"],
        ),
        # A chunk matching a blacklisted token mid-string is dropped too.
        ("here are the options, video editing", ["video editing"]),
        # Empty input yields no categories.
        ("", []),
        # Whitespace-only input yields no categories.
        ("   ,  , ", []),
    ],
)
def test_clean_categories_drops_meta_language(raw: str, expected: list[str]) -> None:
    """Meta-language/truncation tokens must never surface as selectable categories."""
    assert _clean_categories(raw) == expected


def test_clean_categories_caps_length() -> None:
    """Over-long category strings are truncated so a runaway token never renders
    as an unruly option."""
    long = "x" * 100
    assert _clean_categories(long) == ["x" * 50]
    assert _clean_categories(long)[0] == "x" * 50
