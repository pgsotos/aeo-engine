"""FastAPI application for the AEO engine."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
from aeo_engine.metrics import compute_consistency, compute_per_type_metrics
from aeo_engine.models import (
    ClassificationResult,
    Competitor,
    Evaluation,
    PromptRecord,
    PromptType,
)
from aeo_engine.prompts import generate_corpus, get_corpus_by_type

logger = logging.getLogger(__name__)

# Cap Gemini calls in flight across a whole evaluation (all prompts × N samples).
EVAL_CONCURRENCY = 25


class EvaluateRequest(BaseModel):
    """Request body for `POST /api/evaluate`."""

    brand: str = Field("Linear", description="The focus brand being measured.")
    category: str = Field(
        "project management",
        description="Product category the questions are about.",
    )
    competitors: list[str] = Field(
        default=["Jira", "Asana", "Monday", "Notion"],
        description="Competitors to score alongside the focus brand.",
    )
    sampling_n: int | None = Field(
        None,
        ge=1,
        description="Independent Gemini samples per prompt. Defaults to SAMPLING_N (8).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "brand": "Linear",
                    "category": "project management tools",
                    "competitors": ["Jira", "Asana", "Monday", "Notion"],
                    "sampling_n": 8,
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Liveness, plus whether each required credential is present."""

    status: str
    gemini_configured: bool
    supabase_configured: bool


class CategoriesResponse(BaseModel):
    """Categories Gemini infers for a brand."""

    brand: str
    categories: list[str]


class CompetitorsResponse(BaseModel):
    """Competitors Gemini infers for a brand within a category."""

    brand: str
    category: str
    competitors: list[Competitor]


class EvaluationAccepted(BaseModel):
    """Acknowledgement that an evaluation was queued.

    The run happens in the background; poll `GET /api/evaluations/{id}` until
    `status` becomes `completed` or `failed`.
    """

    evaluation_id: str
    status: str
    brand: str
    category: str
    competitors: list[str]
    total_prompts: int
    total_responses: int


class CorpusPrompt(BaseModel):
    """One generated prompt."""

    id: str
    text: str
    inverted: bool = Field(
        description="True when the brand order is swapped, to cancel position bias."
    )


class CorpusResponse(BaseModel):
    """The generated prompt corpus, grouped by prompt type."""

    brand: str
    category: str
    competitors: list[str]
    prompts: dict[str, list[CorpusPrompt]]


DESCRIPTION = """
Measures how often a brand is the **direct answer** Google Gemini gives when
someone asks about a product category — Answer Engine Optimization (AEO).

Each answer is classified per brand as `direct_winner`, `alternative_mention`
or `omitted`. **Direct Answer Win Rate** is the share of runs classified
`direct_winner`, reported with a Wilson score 95% confidence interval.

The corpus spans five prompt types (direct, comparative, use case, feature,
negative), each issued in both brand orderings, and every prompt is sampled N
times independently. Raw Gemini text is stored verbatim and never mutated;
every metric is a pure function over it.

Nothing is hardcoded to a brand — pass any brand, category and competitor set,
or let the `resolve-*` endpoints infer them.
"""

TAGS_METADATA = [
    {"name": "health", "description": "Liveness."},
    {
        "name": "resolution",
        "description": "Ask Gemini which categories a brand competes in, and against whom.",
    },
    {
        "name": "evaluation",
        "description": "Start evaluations and read their results.",
    },
    {"name": "corpus", "description": "Inspect the generated prompts."},
]

app = FastAPI(
    title="aeo-engine",
    description=DESCRIPTION,
    version="0.1.0",
    openapi_tags=TAGS_METADATA,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"], summary="Health check", include_in_schema=False)
@app.get("/api/health", tags=["health"], summary="Health check")
async def health() -> HealthResponse:
    """Report liveness and whether a Gemini API key is configured.

    Served at both `/api/health` and `/health`. The browser must use
    `/api/health` — content blockers drop requests to a bare `/health` path
    (see ADR-016); `/health` remains for server-side uptime pingers.
    """
    return HealthResponse(
        status="ok",
        gemini_configured=bool(settings.gemini_api_key),
        supabase_configured=bool(settings.supabase_url and settings.supabase_key),
    )


@app.get(
    "/api/resolve-category",
    tags=["resolution"],
    summary="Categories a brand competes in",
)
async def resolve_category(brand: str) -> CategoriesResponse:
    """Ask Gemini which product categories a brand belongs to.

    The dashboard uses this to constrain the category field, so an evaluation
    is never run against a category the brand does not compete in.
    """
    if not brand.strip():
        raise HTTPException(status_code=400, detail="brand is required")

    categories = await resolve_brand_categories(brand.strip())
    if not categories:
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve categories for '{brand}'",
        )

    return CategoriesResponse(brand=brand.strip(), categories=categories)


@app.get(
    "/api/resolve-competitors",
    tags=["resolution"],
    summary="Competitors within a category",
)
async def resolve_competitors(brand: str, category: str) -> CompetitorsResponse:
    """Ask Gemini who a brand's main competitors are, with a one-line reason each.

    These become the comparison set for an evaluation — the corpus is generated
    from the focus brand plus these competitors.
    """
    if not brand.strip():
        raise HTTPException(status_code=400, detail="brand is required")
    if not category.strip():
        raise HTTPException(status_code=400, detail="category is required")

    competitors = await resolve_brand_competitors(brand.strip(), category.strip())
    return CompetitorsResponse(
        brand=brand.strip(),
        category=category.strip(),
        competitors=competitors,
    )


@app.get(
    "/api/evaluations",
    tags=["evaluation"],
    summary="List evaluations",
)
async def get_evaluations() -> list[dict[str, Any]]:
    """List every evaluation, newest first.

    Rows are returned as stored, so `status` here is the live state of a run.
    """
    return list_evaluations()


@app.get(
    "/api/evaluations/{evaluation_id}",
    tags=["evaluation"],
    summary="Evaluation detail",
)
async def get_evaluation_detail(evaluation_id: str) -> dict[str, Any]:
    """Return everything recorded for one evaluation.

    Four keys: `evaluation` (the run), `metrics` (win rate and Wilson interval
    per prompt type per brand), `responses` (raw Gemini text, verbatim) and
    `classifications` (one row per response per brand). Every metric can be
    recomputed from the responses.
    """
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


@app.post(
    "/api/evaluate",
    tags=["evaluation"],
    summary="Start an evaluation",
    status_code=202,
)
async def run_evaluation(
    request: EvaluateRequest, background_tasks: BackgroundTasks
) -> EvaluationAccepted:
    """Queue a full evaluation: N samples × every prompt × every brand.

    Returns immediately with `status: "running"` — the sampling and scoring run
    in the background (ADR-017). Poll `GET /api/evaluations/{id}` until the
    status becomes `completed` or `failed`; a default N = 8 run takes roughly
    two minutes.

    No hardcoded brands: the corpus is generated from the brand, category and
    competitors in the request.
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

    return EvaluationAccepted(
        evaluation_id=evaluation_id,
        status="running",
        brand=request.brand,
        category=request.category,
        competitors=request.competitors,
        total_prompts=len(corpus),
        total_responses=len(corpus) * n,
    )


async def _sample_and_store_prompt(
    prompt: PromptRecord,
    evaluation_id: str,
    all_brands: list[str],
    n: int,
    semaphore: asyncio.Semaphore,
) -> list[ClassificationResult]:
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
        classifications_by_type: dict[PromptType, list[ClassificationResult]] = defaultdict(
        list
    )
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
            # Surface why, not just that it failed — the usual cause is a bad
            # GEMINI_API_KEY, and the first prompt's error says so exactly.
            first_error = next(
                (r for r in per_prompt if isinstance(r, BaseException)), None
            )
            raise RuntimeError(
                f"every prompt failed; first error: {first_error!r}"
                if first_error
                else "every prompt failed"
            )

        save_classifications(all_classifications)
        metrics = compute_per_type_metrics(
            classifications_by_type, evaluation_id, all_brands
        )
        save_metrics(metrics)

        # Brand-level consistency over the focus brand's per-type DWR
        win_rates = [m.win_rate for m in metrics if m.brand == all_brands[0]]
        consistency = compute_consistency(win_rates)
        if consistency is not None:
            update_evaluation(evaluation_id, {"consistency": consistency})

        # Mark evaluation as completed
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


@app.get(
    "/api/prompts",
    tags=["corpus"],
    summary="Generated prompt corpus",
)
async def get_prompts(
    brand: str = "Linear",
    category: str = "project management",
    competitors: str = "Jira,Asana,Monday,Notion",
) -> CorpusResponse:
    """Show the exact prompts an evaluation would send, grouped by prompt type.

    Two base questions per type, each in both brand orderings, so `inverted`
    pairs are visible side by side. Pass `competitors` as a comma-separated
    list. Nothing is sent to Gemini by this endpoint.
    """
    competitor_list = [c.strip() for c in competitors.split(",")]
    corpus = generate_corpus(brand, category, competitor_list)
    by_type = get_corpus_by_type(corpus)

    return CorpusResponse(
        brand=brand,
        category=category,
        competitors=competitor_list,
        prompts={
            pt.value: [
                CorpusPrompt(id=p.id, text=p.text, inverted=p.inverted)
                for p in prompts
            ]
            for pt, prompts in by_type.items()
        },
    )
