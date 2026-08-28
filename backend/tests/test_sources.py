"""Tests for the Source Auditor extraction functions (pure, no I/O).

Slices the Google Search grounding metadata (as stored on
`GeminiResponse.grounding_metadata`) into attributed sources and support
segments. Grounding presence is stochastic, so None/empty inputs are
first-class cases.
"""

from aeo_engine.models import Classification, ClassificationResult, GroundingSource
from aeo_engine.sources import (
    aggregate_search_queries,
    compute_source_impact,
    extract_domain,
    extract_search_queries,
    extract_sources,
    extract_supports,
)

# Realistic grounding payload: web.uri is an opaque redirect token, the real
# attribution signal lives in grounding_chunks[].web.title.
GROUNDING_FIXTURE = {
    "grounding_chunks": [
        {
            "web": {
                "uri": "https://redirect.google.com/x1",
                "title": "Linear Review 2025 - linear.app",
            }
        },
        {
            "web": {
                "uri": "https://redirect.google.com/x2",
                "title": "Compare Tools | G2.com",
            }
        },
        {
            "web": {
                "uri": "https://redirect.google.com/x3",
                "title": "An article without a domain",
            }
        },
    ],
    "grounding_supports": [
        {
            "segment": {
                "start_index": 0,
                "end_index": 52,
                "text": "Linear is the best project management tool.",
            },
            "grounding_chunk_indices": [0],
        },
        {
            "segment": {"start_index": 60, "end_index": 120, "text": "G2 ranks it highly."},
            "grounding_chunk_indices": [1, 2],
        },
    ],
    "web_search_queries": [],
}


# ── extract_domain ──────────────────────────────────────────────────────────


def test_extract_domain_parses_host_from_title() -> None:
    """A title carrying a domain-like token yields it, lowercased."""
    assert extract_domain("Linear Review 2025 - linear.app") == "linear.app"
    assert extract_domain("Compare Tools | G2.com") == "g2.com"


def test_extract_domain_unparseable_returns_empty() -> None:
    """Titles without a domain-like token yield '' — never a guess."""
    assert extract_domain("An article without a domain") == ""
    assert extract_domain("") == ""
    assert extract_domain("   ") == ""


def test_extract_domain_takes_first_token() -> None:
    """'Notion vs Monday.com' is attributed to the first domain seen."""
    assert extract_domain("Notion vs Monday.com: Which Is Better?") == "monday.com"


# ── extract_sources ─────────────────────────────────────────────────────────


def test_extract_sources_from_grounding_chunks() -> None:
    """One source per chunk, attributed from web.title (never web.uri)."""
    sources = extract_sources(GROUNDING_FIXTURE)

    assert len(sources) == 3
    assert [s.web_title for s in sources] == [
        "Linear Review 2025 - linear.app",
        "Compare Tools | G2.com",
        "An article without a domain",
    ]
    # chunk 3's URI contains "redirect.google.com" but its title does not —
    # proves extraction is title-based, not uri-based.
    assert [s.domain for s in sources] == ["linear.app", "g2.com", ""]
    assert [s.chunk_index for s in sources] == [0, 1, 2]
    # response_id is assigned by the persistence caller, not the extractor.
    assert all(s.response_id == "" for s in sources)


def test_extract_sources_none_or_empty_yields_no_sources() -> None:
    """No grounding → no sources (None and empty dict are equivalent)."""
    assert extract_sources(None) == []
    assert extract_sources({}) == []
    assert extract_sources({"grounding_chunks": []}) == []


def test_extract_sources_skips_chunk_without_web_title() -> None:
    """A chunk with no web entry/title cannot be attributed and is skipped."""
    payload = {
        "grounding_chunks": [
            {"web": {"title": "Linear - Wikipedia"}},
            {"web": {"uri": "https://redirect.google.com/x2"}},  # no title
            {},  # empty chunk
        ]
    }
    sources = extract_sources(payload)
    assert len(sources) == 1
    assert sources[0].web_title == "Linear - Wikipedia"


# ── extract_supports ────────────────────────────────────────────────────────


def test_extract_supports_segment_offsets() -> None:
    """One support per grounding_support, carrying segment start/end offsets.

    A support citing several chunks links to its FIRST cited chunk index.
    """
    supports = extract_supports(GROUNDING_FIXTURE)

    assert len(supports) == 2
    assert [(s.segment_start, s.segment_end) for s in supports] == [(0, 52), (60, 120)]
    assert [s.source_chunk_index for s in supports] == [0, 1]


def test_extract_supports_none_or_empty_yields_no_supports() -> None:
    """No grounding → no supports."""
    assert extract_supports(None) == []
    assert extract_supports({}) == []
    assert extract_supports({"grounding_supports": []}) == []


def test_extract_supports_skips_segmentless_and_keeps_unlinked() -> None:
    """Supports without segment offsets are dropped; supports without chunk
    references are kept (offsets preserved, no source link)."""
    payload = {
        "grounding_supports": [
            {"segment": {"start_index": 0, "end_index": 10}, "grounding_chunk_indices": [0]},
            {"segment": {"text": "no offsets"}, "grounding_chunk_indices": [0]},
            {"segment": {"start_index": 20, "end_index": 30}},
        ]
    }
    supports = extract_supports(payload)
    assert len(supports) == 2
    assert (supports[0].segment_start, supports[0].segment_end) == (0, 10)
    assert supports[0].source_chunk_index == 0
    assert (supports[1].segment_start, supports[1].segment_end) == (20, 30)
    assert supports[1].source_chunk_index is None


# ── compute_source_impact ────────────────────────────────────────────────────


def _source(response_id: str, domain: str) -> GroundingSource:
    return GroundingSource(
        response_id=response_id,
        web_title=f"{domain} article",
        domain=domain,
        chunk_index=0,
    )


def _classification(response_id: str, classification: Classification) -> ClassificationResult:
    return ClassificationResult(
        response_id=response_id,
        brand="Linear",
        classification=classification,
    )


def test_source_impact_correlates_domains_with_direct_wins() -> None:
    """Impact = how often a cited domain co-occurs with the focus brand being a
    Direct Winner. `response_map` bridges source response ids to classification
    response ids (kept non-identity here to prove the bridge is honored)."""
    sources = [
        _source("src-1", "linear.app"),  # cited in a winning response
        _source("src-1", "g2.com"),  # cited in the same winning response
        _source("src-2", "linear.app"),  # cited in a losing response
    ]
    classifications = [
        _classification("cls-1", Classification.DIRECT_WINNER),
        _classification("cls-2", Classification.ALTERNATIVE_MENTION),
    ]
    response_map = {"src-1": "cls-1", "src-2": "cls-2"}

    rows = compute_source_impact(sources, classifications, response_map)

    assert [(r.domain, r.citations, r.direct_wins, r.impact_ratio) for r in rows] == [
        ("linear.app", 2, 1, 0.5),  # cited in both; won only once
        ("g2.com", 1, 1, 1.0),  # cited in the winning response only
    ]


def test_source_impact_ranks_by_citations_then_ratio() -> None:
    """Equal citation counts break ties by impact ratio (descending)."""
    sources = [
        _source("r1", "a.com"),
        _source("r1", "b.com"),
        _source("r2", "a.com"),  # a.com cited twice: both responses win
        _source("r3", "b.com"),  # b.com cited twice: wins only once
    ]
    classifications = [
        _classification("r1", Classification.DIRECT_WINNER),
        _classification("r2", Classification.DIRECT_WINNER),
        _classification("r3", Classification.OMITTED),
    ]
    response_map = {"r1": "r1", "r2": "r2", "r3": "r3"}

    rows = compute_source_impact(sources, classifications, response_map)

    assert [r.domain for r in rows] == ["a.com", "b.com"]
    assert (rows[0].citations, rows[0].impact_ratio) == (2, 1.0)
    assert (rows[1].citations, rows[1].impact_ratio) == (2, 0.5)


def test_source_impact_excludes_unknown_domains() -> None:
    """Sources whose domain could not be parsed are excluded from the matrix —
    an unparseable title carries no attribution signal."""
    sources = [
        _source("r1", "linear.app"),
        _source("r1", ""),  # unknown domain
    ]
    classifications = [_classification("r1", Classification.DIRECT_WINNER)]
    response_map = {"r1": "r1"}

    rows = compute_source_impact(sources, classifications, response_map)

    assert len(rows) == 1
    assert rows[0].domain == "linear.app"


def test_source_impact_empty_inputs() -> None:
    """No sources, no classifications → empty matrix (never raises)."""
    assert compute_source_impact([], [], {}) == []


# ── Segments whose start_index is omitted ───────────────────────────────────
#
# Protobuf leaves an integer field out when it equals 0, so a support that
# begins at the very start of the answer arrives with no `start_index` at all.
# Measured against 100 stored responses: 47 of 321 supports (15%) look like
# this. They are also the ones that matter most — the opening sentence is
# where an answer engine names its recommendation.


def test_missing_start_index_is_read_as_zero() -> None:
    payload = {
        "grounding_supports": [
            {"segment": {"end_index": 42}, "grounding_chunk_indices": [0]},
        ]
    }
    supports = extract_supports(payload)
    assert len(supports) == 1
    assert supports[0].segment_start == 0
    assert supports[0].segment_end == 42


def test_missing_end_index_is_still_skipped() -> None:
    """An absent end has no such defensible default: 0 would make the segment
    empty and any other value would be invented."""
    payload = {"grounding_supports": [{"segment": {"start_index": 5}}]}
    assert extract_supports(payload) == []


def test_explicit_zero_start_still_works() -> None:
    payload = {"grounding_supports": [{"segment": {"start_index": 0, "end_index": 10}}]}
    assert extract_supports(payload)[0].segment_start == 0


# ── Search queries ──────────────────────────────────────────────────────────


def test_extract_search_queries() -> None:
    payload = {"web_search_queries": ["Linear vs Jira comparison", "best pm tool 2025"]}
    assert extract_search_queries(payload) == [
        "Linear vs Jira comparison",
        "best pm tool 2025",
    ]


def test_search_queries_absent_or_empty() -> None:
    assert extract_search_queries(None) == []
    assert extract_search_queries({}) == []
    assert extract_search_queries({"web_search_queries": None}) == []


def test_search_queries_are_trimmed_and_deduped_preserving_order() -> None:
    """The same query recurs across the N samples of one prompt; a panel wants
    each distinct query once, in the order the model first ran it."""
    payload = {
        "web_search_queries": ["  best pm tool  ", "Linear vs Jira", "best pm tool", ""],
    }
    assert extract_search_queries(payload) == ["best pm tool", "Linear vs Jira"]


def test_aggregate_search_queries_counts_across_responses() -> None:
    payloads = [
        {"web_search_queries": ["Linear vs Jira", "best pm tool"]},
        {"web_search_queries": ["Linear vs Jira"]},
        None,
        {"web_search_queries": ["Linear vs Jira", "best pm tool"]},
    ]
    rows = aggregate_search_queries(payloads)
    assert [(r.query, r.count) for r in rows] == [
        ("Linear vs Jira", 3),
        ("best pm tool", 2),
    ]


def test_aggregate_search_queries_empty() -> None:
    assert aggregate_search_queries([]) == []
    assert aggregate_search_queries([None, {}]) == []
