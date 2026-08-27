"""FastAPI application for the AEO engine."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
from aeo_engine.gemini import run_parallel_sampling
from aeo_engine.metrics import compute_per_type_metrics
from aeo_engine.models import (
    ClassificationResult,
    Evaluation,
    GeminiResponse,
    PromptType,
)
from aeo_engine.prompts import ALL_BRANDS, ALL_PROMPTS, FOCUS_BRAND, PROMPTS_BY_TYPE

app = FastAPI(
    title="aeo-engine",
    description="AEO monitoring: how often is Linear the direct answer in Gemini?",
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
    brand: str = FOCUS_BRAND,
    sampling_n: int | None = None,
) -> dict:
    """Run a full evaluation: N runs × M prompts × all brands.

    This is the main orchestration endpoint. It:
    1. Creates an evaluation record
    2. Runs N independent Gemini calls per prompt
    3. Classifies each response for all brands
    4. Computes per-type metrics with confidence intervals
    5. Stores everything in Supabase
    """
    n = sampling_n or settings.sampling_n
    evaluation_id = str(uuid.uuid4())

    # Create evaluation record
    evaluation = Evaluation(
        id=evaluation_id,
        brand=brand,
        category="Project Management Tools",
        sampling_n=n,
        status="running",
    )
    create_evaluation(evaluation)

    try:
        all_responses: list[GeminiResponse] = []
        all_classifications: list[ClassificationResult] = []
        classifications_by_type: dict[PromptType, list[ClassificationResult]] = (
            defaultdict(list)
        )

        # Run each prompt with N parallel samples
        for prompt in ALL_PROMPTS:
            responses = await run_parallel_sampling(
                prompt=prompt.text,
                prompt_id=prompt.id,
                evaluation_id=evaluation_id,
                n=n,
            )
            all_responses.extend(responses)

            # Classify each response for all brands
            for resp in responses:
                brand_results = classify_all_brands(resp.raw_text, ALL_BRANDS)
                for result in brand_results:
                    result.response_id = resp.id or ""
                    all_classifications.append(result)
                    classifications_by_type[prompt.prompt_type].append(result)

        # Save raw responses (immutable)
        save_responses(all_responses)

        # Save classifications
        save_classifications(all_classifications)

        # Compute per-type metrics
        metrics = compute_per_type_metrics(
            classifications_by_type, evaluation_id, ALL_BRANDS
        )
        save_metrics(metrics)

        # Mark evaluation as completed
        update_evaluation(
            evaluation_id,
            {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
            },
        )

        return {
            "evaluation_id": evaluation_id,
            "status": "completed",
            "total_responses": len(all_responses),
            "total_classifications": len(all_classifications),
            "metrics_count": len(metrics),
        }

    except Exception as e:
        update_evaluation(evaluation_id, {"status": "failed"})
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e!s}")


@app.get("/api/prompts")
async def get_prompts() -> dict:
    """Return the prompt corpus grouped by type."""
    return {
        "brand": FOCUS_BRAND,
        "competitors": [b for b in ALL_BRANDS if b != FOCUS_BRAND],
        "prompts": {
            pt.value: [{"id": p.id, "text": p.text, "inverted": p.inverted} for p in prompts]
            for pt, prompts in PROMPTS_BY_TYPE.items()
        },
    }
