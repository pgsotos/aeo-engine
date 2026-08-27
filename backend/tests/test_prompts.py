"""Tests for the prompt corpus citation suffix.

Every corpus prompt ends with the same citation instruction so Gemini's
grounding consistently cites sources with titles and domains — and so inverted
pairs stay symmetric (a pair differs only in brand wording, never in the
citation instruction).
"""

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
