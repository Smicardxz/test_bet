-- Migration 006: Add shadow tier fields for tier redesign simulation
-- This is a SHADOW system - does not replace existing tiers

-- Add shadow tier columns
ALTER TABLE predictions
ADD COLUMN IF NOT EXISTS shadow_tier TEXT,
ADD COLUMN IF NOT EXISTS shadow_tier_score NUMERIC,
ADD COLUMN IF NOT EXISTS shadow_tier_reason TEXT;

-- Add index for shadow tier queries
CREATE INDEX IF NOT EXISTS idx_predictions_shadow_tier
ON predictions(shadow_tier);

-- Add comment
COMMENT ON COLUMN predictions.shadow_tier IS 'Shadow tier for tier redesign simulation (SHADOW_S, SHADOW_A, SHADOW_B, SHADOW_WATCH, SHADOW_RESEARCH)';
COMMENT ON COLUMN predictions.shadow_tier_score IS 'Shadow tier score (0-100) based on new weighting formula';
COMMENT ON COLUMN predictions.shadow_tier_reason IS 'Reason for shadow tier assignment (penalties applied, etc.)';
