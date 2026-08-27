"""Source Auditor: pure extraction of Gemini grounding into citable sources.

All functions are pure — no I/O, no hidden state, deterministic. They consume
`GeminiResponse.grounding_metadata` (the JSON-serialized Google Search
grounding) and produce source/support candidates; persistence happens in
`database.py`, impact ranking in `compute_source_impact`.

Empirical notes driving this module (from grounding exploration):
- Grounding presence is stochastic (~20-30% of calls) — callers treat None as
  "no grounding" and the pipeline degrades gracefully.
- `web.uri` is an opaque redirect token; the real attribution signal lives in
  `grounding_chunks[].web.title`, so domain extraction is TITLE-based.
- `grounding_supports[].segment` carries `start_index`/`end_index` offsets into
  the response text.
- `web_search_queries` is often empty and is not used for attribution.
"""

from __future__ import annotations

import re

from aeo_engine.models import GroundingSource, GroundingSupport

# Best-effort first domain-like token: label.host with a 2+ letter TLD.
# e.g. "Linear Review 2025 - linear.app" -> "linear.app"; prose without a
# domain-like token yields "". Documented limitation: this is a heuristic, not
# a registered-suffix parse.
_TITLE_DOMAIN_RE = re.compile(
    r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,63})\b",
    re.IGNORECASE,
)


def extract_domain(web_title: str) -> str:
    """Parse the first domain-like token from a web title; ``""`` when unparseable.

    The Google Search grounding URI is an opaque redirect token, so attribution
    is derived from the chunk's ``web.title``. Titles without a domain-like
    token (e.g. "An article without a domain") yield ``""``.
    """
    match = _TITLE_DOMAIN_RE.search(web_title)
    return match.group(1).lower() if match else ""


def extract_sources(grounding_metadata: dict | None) -> list[GroundingSource]:
    """Extract one :class:`GroundingSource` per grounding chunk with a web title.

    Chunks without a ``web.title`` cannot be attributed and are skipped.
    ``response_id`` is left empty — the persistence caller assigns it.
    """
    if not grounding_metadata:
        return []
    chunks = grounding_metadata.get("grounding_chunks") or []
    sources: list[GroundingSource] = []
    for index, chunk in enumerate(chunks):
        web = chunk.get("web") or {}
        title = (web.get("title") or "").strip()
        if not title:
            continue  # a chunk without a web title cannot be attributed
        sources.append(
            GroundingSource(
                web_title=title,
                domain=extract_domain(title),
                chunk_index=index,
            )
        )
    return sources


def extract_supports(grounding_metadata: dict | None) -> list[GroundingSupport]:
    """Extract one :class:`GroundingSupport` per grounding support segment.

    A support may cite several chunks (``grounding_chunk_indices``); it links to
    its FIRST cited chunk only — segment offsets are preserved regardless.
    Supports without ``start_index``/``end_index`` are skipped.
    """
    if not grounding_metadata:
        return []
    supports = grounding_metadata.get("grounding_supports") or []
    result: list[GroundingSupport] = []
    for support in supports:
        segment = support.get("segment") or {}
        start = segment.get("start_index")
        end = segment.get("end_index")
        if start is None or end is None:
            continue
        chunk_indices = support.get("grounding_chunk_indices") or []
        result.append(
            GroundingSupport(
                segment_start=int(start),
                segment_end=int(end),
                source_chunk_index=chunk_indices[0] if chunk_indices else None,
            )
        )
    return result