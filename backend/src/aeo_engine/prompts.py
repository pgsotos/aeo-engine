"""Multi-dimension prompt corpus for AEO evaluation.

Prompts are GENERIC templates. No brand or category is hardcoded.
The corpus is generated dynamically for any brand + category + competitors.

Prompt types:
  - direct:       General "best tool" recommendation queries
  - comparative:  Head-to-head brand comparisons
  - use_case:     Specific context / use-case queries
  - feature:      Feature-specific queries
  - negative:     Negative framing (stress test brand resilience)
"""

from __future__ import annotations

from aeo_engine.models import PromptRecord, PromptType

CITATION_SUFFIX = " If you consult sources, cite them with titles and source domains."


def _id(prefix: str, index: int, inverted: bool = False) -> str:
    suffix = "-inv" if inverted else ""
    return f"{prefix}-{index:02d}{suffix}"


def generate_corpus(
    brand: str,
    category: str,
    competitors: list[str],
) -> list[PromptRecord]:
    """Generate the full prompt corpus for any brand + category + competitors.

    Each prompt type has 2 base prompts × 2 orderings = 4 prompts per type.
    Total: 5 types × 4 = 20 prompts. Every prompt is suffixed with the same
    citation instruction so Gemini grounding cites sources with titles and
    domains — appended identically to base and inverted prompts to preserve
    competitive symmetry.
    """
    all_brands = [brand] + competitors
    corpus: list[PromptRecord] = []

    # ── Direct prompts ──────────────────────────────────────────────────

    # Every template below is category-neutral on purpose: no "tool",
    # "platform", "team" or any other word that presumes the category is
    # software bought by a company. The same twenty questions have to mean
    # something for a beer, an airline and a supermarket (ADR-028).
    #
    # `{category}` also only ever appears AFTER A PREPOSITION. It may arrive as
    # a mass noun ("beer"), a plural ("automobiles") or a plural phrase
    # ("project management tools"), and no English article or number agreement
    # holds for all three — "the best automobiles" and "Which beer option" both
    # came out wrong. After a preposition the category is a topic rather than a
    # noun phrase, and every shape reads correctly.
    direct_templates = [
        (
            "As of 2025, what is the best choice in {category}? "
            "Consider {brand_list}. Recommend the top one and explain why."
        ),
        ("If you could only pick one option in {category}, which would it be among {brand_list}?"),
    ]

    for i, template in enumerate(direct_templates, 1):
        brand_list = ", ".join(all_brands)
        inverted_list = ", ".join([competitors[0], brand] + competitors[1:])
        corpus.append(
            PromptRecord(
                id=_id("direct", i),
                prompt_type=PromptType.DIRECT,
                text=template.format(category=category, brand_list=brand_list),
            )
        )
        corpus.append(
            PromptRecord(
                id=_id("direct", i, inverted=True),
                prompt_type=PromptType.DIRECT,
                text=template.format(category=category, brand_list=inverted_list),
                inverted=True,
            )
        )

    # ── Comparative prompts ─────────────────────────────────────────────

    comparative_templates = [
        ("{brand} vs {competitor}: which one is better, and why?"),
        (
            "I'm choosing between {brand} and {competitor} for {category}. "
            "Which should I pick and what are the key differences?"
        ),
    ]

    for i, template in enumerate(comparative_templates, 1):
        competitor = competitors[0]
        corpus.append(
            PromptRecord(
                id=_id("comp", i),
                prompt_type=PromptType.COMPARATIVE,
                text=template.format(brand=brand, competitor=competitor, category=category),
            )
        )
        corpus.append(
            PromptRecord(
                id=_id("comp", i, inverted=True),
                prompt_type=PromptType.COMPARATIVE,
                text=template.format(brand=competitor, competitor=brand, category=category),
                inverted=True,
            )
        )

    # ── Use-case prompts ────────────────────────────────────────────────

    # The use-case dimension needs a *situation*, and the only situations that
    # transfer across every category are the buyer's: choosing for the first
    # time, and choosing on price. Sharper, domain-specific scenarios would
    # measure more per category but stop being comparable between them.
    use_case_templates = [
        (
            "I'm new to {category} and don't know the market. "
            "Which of {brand_list} would you recommend, and why?"
        ),
        (
            "I want the best value for money in {category}. "
            "Which would you recommend from {brand_list}?"
        ),
    ]

    for i, template in enumerate(use_case_templates, 1):
        brand_list = ", ".join(all_brands)
        inverted_list = ", ".join([competitors[0], brand] + competitors[1:])
        corpus.append(
            PromptRecord(
                id=_id("uc", i),
                prompt_type=PromptType.USE_CASE,
                text=template.format(category=category, brand_list=brand_list),
            )
        )
        corpus.append(
            PromptRecord(
                id=_id("uc", i, inverted=True),
                prompt_type=PromptType.USE_CASE,
                text=template.format(category=category, brand_list=inverted_list),
                inverted=True,
            )
        )

    # ── Feature prompts ─────────────────────────────────────────────────

    # The feature dimension needs an *attribute*. Quality and reliability are
    # the two that every category has an answer for; anything more specific
    # (latency, horsepower, alcohol content) would have to vary per category
    # and break the fixed corpus.
    feature_templates = [
        (
            "Which of {brand_list} is the highest quality in {category}, "
            "and what makes it stand out?"
        ),
        ("Which of {brand_list} is the most reliable in {category}? Explain what separates them."),
    ]

    for i, template in enumerate(feature_templates, 1):
        brand_list = ", ".join(all_brands)
        inverted_list = ", ".join([competitors[0], brand] + competitors[1:])
        corpus.append(
            PromptRecord(
                id=_id("feat", i),
                prompt_type=PromptType.FEATURE,
                text=template.format(category=category, brand_list=brand_list),
            )
        )
        corpus.append(
            PromptRecord(
                id=_id("feat", i, inverted=True),
                prompt_type=PromptType.FEATURE,
                text=template.format(category=category, brand_list=inverted_list),
                inverted=True,
            )
        )

    # ── Negative prompts ────────────────────────────────────────────────

    negative_templates = [
        (
            "What are the reasons NOT to choose {brand} for {category}? "
            "What are its weaknesses compared to {competitor_list}?"
        ),
        (
            "I've heard {brand} is overrated. Convince me that "
            "{competitor_list} would be a better choice."
        ),
    ]

    for i, template in enumerate(negative_templates, 1):
        competitor_list = ", ".join(competitors)
        # A second, different ordering for variety — reversed, not shuffled.
        # random.shuffle made the corpus differ between calls, so two
        # evaluations of the same brand were not sampling the same instrument
        # and `GET /api/prompts` did not describe what had actually been sent.
        shuffled_list = ", ".join(reversed(competitors))
        corpus.append(
            PromptRecord(
                id=_id("neg", i),
                prompt_type=PromptType.NEGATIVE,
                text=template.format(
                    brand=brand,
                    category=category,
                    competitor_list=competitor_list,
                ),
            )
        )
        corpus.append(
            PromptRecord(
                id=_id("neg", i, inverted=True),
                prompt_type=PromptType.NEGATIVE,
                text=template.format(
                    brand=brand,
                    category=category,
                    competitor_list=shuffled_list,
                ),
                inverted=True,
            )
        )

    # ── Citation instruction ────────────────────────────────────────────
    # Single suffix for ALL prompts (including inverted pairs) so grounding
    # captures citable sources and pair symmetry is preserved.

    return [p.model_copy(update={"text": f"{p.text}{CITATION_SUFFIX}"}) for p in corpus]


def get_corpus_by_type(
    corpus: list[PromptRecord],
) -> dict[PromptType, list[PromptRecord]]:
    """Group prompts by type."""
    return {pt: [p for p in corpus if p.prompt_type == pt] for pt in PromptType}
