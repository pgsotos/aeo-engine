"""Tests for grounding persistence (Supabase REST wrapper, client mocked).

`save_grounding_sources` is the only function with real logic: it inserts
source rows, then links support rows to them via chunk_index. The Supabase
client is replaced by a recording fake so the exact insert payloads can be
asserted (behavior, not implementation).
"""

from unittest.mock import patch

from aeo_engine.database import (
    get_grounding_sources,
    get_grounding_supports,
    save_grounding_sources,
)
from aeo_engine.models import GroundingSource, GroundingSupport


class _FakeResult:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _FakeTable:
    """Records insert payloads; returns canned data on execute."""

    def __init__(self, result_data: list[dict]) -> None:
        self._result_data = result_data
        self.insert_payloads: list[list[dict]] = []

    def insert(self, rows: list[dict]) -> "_FakeTable":
        self.insert_payloads.append(rows)
        return self

    def execute(self) -> _FakeResult:
        return _FakeResult(self._result_data)


class _FakeClient:
    def __init__(self, sources_data: list[dict], supports_data: list[dict]) -> None:
        self.tables = {
            "grounding_sources": _FakeTable(sources_data),
            "grounding_supports": _FakeTable(supports_data),
        }
        self.lookup_by_name: list[tuple[str, _FakeTable]] = []

    def table(self, name: str) -> _FakeTable:
        self.lookup_by_name.append((name, self.tables[name]))
        return self.tables[name]


def _sources() -> list[GroundingSource]:
    return [
        GroundingSource(
            response_id="resp-1",
            web_title="Linear Review 2025 - linear.app",
            domain="linear.app",
            chunk_index=0,
        ),
        GroundingSource(
            response_id="resp-1",
            web_title="Compare Tools | G2.com",
            domain="g2.com",
            chunk_index=1,
        ),
    ]


def _supports() -> list[GroundingSupport]:
    return [
        GroundingSupport(
            response_id="resp-1", segment_start=0, segment_end=52, source_chunk_index=0
        ),
        GroundingSupport(
            response_id="resp-1", segment_start=60, segment_end=120, source_chunk_index=1
        ),
    ]


def test_save_grounding_sources_persists_rows_and_links_supports() -> None:
    """Sources are inserted first; supports carry source_id resolved by
    chunk_index from the inserted source rows."""
    fake = _FakeClient(
        sources_data=[
            {
                "id": "src-row-1",
                "response_id": "resp-1",
                "web_title": "Linear Review 2025 - linear.app",
                "domain": "linear.app",
            },
            {
                "id": "src-row-2",
                "response_id": "resp-1",
                "web_title": "Compare Tools | G2.com",
                "domain": "g2.com",
            },
        ],
        supports_data=[
            {
                "id": "sup-1",
                "response_id": "resp-1",
                "source_id": "src-row-1",
                "segment_start": 0,
                "segment_end": 52,
            },
            {
                "id": "sup-2",
                "response_id": "resp-1",
                "source_id": "src-row-2",
                "segment_start": 60,
                "segment_end": 120,
            },
        ],
    )

    with patch("aeo_engine.database.get_client", return_value=fake):
        result = save_grounding_sources("resp-1", _sources(), _supports())

    sources_table = fake.tables["grounding_sources"]
    supports_table = fake.tables["grounding_supports"]

    # Exact source payload: response_id + web_title + domain (no chunk_index leak).
    assert sources_table.insert_payloads == [
        [
            {
                "response_id": "resp-1",
                "web_title": "Linear Review 2025 - linear.app",
                "domain": "linear.app",
            },
            {"response_id": "resp-1", "web_title": "Compare Tools | G2.com", "domain": "g2.com"},
        ]
    ]
    # Supports link to the source row their chunk cited (chunk 0 -> src-row-1...).
    assert supports_table.insert_payloads == [
        [
            {
                "response_id": "resp-1",
                "source_id": "src-row-1",
                "segment_start": 0,
                "segment_end": 52,
            },
            {
                "response_id": "resp-1",
                "source_id": "src-row-2",
                "segment_start": 60,
                "segment_end": 120,
            },
        ]
    ]
    assert len(result["sources"]) == 2
    assert result["supports"] == fake.tables["grounding_supports"]._result_data


def test_save_grounding_sources_unresolved_support_gets_null_source() -> None:
    """A support whose chunk has no inserted source (e.g. chunk had no title)
    persists with source_id=None — segment offsets are kept."""
    fake = _FakeClient(
        sources_data=[{"id": "src-row-1", "response_id": "resp-1"}],
        supports_data=[
            {
                "id": "sup-1",
                "response_id": "resp-1",
                "source_id": None,
                "segment_start": 0,
                "segment_end": 52,
            }
        ],
    )
    supports = [
        GroundingSupport(
            response_id="resp-1", segment_start=0, segment_end=52, source_chunk_index=5
        )  # no source inserted for chunk 5
    ]

    with patch("aeo_engine.database.get_client", return_value=fake):
        save_grounding_sources("resp-1", _sources()[:1], supports)

    assert fake.tables["grounding_supports"].insert_payloads == [
        [{"response_id": "resp-1", "source_id": None, "segment_start": 0, "segment_end": 52}]
    ]


def test_save_grounding_sources_empty_never_touches_client() -> None:
    """No sources and no supports → empty result, client is never called."""
    with patch("aeo_engine.database.get_client") as mock_get:
        result = save_grounding_sources("resp-1", [], [])

    assert result == {"sources": [], "supports": []}
    mock_get.assert_not_called()


def test_get_grounding_sources_filters_by_response() -> None:
    """Getter returns source rows for one response, ordered by created_at."""
    response_id = "resp-1"
    fake_rows = [{"id": "src-row-1", "response_id": response_id, "domain": "linear.app"}]
    mock_client = _ChainMock(fake_rows)

    with patch("aeo_engine.database.get_client", return_value=mock_client):
        result = get_grounding_sources(response_id)

    assert result == fake_rows
    assert mock_client.last_filters == [
        ("eq", ("response_id", response_id)),
        ("order", ("created_at",)),
    ]


def test_get_grounding_supports_filters_by_response() -> None:
    """Getter returns support rows for one response, ordered by segment_start."""
    response_id = "resp-1"
    fake_rows = [{"id": "sup-1", "response_id": response_id, "segment_start": 0, "segment_end": 52}]
    mock_client = _ChainMock(fake_rows)

    with patch("aeo_engine.database.get_client", return_value=mock_client):
        result = get_grounding_supports(response_id)

    assert result == fake_rows
    assert ("eq", ("response_id", response_id)) in mock_client.last_filters
    assert ("order", ("segment_start",)) in mock_client.last_filters


class _ChainMock:
    """Records the query-builder chain: table → select → eq → order → execute."""

    def __init__(self, data: list[dict]) -> None:
        self._data = data
        self.last_filters: list[tuple[str, tuple]] = []
        self.table_name = None

    def table(self, name: str) -> "_ChainMock":
        self.table_name = name
        return self

    def select(self, _cols: str) -> "_ChainMock":
        return self

    def eq(self, col: str, value: str) -> "_ChainMock":
        self.last_filters.append(("eq", (col, value)))
        return self

    def order(self, col: str, desc: bool = False) -> "_ChainMock":
        self.last_filters.append(("order", (col,)))
        return self

    def execute(self) -> _FakeResult:
        return _FakeResult(self._data)
