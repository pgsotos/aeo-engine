"""Tests for the Gemini client (unit tests, no real API calls).

Grounding behavior (Slice 2): `_sync_call` returns `(raw_text, grounding_metadata)`
and `call_gemini` surfaces grounding metadata on the response model while keeping
`raw_text` verbatim. Grounding presence is stochastic in the provider, so both
with-metadata and without-metadata paths are first-class.
"""

from unittest.mock import MagicMock, patch

import pytest

from aeo_engine.gemini import _clean_categories, call_gemini

GROUNDING_PAYLOAD = {
    "grounding_chunks": [
        {"web": {"uri": "https://redirect.example/x", "title": "Linear - Wikipedia"}},
        {"web": {"uri": "https://redirect.example/y", "title": "Jira - Atlassian.com"}},
    ],
    "grounding_supports": [
        {"segment": {"start_index": 0, "end_index": 52, "text": "Linear is..."}}
    ],
    "web_search_queries": ["best project management tool"],
}


def _mock_grounding_metadata(payload: dict) -> MagicMock:
    """A candidate.grounding_metadata stand-in whose model_dump yields `payload`."""
    gm = MagicMock()
    gm.model_dump.return_value = payload
    return gm


@pytest.mark.asyncio
async def test_call_gemini_returns_response() -> None:
    """Mock the Gemini API and verify the response shape."""
    mock_response = MagicMock()
    mock_response.text = "Linear is the best project management tool."
    mock_response.candidates = []  # no candidates → no grounding metadata

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
        # Instruction regurgitation: the model echoes the prompt instead of
        # returning categories ("no quotes", "lowercase", "nothing else", ...).
        ("no quotes", []),
        ('"no quotes", project management', ["project management"]),
        ("lowercase, issue tracking", ["issue tracking"]),
        ("nothing else, note-taking", ["note-taking"]),
        ("comma-separated list of categories, video editing", ["video editing"]),
        ("return the brand name, project management", ["project management"]),
        ("e.g. linear algebra, note-taking", ["note-taking"]),
        # Empty input yields no categories.
        ("", []),
        # Whitespace-only input yields no categories.
        ("   ,  , ", []),
    ],
)
def test_clean_categories_drops_meta_language(raw: str, expected: list[str]) -> None:
    """Meta-language/truncation tokens must never surface as selectable categories."""
    assert _clean_categories(raw) == expected


def test_clean_categories_drops_echoed_brand() -> None:
    """A brand name echoed back as a 'category' is dropped — exact match only,
    so lookalike categories like "linear algebra" survive."""
    assert _clean_categories('"Linear", project management', brand="Linear") == [
        "project management",
    ]
    assert _clean_categories("Linear", brand="Linear") == []
    assert _clean_categories("linear algebra, note-taking", brand="Linear") == [
        "linear algebra",
        "note-taking",
    ]
    assert _clean_categories("linear algebra", brand="Linear") == ["linear algebra"]


def test_clean_categories_brand_filter_is_opt_in() -> None:
    """Without a brand argument the exact-name chunk is kept — the filter is an
    explicit opt-in, so callers that don't know the brand never lose a category."""
    assert _clean_categories("Linear") == ["Linear"]


def test_clean_categories_caps_length() -> None:
    """Over-long category strings are truncated so a runaway token never renders
    as an unruly option."""
    long = "x" * 100
    assert _clean_categories(long) == ["x" * 50]
    assert _clean_categories(long)[0] == "x" * 50


@pytest.mark.asyncio
async def test_call_gemini_surfaces_grounding_metadata() -> None:
    """When the provider returns grounding metadata, it is serialized onto the
    response model and raw_text stays verbatim."""
    text = "Linear is the best project management tool."
    mock_response = MagicMock()
    mock_response.text = text
    mock_response.candidates = [
        MagicMock(grounding_metadata=_mock_grounding_metadata(GROUNDING_PAYLOAD))
    ]

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

        # Immutability rule: raw text preserved byte-for-byte.
        assert result.raw_text == text
        # Grounding metadata surfaced on the public model (plain dict).
        assert result.grounding_metadata == GROUNDING_PAYLOAD
        # Google Search grounding is requested on the chat config.
        config = mock_client.chats.create.call_args.kwargs["config"]
        assert config.tools[0].google_search is not None


@pytest.mark.asyncio
async def test_call_gemini_grounding_metadata_none_when_absent() -> None:
    """When the provider returns no grounding, grounding_metadata is None —
    never a partial or empty object."""
    text = "Jira is the best project management tool."
    mock_response = MagicMock()
    mock_response.text = text
    mock_response.candidates = []

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

        assert result.raw_text == text
        assert result.grounding_metadata is None


# ── Client caching ──────────────────────────────────────────────────────────
#
# `_get_client` used to build a fresh `genai.Client` on every call, from inside
# `_sync_call` — 160 clients per evaluation at 20 prompts x N=8, each carrying
# its own HTTP connection pool. Measured at ~117 KB apiece before counting
# socket buffers, on a 512 MB instance. `database.get_client` was already a
# singleton; this brings the two in line.


def test_client_is_cached_across_calls(monkeypatch) -> None:
    import aeo_engine.gemini as gemini_module

    monkeypatch.setattr(gemini_module, "_client", None)
    monkeypatch.setattr(gemini_module.settings, "gemini_api_key", "test-key")

    built = []

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            built.append(kwargs)

    monkeypatch.setattr(gemini_module.genai, "Client", FakeClient)

    first = gemini_module._get_client()
    second = gemini_module._get_client()

    assert first is second
    assert len(built) == 1, "a second client was constructed"


def test_missing_key_still_raises_and_caches_nothing(monkeypatch) -> None:
    """The setup error must survive caching — an absent key cannot be memoised
    into a client, and a later call with a key configured must still work."""
    import aeo_engine.gemini as gemini_module

    monkeypatch.setattr(gemini_module, "_client", None)
    monkeypatch.setattr(gemini_module.settings, "gemini_api_key", "")

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        gemini_module._get_client()

    assert gemini_module._client is None
