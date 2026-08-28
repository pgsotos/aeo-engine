"""Gemini API client for AEO evaluation."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from google import genai
from google.genai import types

from aeo_engine.config import settings
from aeo_engine.models import Competitor, GeminiResponse

DEFAULT_MODEL = "gemini-3.6-flash"
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds; grows 3x per attempt

# Residue defense for category resolves: the low token cap can truncate an
# answer mid-sentence, leaking meta-language like "Select the…", and a model
# may regurgitate parts of the instruction itself ("no quotes", "lowercase").
# Keep the set small and conservative — a real category must never be rejected
# here (Retry is the recovery path when a legit token is over-aggressively
# dropped).
_META_BLACKLIST = (
    "select",
    "please",
    "here are",
    "here is",
    "and more",
    "such as",
    "examples include",
    "for example",
    "e.g.",
    "quotes",
    "lowercase",
    "nothing else",
    "comma-separated",
    "comma separated",
    "list of categories",
    "brand name",
    "bullets",
)
_MAX_CATEGORY_LEN = 50


def _clean_categories(
    raw: str,
    *,
    max_len: int = _MAX_CATEGORY_LEN,
    brand: str | None = None,
) -> list[str]:
    """Split a Gemini category response and drop meta-language/truncation residue.

    Pure function: strips surrounding whitespace/quotes, filters empty chunks,
    drops anything containing a conservative meta-language token, and caps each
    category's length. When ``brand`` is given, a chunk that is exactly the brand
    name echoed back (case-insensitive) is dropped too — lookalike categories
    such as "linear algebra" survive. No hidden state, no I/O.
    """
    categories: list[str] = []
    focus = brand.lower() if brand is not None else None
    for chunk in raw.split(","):
        cleaned = chunk.strip().strip('"').strip("'")
        lowered = cleaned.lower()
        if not cleaned or any(token in lowered for token in _META_BLACKLIST):
            continue
        if focus is not None and lowered == focus:
            continue
        categories.append(cleaned[:max_len])
    return categories


_SETUP_HINT = """
Gemini is not configured. Set this in backend/.env (see .env.example):

  GEMINI_API_KEY=<your key>

Create a key at https://aistudio.google.com/apikey — the free tier is enough.
"""


def _get_client() -> genai.Client:
    """Create a Gemini client from settings.

    Raises with setup instructions when the key is absent, rather than letting
    the SDK fail deep inside an evaluation.
    """
    if not settings.gemini_api_key:
        raise RuntimeError(f"Missing GEMINI_API_KEY.\n{_SETUP_HINT}")
    return genai.Client(api_key=settings.gemini_api_key)


def _is_transient(exc: Exception) -> bool:
    """Is this worth retrying?

    Rate limits (429) and 5xx blips pass. A 4xx — an invalid key, a malformed
    request — will fail identically every time, so retrying it only delays the
    error by the whole backoff sequence, multiplied by every call in flight.
    """
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status == 429 or status >= 500
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text or " 5" in text[:8]


async def _call_in_thread_with_retry(fn: Callable[[], str]) -> str:
    """Run a blocking Gemini call in a thread, retrying transient failures.

    Rate limits and brief 5xx blips are common under parallel load; a few
    backed-off retries absorb them without failing the whole evaluation.
    Anything else is raised immediately.
    """
    delay = _RETRY_BASE_DELAY
    for attempt in range(_MAX_RETRIES):
        try:
            return await asyncio.to_thread(fn)
        except Exception as exc:
            if attempt == _MAX_RETRIES - 1 or not _is_transient(exc):
                raise
            await asyncio.sleep(delay)
            delay *= 3
    raise RuntimeError("unreachable")  # pragma: no cover


async def call_gemini(
    prompt: str,
    evaluation_id: str,
    prompt_id: str,
    run_index: int,
    model: str = DEFAULT_MODEL,
) -> GeminiResponse:
    """Make a single async call to Gemini and return the raw response.

    Uses Chat API (recommended over Models.generate_content).
    Runs in a thread to avoid blocking the event loop.
    """

    def _sync_call() -> str:
        client = _get_client()
        chat = client.chats.create(
            model=model,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        response = chat.send_message(prompt)
        return response.text or ""

    raw_text = await _call_in_thread_with_retry(_sync_call)

    return GeminiResponse(
        id=str(uuid.uuid4()),
        evaluation_id=evaluation_id,
        prompt_id=prompt_id,
        run_index=run_index,
        model_id=model,
        raw_text=raw_text,
        created_at=datetime.now(UTC),
    )


async def resolve_brand_categories(brand: str) -> list[str]:
    """Ask Gemini what product/service categories a brand belongs to.

    Returns a list of category strings. Uses low temperature for consistency.
    This is a single cheap call — not part of the evaluation pipeline.
    """

    prompt = (
        f'What product or service categories does the brand "{brand}" belong to?\n'
        "Respond with ONLY a comma-separated list of category names.\n"
        "Do not include quotes, bullets, numbering, examples, explanations, or "
        "the brand name itself. Use lowercase.\n"
        "Output format: category1, category2, category3\n"
        "For a brand like Notion, the entire answer must be exactly:\n"
        "note-taking, project management, documentation, knowledge base"
    )

    def _sync_call() -> str:
        client = _get_client()
        chat = client.chats.create(
            model=DEFAULT_MODEL,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=512,
            ),
        )
        response = chat.send_message(prompt)
        return response.text or ""

    raw = await asyncio.to_thread(_sync_call)

    # Parse + clean the comma-separated response: drop meta-language/truncation
    # residue and cap each category's length. Pass the focus brand so an exact
    # echo of the brand name is never mistaken for a category.
    return _clean_categories(raw, brand=brand)


async def resolve_brand_competitors(brand: str, category: str) -> list[Competitor]:
    """Ask Gemini who the main competitors are for a brand in a category.

    Returns a list of Competitor objects with name and reason.
    Parses line-based format: "BrandName: brief reason"
    """

    prompt = (
        f"Competitors of {brand} in {category}:\n"
        "1. Name: reason\n2. Name: reason\n3. Name: reason\n4. Name: reason"
    )

    def _sync_call() -> str:
        client = _get_client()
        chat = client.chats.create(
            model=DEFAULT_MODEL,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        response = chat.send_message(prompt)
        return response.text or ""

    raw = await asyncio.to_thread(_sync_call)

    competitors = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Remove list markers: "1. ", "- ", "* "
        line = line.lstrip("-").lstrip("*").strip()
        if line and line[0].isdigit() and ". " in line:
            line = line.split(". ", 1)[1]
        if ":" in line:
            parts = line.split(":", 1)
            name = parts[0].strip().strip('"').strip("'").replace("**", "")
            reason = parts[1].strip().strip('"').strip("'").rstrip(".").replace("**", "")
            if name and reason and len(name) < 50:
                competitors.append(Competitor(name=name, reason=reason))

    return competitors


async def run_parallel_sampling(
    prompt: str,
    prompt_id: str,
    evaluation_id: str,
    n: int = 8,
    model: str = DEFAULT_MODEL,
    concurrency: int = 4,
    semaphore: asyncio.Semaphore | None = None,
) -> list[GeminiResponse]:
    """Run N independent calls to Gemini with bounded concurrency.

    Pass a shared ``semaphore`` to cap concurrency across a whole evaluation
    (many prompts sampled at once); otherwise a local one of size
    ``concurrency`` is used.
    """
    sem = semaphore or asyncio.Semaphore(concurrency)

    async def _bounded_call(run_idx: int) -> GeminiResponse:
        async with sem:
            return await call_gemini(prompt, evaluation_id, prompt_id, run_idx + 1, model)

    tasks = [_bounded_call(i) for i in range(n)]
    return await asyncio.gather(*tasks)
