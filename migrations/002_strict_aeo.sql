-- aeo-engine: Strict AEO methodology schema additions
-- Run in the Supabase SQL editor after 001_initial_schema.sql.
-- Additive only: existing rows keep NULL until the next evaluation writes them.

-- Metrics: Share of Voice (complementary to Direct Answer Win Rate)
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS share_of_voice REAL;

-- Evaluations: brand consistency across per-type win rates (NULL if <2 types)
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS consistency REAL;

-- Gemini responses: Google Search grounding metadata (JSONB, NULL when the
-- provider returns no grounding - stochastic, ~20-30% of calls). Additive.
ALTER TABLE gemini_responses ADD COLUMN IF NOT EXISTS grounding_metadata JSONB;

-- Sources cited by Gemini grounding: one row per grounding_chunk. `domain` is
-- parsed from web.title (the URI is an opaque redirect token, per exploration).
CREATE TABLE IF NOT EXISTS grounding_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id UUID NOT NULL REFERENCES gemini_responses(id) ON DELETE CASCADE,
    web_title TEXT NOT NULL,
    domain TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Segments of the response text backed by grounding: one row per
-- grounding_support, linked to its first cited source (segment offsets belong
-- to the response; the source reference may be dropped to NULL).
CREATE TABLE IF NOT EXISTS grounding_supports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id UUID NOT NULL REFERENCES gemini_responses(id) ON DELETE CASCADE,
    source_id UUID REFERENCES grounding_sources(id) ON DELETE SET NULL,
    segment_start INTEGER NOT NULL,
    segment_end INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_grounding_sources_response ON grounding_sources(response_id);
CREATE INDEX IF NOT EXISTS idx_grounding_supports_response ON grounding_supports(response_id);
CREATE INDEX IF NOT EXISTS idx_grounding_supports_source ON grounding_supports(source_id);