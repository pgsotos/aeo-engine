-- aeo-engine: Strict AEO methodology schema additions
-- Run in the Supabase SQL editor after 001_initial_schema.sql.
-- Additive only: existing rows keep NULL until the next evaluation writes them.

-- Metrics: Share of Voice (complementary to Direct Answer Win Rate)
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS share_of_voice REAL;

-- Evaluations: brand consistency across per-type win rates (NULL if <2 types)
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS consistency REAL;