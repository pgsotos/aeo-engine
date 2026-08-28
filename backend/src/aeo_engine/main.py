"""FastAPI application for the AEO engine."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aeo_engine.classifier import classify_all_brands
from aeo_engine.config import settings
from aeo_engine.database import (
    create_evaluation,
    get_classifications,
    get_evaluation,
    get_metrics,
    get_responses,
    list_evaluations,
    save_classifications,
    save_metrics,
    save_responses,
    update_evaluation,
)
from aeo_engine.gemini import (
    resolve_brand_categories,
    resolve_brand_competitors,
    run_parallel_sampling,
)
from aeo_engine.metrics import compute_per_type_metrics
from aeo_engine.models import Evaluation, PromptRecord, PromptType
from aeo_engine.prompts import generate_corpus, get_corpus_by_type

logger = logging.getLogger(__name__)

# Cap Gemini calls in flight across a whole evaluation (all prompts × N samples).
EVAL_CONCURRENCY = 25


class EvaluateRequest(BaseModel):
    """Request body for /api/evaluate."""

    brand: str = "Linear"
    category: str = "project management"
    competitors: list[str] = ["Jira", "Asana", "Monday", "Notion"]
    sampling_n: int | None = None


app = FastAPI(
    title="aeo-engine",
    description="AEO monitoring: how often is a brand the direct answer in Gemini?",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint.

    Exposed at both `/health` (for server-side uptime pingers) and `/api/health`
    (for the browser: content blockers drop requests to a bare `/health` path).
    """
    return {"status": "ok", "gemini_configured": bool(settings.gemini_api_key)}


@app.get("/api/resolve-category")
async def resolve_category(brand: str) -> dict:
    """Resolve what product/service categories a brand belongs to.

    Uses Gemini to infer the correct categories for the given brand.
    The frontend must use this list to constrain user selection.
    """
    if not brand.strip():
        raise HTTPException(status_code=400, detail="brand is required")

    categories = await resolve_brand_categories(brand.strip())
    if not categories:
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve categories for '{brand}'",
        )

    return {"brand": brand.strip(), "categories": categories}


@app.get("/api/resolve-competitors")
async def resolve_competitors(brand: str, category: str) -> dict:
    """Resolve main competitors for a brand in a given category.

    Uses Gemini to infer competitors with brief justifications.
    The frontend displays these as read-only context before evaluation.
    """
    if not brand.strip():
        raise HTTPException(status_code=400, detail="brand is required")
    if not category.strip():
        raise HTTPException(status_code=400, detail="category is required")

    competitors = await resolve_brand_competitors(brand.strip(), category.strip())
    return {
        "brand": brand.strip(),
        "category": category.strip(),
        "competitors": [c.model_dump() for c in competitors],
    }


@app.get("/api/evaluations")
async def get_evaluations() -> list[dict]:
    """List all evaluations."""
    return list_evaluations()


@app.get("/api/evaluations/{evaluation_id}")
async def get_evaluation_detail(evaluation_id: str) -> dict:
    """Get full evaluation detail with metrics and responses."""
    evaluation = get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    responses = get_responses(evaluation_id)
    classifications = get_classifications(evaluation_id)
    metrics = get_metrics(evaluation_id)

    return {
        "evaluation": evaluation,
        "metrics": metrics,
        "responses": responses,
        "classifications": classifications,
    }


@app.post("/api/evaluate")
async def run_evaluation(
    request: EvaluateRequest, background_tasks: BackgroundTasks
) -> dict:
    """Kick off a full evaluation (N runs × M prompts × all brands).

    Returns immediately with ``status: "running"``; the sampling and scoring
    run in the background. Poll ``GET /api/evaluations/{id}`` for progress —
    the row flips to ``completed`` (or ``failed``) when done.

    No hardcoded brands — the prompt corpus is generated from the request.
    """
    n = request.sampling_n or settings.sampling_n
    evaluation_id = str(uuid.uuid4())
    all_brands = [request.brand, *request.competitors]
    corpus = generate_corpus(request.brand, request.category, request.competitors)

    create_evaluation(
        Evaluation(
            id=evaluation_id,
            brand=request.brand,
            category=request.category,
            sampling_n=n,
            status="running",
        )
    )
    background_tasks.add_task(
        _execute_evaluation, evaluation_id, corpus, all_brands, n
    )

    return {
        "evaluation_id": evaluation_id,
        "status": "running",
        "brand": request.brand,
        "category": request.category,
        "competitors": request.competitors,
        "total_prompts": len(corpus),
        "total_responses": len(corpus) * n,
    }


async def _sample_and_store_prompt(
    prompt: PromptRecord,
    evaluation_id: str,
    all_brands: list[str],
    n: int,
    semaphore: asyncio.Semaphore,
) -> list:
    """Sample one prompt N times, persist the raw responses, classify them.

    Returns the classification results (response ids already attached). Runs as
    its own task so results are stored as each prompt finishes, not all at once.
    """
    responses = await run_parallel_sampling(
        prompt=prompt.text,
        prompt_id=prompt.id,
        evaluation_id=evaluation_id,
        n=n,
        semaphore=semaphore,
    )
    save_responses(responses)  # raw responses stored verbatim, immediately

    results = []
    for resp in responses:
        for result in classify_all_brands(resp.raw_text, all_brands):
            result.response_id = resp.id or ""
            results.append(result)
    return results


async def _execute_evaluation(
    evaluation_id: str,
    corpus: list[PromptRecord],
    all_brands: list[str],
    n: int,
) -> None:
    """Background job: sample every prompt concurrently, classify, aggregate.

    One shared semaphore bounds Gemini concurrency across the whole run, so many
    prompts are in flight at once instead of one prompt at a time. Each prompt's
    raw responses are saved as it finishes; a failed prompt is skipped rather
    than sinking the whole evaluation.
    """
    try:
        semaphore = asyncio.Semaphore(EVAL_CONCURRENCY)
        per_prompt = await asyncio.gather(
            *(
                _sample_and_store_prompt(p, evaluation_id, all_brands, n, semaphore)
                for p in corpus
            ),
            return_exceptions=True,
        )

        all_classifications = []
        classifications_by_type: dict[PromptType, list] = defaultdict(list)
        failures = 0
        for prompt, results in zip(corpus, per_prompt, strict=True):
            if isinstance(results, BaseException):
                failures += 1
                logger.warning(
                    "evaluation %s: prompt %s failed: %r",
                    evaluation_id,
                    prompt.id,
                    results,
                )
                continue
            for result in results:
                all_classifications.append(result)
                classifications_by_type[prompt.prompt_type].append(result)

        if not all_classifications:
            raise RuntimeError("every prompt failed")

        save_classifications(all_classifications)
        metrics = compute_per_type_metrics(
            classifications_by_type, evaluation_id, all_brands
        )
        save_metrics(metrics)
        update_evaluation(
            evaluation_id,
            {
                "status": "completed",
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )
    except Exception:
        logger.exception("evaluation %s failed", evaluation_id)
        update_evaluation(evaluation_id, {"status": "failed"})


@app.get("/api/prompts")
async def get_prompts(
    brand: str = "Linear",
    category: str = "project management",
    competitors: str = "Jira,Asana,Monday,Notion",
) -> dict:
    """Return the prompt corpus grouped by type for any brand/category."""
    competitor_list = [c.strip() for c in competitors.split(",")]
    corpus = generate_corpus(brand, category, competitor_list)
    by_type = get_corpus_by_type(corpus)

    return {
        "brand": brand,
        "category": category,
        "competitors": competitor_list,
        "prompts": {
            pt.value: [
                {"id": p.id, "text": p.text, "inverted": p.inverted}
                for p in prompts
            ]
            for pt, prompts in by_type.items()
        },
    }
