"""Gemini API client for AEO evaluation."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from google import genai
from google.genai import types

from aeo_engine.config import settings
from aeo_engine.models import GeminiResponse


def _get_client() -> genai.Client:
    """Create a Gemini client from settings."""
    return genai.Client(api_key=settings.gemini_api_key)


async def call_gemini(
    prompt: str,
    evaluation_id: str,
    prompt_id: str,
    run_index: int,
    model: str = "gemini-2.0-flash",
) -> GeminiResponse:
    """Make a single async call to Gemini and return the raw response.

    Uses asyncio.to_thread to run the synchronous google-genai client
    without blocking the event loop.
    """

    def _sync_call() -> str:
        client = _get_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        return response.text or ""

    raw_text = await asyncio.to_thread(_sync_call)

    return GeminiResponse(
        id=str(uuid.uuid4()),
        evaluation_id=evaluation_id,
        prompt_id=prompt_id,
        run_index=run_index,
        model_id=model,
        raw_text=raw_text,
        created_at=datetime.utcnow(),
    )


async def run_parallel_sampling(
    prompt: str,
    prompt_id: str,
    evaluation_id: str,
    n: int = 8,
    model: str = "gemini-2.0-flash",
    concurrency: int = 4,
) -> list[GeminiResponse]:
    """Run N independent calls to Gemini with bounded concurrency.

    Uses asyncio.Semaphore to avoid hammering the API rate limit.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded_call(run_idx: int) -> GeminiResponse:
        async with semaphore:
            return await call_gemini(prompt, evaluation_id, prompt_id, run_idx + 1, model)

    tasks = [_bounded_call(i) for i in range(n)]
    return await asyncio.gather(*tasks)
