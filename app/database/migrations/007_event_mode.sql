-- Migration 007: Add event mode fields for international tournaments
-- This adds parallel tagging for event matches without affecting domestic league logic

-- Add event mode columns
ALTER TABLE predictions
ADD COLUMN IF NOT EXISTS event_context TEXT,
ADD COLUMN IF NOT EXISTS event_name TEXT,
ADD COLUMN IF NOT EXISTS is_event_match BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS event_phase TEXT;

-- Add index for event context queries
CREATE INDEX IF NOT EXISTS idx_predictions_event_context
ON predictions(event_context);

CREATE INDEX IF NOT EXISTS idx_predictions_is_event_match
ON predictions(is_event_match);

-- Add comments
COMMENT ON COLUMN predictions.event_context IS 'Event context: DOMESTIC_LEAGUE, INTERNATIONAL_FRIENDLY, WORLD_CUP, CONTINENTAL_TOURNAMENT, YOUTH_TOURNAMENT, UNKNOWN_EVENT';
COMMENT ON COLUMN predictions.event_name IS 'Human-readable event name (e.g., FIFA World Cup 2026, International Friendlies)';
COMMENT ON COLUMN predictions.is_event_match IS 'True if match is an event (non-domestic league)';
COMMENT ON COLUMN predictions.event_phase IS 'Event phase: qualification, group_stage, knockout_round, semi_final, final, warmup, unknown_phase';
