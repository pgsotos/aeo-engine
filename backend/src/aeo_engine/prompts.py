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

import random

from aeo_engine.models import PromptRecord, PromptType


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
    Total: 5 types × 4 = 20 prompts.
    """
    all_brands = [brand] + competitors
    corpus: list[PromptRecord] = []

    # ── Direct prompts ──────────────────────────────────────────────────

    direct_templates = [
        (
            "What is the best {category} tool in 2025? "
            "Consider {brand_list}. Recommend the top one and explain why."
        ),
        (
            "If you could only pick one {category} platform "
            "for your team, which would it be among {brand_list}?"
        ),
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
        (
            "{brand} vs {competitor}: which one is better "
            "for a growing team and why?"
        ),
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
                text=template.format(
                    brand=brand, competitor=competitor, category=category
                ),
            )
        )
        corpus.append(
            PromptRecord(
                id=_id("comp", i, inverted=True),
                prompt_type=PromptType.COMPARATIVE,
                text=template.format(
                    brand=competitor, competitor=brand, category=category
                ),
                inverted=True,
            )
        )

    # ── Use-case prompts ────────────────────────────────────────────────

    use_case_templates = [
        (
            "What's the best {category} tool for a startup "
            "of 10 engineers that moves fast and values simplicity?"
        ),
        (
            "We're a remote team of 25 developers. We need something "
            "for sprint planning and bug tracking. What do you recommend "
            "from {brand_list}?"
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

    feature_templates = [
        (
            "Which {category} tool has the best developer experience "
            "and keyboard-driven workflow? Compare {brand_list}."
        ),
        (
            "I need a fast, minimal {category} tool with good "
            "integration. Which is best: {brand_list}?"
        ),
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
            "What are the reasons NOT to use {brand} for {category}? "
            "What are its weaknesses compared to {competitor_list}?"
        ),
        (
            "I've heard {brand} is overhyped. Convince me that "
            "{competitor_list} would be a better choice for my team."
        ),
    ]

    for i, template in enumerate(negative_templates, 1):
        competitor_list = ", ".join(competitors)
        # For the second prompt, shuffle competitor order for variety
        shuffled = competitors.copy()
        random.shuffle(shuffled)
        shuffled_list = ", ".join(shuffled)
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

    return corpus


def get_corpus_by_type(
    corpus: list[PromptRecord],
) -> dict[PromptType, list[PromptRecord]]:
    """Group prompts by type."""
    return {
        pt: [p for p in corpus if p.prompt_type == pt]
        for pt in PromptType
    }
