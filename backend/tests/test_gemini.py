"""Tests for the Gemini client (unit tests, no real API calls)."""

from unittest.mock import MagicMock, patch

import pytest

from aeo_engine.gemini import call_gemini


@pytest.mark.asyncio
async def test_call_gemini_returns_response() -> None:
    """Mock the Gemini API and verify the response shape."""
    mock_response = MagicMock()
    mock_response.text = "Linear is the best project management tool."

    with patch("aeo_engine.gemini._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
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
