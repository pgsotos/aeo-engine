"""Multi-dimension prompt corpus for AEO evaluation.

Prompt types:
  - direct:       General "best tool" recommendation queries
  - comparative:  Head-to-head brand comparisons
  - use_case:     Specific context / use-case queries
  - feature:      Feature-specific queries
  - negative:     Negative framing (stress test brand resilience)

Each type has symmetric pairs (brand order swapped) to isolate positional bias.
"""

from aeo_engine.models import PromptRecord, PromptType

_FOCUS_BRAND = "Linear"
_COMPETITORS = ["Jira", "Asana", "Monday", "Notion"]
_ALL_BRANDS = [_FOCUS_BRAND] + _COMPETITORS

# ── Direct prompts ──────────────────────────────────────────────────────────

_DIRECT = [
    PromptRecord(
        id="direct-01",
        prompt_type=PromptType.DIRECT,
        text=(
            "What is the best project management tool in 2025? "
            "Consider Linear, Jira, Asana, Monday, and Notion. "
            "Recommend the top one and explain why."
        ),
    ),
    PromptRecord(
        id="direct-01-inv",
        prompt_type=PromptType.DIRECT,
        text=(
            "What is the best project management tool in 2025? "
            "Consider Jira, Linear, Asana, Monday, and Notion. "
            "Recommend the top one and explain why."
        ),
        inverted=True,
    ),
    PromptRecord(
        id="direct-02",
        prompt_type=PromptType.DIRECT,
        text=(
            "If you could only pick one project management platform "
            "for a software team, which would it be among "
            "Linear, Jira, Asana, Monday, and Notion?"
        ),
    ),
    PromptRecord(
        id="direct-02-inv",
        prompt_type=PromptType.DIRECT,
        text=(
            "If you could only pick one project management platform "
            "for a software team, which would it be among "
            "Jira, Linear, Asana, Monday, and Notion?"
        ),
        inverted=True,
    ),
]

# ── Comparative prompts ─────────────────────────────────────────────────────

_COMPARATIVE = [
    PromptRecord(
        id="comp-01",
        prompt_type=PromptType.COMPARATIVE,
        text="Linear vs Jira: which one is better for a growing software team and why?",
    ),
    PromptRecord(
        id="comp-01-inv",
        prompt_type=PromptType.COMPARATIVE,
        text="Jira vs Linear: which one is better for a growing software team and why?",
        inverted=True,
    ),
    PromptRecord(
        id="comp-02",
        prompt_type=PromptType.COMPARATIVE,
        text=(
            "I'm choosing between Linear and Notion for issue tracking. "
            "Which should I pick and what are the key differences?"
        ),
    ),
    PromptRecord(
        id="comp-02-inv",
        prompt_type=PromptType.COMPARATIVE,
        text=(
            "I'm choosing between Notion and Linear for issue tracking. "
            "Which should I pick and what are the key differences?"
        ),
        inverted=True,
    ),
]

# ── Use-case prompts ────────────────────────────────────────────────────────

_USE_CASE = [
    PromptRecord(
        id="uc-01",
        prompt_type=PromptType.USE_CASE,
        text=(
            "What's the best project management tool for a startup "
            "of 10 software engineers that moves fast and values simplicity?"
        ),
    ),
    PromptRecord(
        id="uc-01-inv",
        prompt_type=PromptType.USE_CASE,
        text=(
            "What's the best project management tool for a startup "
            "of 10 software engineers that values simplicity and moves fast?"
        ),
        inverted=True,
    ),
    PromptRecord(
        id="uc-02",
        prompt_type=PromptType.USE_CASE,
        text=(
            "We're a remote team of 25 developers. We need something "
            "for sprint planning and bug tracking. What do you recommend "
            "from Linear, Jira, Asana, Monday, or Notion?"
        ),
    ),
    PromptRecord(
        id="uc-02-inv",
        prompt_type=PromptType.USE_CASE,
        text=(
            "We're a remote team of 25 developers. We need something "
            "for sprint planning and bug tracking. What do you recommend "
            "from Jira, Linear, Asana, Monday, or Notion?"
        ),
        inverted=True,
    ),
]

# ── Feature prompts ─────────────────────────────────────────────────────────

_FEATURE = [
    PromptRecord(
        id="feat-01",
        prompt_type=PromptType.FEATURE,
        text=(
            "Which project management tool has the best developer experience "
            "and keyboard-driven workflow? Compare Linear, Jira, Asana, "
            "Monday, and Notion."
        ),
    ),
    PromptRecord(
        id="feat-01-inv",
        prompt_type=PromptType.FEATURE,
        text=(
            "Which project management tool has the best keyboard-driven workflow "
            "and developer experience? Compare Jira, Linear, Asana, "
            "Monday, and Notion."
        ),
        inverted=True,
    ),
    PromptRecord(
        id="feat-02",
        prompt_type=PromptType.FEATURE,
        text=(
            "I need a fast, minimal project management tool with good "
            "GitHub integration. Which is best: Linear, Jira, Asana, "
            "Monday, or Notion?"
        ),
    ),
    PromptRecord(
        id="feat-02-inv",
        prompt_type=PromptType.FEATURE,
        text=(
            "I need a minimal, fast project management tool with good "
            "GitHub integration. Which is best: Jira, Linear, Asana, "
            "Monday, or Notion?"
        ),
        inverted=True,
    ),
]

# ── Negative prompts ────────────────────────────────────────────────────────

_NEGATIVE = [
    PromptRecord(
        id="neg-01",
        prompt_type=PromptType.NEGATIVE,
        text=(
            "What are the reasons NOT to use Linear for project management? "
            "What are its weaknesses compared to Jira, Asana, Monday, and Notion?"
        ),
    ),
    PromptRecord(
        id="neg-01-inv",
        prompt_type=PromptType.NEGATIVE,
        text=(
            "What are the reasons NOT to use Linear for project management? "
            "What are its weaknesses compared to Notion, Monday, Asana, and Jira?"
        ),
        inverted=True,
    ),
    PromptRecord(
        id="neg-02",
        prompt_type=PromptType.NEGATIVE,
        text=(
            "I've heard Linear is overhyped. Convince me that Jira, Asana, "
            "Monday, or Notion would be a better choice for my team."
        ),
    ),
    PromptRecord(
        id="neg-02-inv",
        prompt_type=PromptType.NEGATIVE,
        text=(
            "I've heard Linear is overhyped. Convince me that Notion, Monday, "
            "Asana, or Jira would be a better choice for my team."
        ),
        inverted=True,
    ),
]

ALL_PROMPTS: list[PromptRecord] = _DIRECT + _COMPARATIVE + _USE_CASE + _FEATURE + _NEGATIVE

PROMPTS_BY_TYPE: dict[PromptType, list[PromptRecord]] = {
    pt: [p for p in ALL_PROMPTS if p.prompt_type == pt] for pt in PromptType
}

FOCUS_BRAND = _FOCUS_BRAND
COMPETITORS = _COMPETITORS
ALL_BRANDS = _ALL_BRANDS
