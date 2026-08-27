"""FastAPI application for the AEO engine."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
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
from aeo_engine.gemini import resolve_brand_categories, run_parallel_sampling
from aeo_engine.metrics import compute_per_type_metrics
from aeo_engine.models import Evaluation, PromptType
from aeo_engine.prompts import generate_corpus, get_corpus_by_type


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
async def health() -> dict:
    """Health check endpoint."""
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
async def run_evaluation(request: EvaluateRequest) -> dict:
    """Run a full evaluation: N runs × M prompts × all brands.

    Accepts brand, category, and competitors as parameters.
    No hardcoded brands — fully dynamic prompt generation.
    """
    n = request.sampling_n or settings.sampling_n
    evaluation_id = str(uuid.uuid4())
    all_brands = [request.brand] + request.competitors

    # Generate corpus dynamically
    corpus = generate_corpus(request.brand, request.category, request.competitors)
    corpus_by_type = get_corpus_by_type(corpus)

    # Create evaluation record
    evaluation = Evaluation(
        id=evaluation_id,
        brand=request.brand,
        category=request.category,
        sampling_n=n,
        status="running",
    )
    create_evaluation(evaluation)

    try:
        all_classifications = []
        classifications_by_type: dict[PromptType, list] = defaultdict(list)

        # Run each prompt with N parallel samples
        for prompt in corpus:
            responses = await run_parallel_sampling(
                prompt=prompt.text,
                prompt_id=prompt.id,
                evaluation_id=evaluation_id,
                n=n,
            )

            # Save raw responses (immutable)
            save_responses(responses)

            # Classify each response for all brands
            for resp in responses:
                brand_results = classify_all_brands(resp.raw_text, all_brands)
                for result in brand_results:
                    result.response_id = resp.id or ""
                    all_classifications.append(result)
                    classifications_by_type[prompt.prompt_type].append(result)

        # Save classifications
        save_classifications(all_classifications)

        # Compute per-type metrics
        metrics = compute_per_type_metrics(
            classifications_by_type, evaluation_id, all_brands
        )
        save_metrics(metrics)

        # Mark evaluation as completed
        update_evaluation(
            evaluation_id,
            {
                "status": "completed",
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )

        return {
            "evaluation_id": evaluation_id,
            "status": "completed",
            "brand": request.brand,
            "category": request.category,
            "competitors": request.competitors,
            "total_prompts": len(corpus),
            "total_responses": len(corpus) * n,
            "total_classifications": len(all_classifications),
            "metrics_count": len(metrics),
        }

    except Exception as e:
        update_evaluation(evaluation_id, {"status": "failed"})
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e!s}")


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
