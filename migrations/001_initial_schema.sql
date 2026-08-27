-- aeo-engine: Supabase schema
-- Run this in the Supabase SQL editor to create the required tables.

-- Evaluations: tracks each full evaluation run
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY,
    brand TEXT NOT NULL DEFAULT 'Linear',
    category TEXT NOT NULL DEFAULT 'Project Management Tools',
    sampling_n INTEGER NOT NULL DEFAULT 8,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Gemini responses: raw, immutable storage of every API call
CREATE TABLE IF NOT EXISTS gemini_responses (
    id UUID PRIMARY KEY,
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    prompt_id TEXT NOT NULL,
    run_index INTEGER NOT NULL CHECK (run_index BETWEEN 1 AND 100),
    model_id TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Classifications: how each brand appears in each response
CREATE TABLE IF NOT EXISTS classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id UUID NOT NULL REFERENCES gemini_responses(id) ON DELETE CASCADE,
    brand TEXT NOT NULL,
    classification TEXT NOT NULL CHECK (classification IN ('direct_winner', 'alternative_mention', 'omitted')),
    first_mention_position INTEGER,
    mention_count INTEGER NOT NULL DEFAULT 0,
    confidence_score REAL NOT NULL DEFAULT 0.0
);

-- Metrics: aggregated Win Rate + confidence intervals per prompt type
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    prompt_type TEXT NOT NULL CHECK (prompt_type IN ('direct', 'comparative', 'use_case', 'feature', 'negative')),
    brand TEXT NOT NULL,
    win_rate REAL NOT NULL,
    ci_lower REAL NOT NULL,
    ci_upper REAL NOT NULL,
    total_runs INTEGER NOT NULL,
    direct_wins INTEGER NOT NULL,
    alternative_mentions INTEGER NOT NULL,
    omitted INTEGER NOT NULL
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_responses_evaluation ON gemini_responses(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_classifications_response ON classifications(response_id);
CREATE INDEX IF NOT EXISTS idx_classifications_brand ON classifications(brand);
CREATE INDEX IF NOT EXISTS idx_metrics_evaluation ON metrics(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_metrics_type_brand ON metrics(prompt_type, brand);
