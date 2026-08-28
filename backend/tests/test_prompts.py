"""Tests for the prompt corpus citation suffix.

Every corpus prompt ends with the same citation instruction so Gemini's
grounding consistently cites sources with titles and domains — and so inverted
pairs stay symmetric (a pair differs only in brand wording, never in the
citation instruction).
"""

import pytest

from aeo_engine.prompts import generate_corpus

# Pinned verbatim on purpose: rewording the instruction is a behavior change
# that must be deliberate.
CITATION_SUFFIX = " If you consult sources, cite them with titles and source domains."

BRAND = "Linear"
CATEGORY = "project management"
COMPETITORS = ["Jira", "Monday.com"]


def _corpus() -> list:
    return generate_corpus(BRAND, CATEGORY, COMPETITORS)


def test_all_corpus_prompts_end_with_citation_instruction() -> None:
    """Every one of the 20 prompts carries the citation suffix at the end."""
    corpus = _corpus()
    assert len(corpus) == 20
    assert all(p.text.endswith(CITATION_SUFFIX) for p in corpus)


def test_citation_instruction_appears_exactly_once() -> None:
    """The suffix is appended exactly once — never duplicated or mid-text."""
    corpus = _corpus()
    assert all(p.text.count(CITATION_SUFFIX) == 1 for p in corpus)


def test_inverted_pairs_keep_citation_instruction() -> None:
    """Base and inverted prompts of the same pair still end with the exact
    same suffix — the instruction is brand-order independent."""
    corpus = _corpus()
    by_id = {p.id: p for p in corpus}
    pairs = [p for p in corpus if p.inverted]
    assert len(pairs) == 10
    for inverted in pairs:
        base = by_id[inverted.id.replace("-inv", "")]
        assert base.text.endswith(CITATION_SUFFIX)
        assert inverted.text.endswith(CITATION_SUFFIX)
        # Pair symmetry: same suffix tail; only the brand wording differs.
        assert base.text[-len(CITATION_SUFFIX) :] == inverted.text[-len(CITATION_SUFFIX) :]


def test_every_prompt_type_is_suffixed() -> None:
    """All five prompt dimensions carry the instruction (not just direct)."""
    corpus = _corpus()
    types = {p.prompt_type for p in corpus}
    assert len(types) == 5  # direct, comparative, use_case, feature, negative
    assert all(p.text.endswith(CITATION_SUFFIX) for p in corpus)


# ── Category neutrality ─────────────────────────────────────────────────────
#
# ADR-012 makes the engine generic in the *brand*. The corpus was not generic
# in the *category*: every one of the five types assumed B2B software bought by
# a team ("tool", "platform", "10 engineers", "sprint planning and bug
# tracking", "developer experience", "keyboard-driven workflow"). Running an
# airline or a beer through it produced questions that measure nothing — a real
# stored run searched for "LATAM Airlines sprint planning bug tracking".

# Vocabulary that presumes the thing being measured is software for a team.
SOFTWARE_VOCABULARY = [
    "tool",
    "platform",
    "engineer",
    "developer",
    "sprint",
    "bug tracking",
    "keyboard",
    "integration",
    "team",
    "workflow",
]

NON_SOFTWARE_CASES = [
    ("Guinness", "beer", ["Heineken", "Corona", "Stella Artois"]),
    ("SKY Airline", "airlines", ["LATAM", "JetSMART", "Avianca"]),
    ("Mercadona", "supermarkets", ["Carrefour", "Lidl", "Aldi"]),
    ("Toyota", "cars", ["Honda", "Ford", "Volkswagen"]),
]


@pytest.mark.parametrize(("brand", "category", "competitors"), NON_SOFTWARE_CASES)
def test_corpus_carries_no_software_vocabulary(
    brand: str, category: str, competitors: list[str]
) -> None:
    """No prompt may presume the category is software bought by a team."""
    corpus = generate_corpus(brand, category, competitors)
    offenders = [
        (p.id, word, p.text)
        for p in corpus
        for word in SOFTWARE_VOCABULARY
        if word in p.text.lower()
    ]
    assert not offenders, f"software vocabulary leaked into {category}: " + "; ".join(
        f"{pid} contains {word!r}" for pid, word, _ in offenders[:5]
    )


@pytest.mark.parametrize(("brand", "category", "competitors"), NON_SOFTWARE_CASES)
def test_every_prompt_still_names_the_category_or_the_brands(
    brand: str, category: str, competitors: list[str]
) -> None:
    """Neutrality must not become vagueness: a prompt with neither the category
    nor a brand in it is not asking about anything measurable."""
    corpus = generate_corpus(brand, category, competitors)
    for prompt in corpus:
        text = prompt.text.lower()
        named = category.lower() in text or any(b.lower() in text for b in [brand, *competitors])
        assert named, f"{prompt.id} names neither category nor any brand: {prompt.text}"


def test_corpus_is_deterministic() -> None:
    """The corpus is the instrument (ADR-024). Two calls with the same inputs
    must produce byte-identical prompts, or two evaluations are not comparable
    and `GET /api/prompts` does not describe what was actually sent."""
    args = ("Guinness", "beer", ["Heineken", "Corona", "Stella Artois"])
    first = [(p.id, p.text) for p in generate_corpus(*args)]
    second = [(p.id, p.text) for p in generate_corpus(*args)]
    assert first == second


def test_corpus_size_is_unchanged_for_any_category() -> None:
    """5 types x 2 phrasings x 2 orderings = 20. The denominator must not move,
    or results across categories stop being comparable."""
    for brand, category, competitors in NON_SOFTWARE_CASES:
        assert len(generate_corpus(brand, category, competitors)) == 20
