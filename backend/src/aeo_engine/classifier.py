"""Response classifier: determines how a brand appears in a Gemini response.

Classification rules (deterministic, pure function over raw_text):
  - DIRECT_WINNER: brand is the #1 recommendation or appears first/prominently
  - ALTERNATIVE_MENTION: brand appears but not as the primary recommendation
  - OMITTED: brand is not mentioned at all
"""

from __future__ import annotations

import re
import uuid

from aeo_engine.models import Classification, ClassificationResult


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation for matching."""
    return re.sub(r"[^\w\s]", "", text.lower())


def _count_mentions(normalized: str, brand: str) -> int:
    """Count how many times a brand is mentioned in the text."""
    return len(re.findall(rf"\b{re.escape(brand.lower())}\b", normalized))


def _first_mention_position(raw_text: str, brand: str) -> int | None:
    """Return the character offset of the brand's first mention, or None."""
    match = re.search(rf"\b{re.escape(brand)}\b", raw_text, re.IGNORECASE)
    return match.start() if match else None


def _is_primary_recommendation(raw_text: str, brand: str) -> bool:
    """Check if the brand is the primary recommendation.

    Heuristics:
    - Brand appears in the first 20% of the response
    - Brand is mentioned with recommendation keywords nearby
    """
    normalized = _normalize(raw_text)
    brand_lower = brand.lower()

    if brand_lower not in normalized:
        return False

    # Check position: is brand in the first 20% of the text?
    pos = _first_mention_position(raw_text, brand)
    if pos is None:
        return False

    text_len = len(raw_text)
    in_first_portion = pos < text_len * 0.25

    # Check for recommendation keywords near the brand mention
    # Look at a window around the first mention
    window_start = max(0, pos - 100)
    window_end = min(text_len, pos + len(brand) + 100)
    window = raw_text[window_start:window_end].lower()

    recommendation_keywords = [
        "recommend",
        "best choice",
        "top pick",
        "i'd choose",
        "i would choose",
        "go with",
        "the best",
        "stands out",
        "top option",
        "number one",
        "#1",
        "first choice",
        "primary",
        "leading",
        "superior",
    ]
    # Negative signals that override recommendation detection
    negative_signals = [
        "alternative",
        "however",
        "but",
        "although",
        "while",
        "instead",
        "compared to",
        "not as",
    ]

    has_recommendation_signal = any(kw in window for kw in recommendation_keywords)
    has_negative_signal = any(ns in window for ns in negative_signals)

    # If there's both a recommendation keyword AND a negative signal,
    # it's likely an alternative mention, not a primary recommendation
    if has_recommendation_signal and has_negative_signal:
        return in_first_portion and not has_negative_signal

    return in_first_portion or has_recommendation_signal


def classify_response(raw_text: str, brand: str) -> ClassificationResult:
    """Classify how a brand appears in a Gemini response.

    This is a pure function: same input → same output.
    """
    normalized = _normalize(raw_text)
    brand_lower = brand.lower()

    mention_count = _count_mentions(normalized, brand_lower)
    first_pos = _first_mention_position(raw_text, brand)

    if mention_count == 0:
        return ClassificationResult(
            response_id=str(uuid.uuid4()),
            brand=brand,
            classification=Classification.OMITTED,
            first_mention_position=None,
            mention_count=0,
            confidence_score=1.0,  # high confidence: brand is simply not there
        )

    if _is_primary_recommendation(raw_text, brand):
        return ClassificationResult(
            response_id=str(uuid.uuid4()),
            brand=brand,
            classification=Classification.DIRECT_WINNER,
            first_mention_position=first_pos,
            mention_count=mention_count,
            confidence_score=0.85,
        )

    return ClassificationResult(
        response_id=str(uuid.uuid4()),
        brand=brand,
        classification=Classification.ALTERNATIVE_MENTION,
        first_mention_position=first_pos,
        mention_count=mention_count,
        confidence_score=0.75,
    )


def classify_all_brands(raw_text: str, brands: list[str]) -> list[ClassificationResult]:
    """Classify a single response against all brands."""
    return [classify_response(raw_text, brand) for brand in brands]
