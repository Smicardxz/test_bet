-- Migration: add odds_source column to predictions table
-- Phase 6 — Odds Source Breakdown tracking

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS odds_source TEXT DEFAULT 'NO_ODDS';

-- Index for quick breakdown queries in performance report
CREATE INDEX IF NOT EXISTS idx_predictions_odds_source
    ON predictions (odds_source);

-- Comment
COMMENT ON COLUMN predictions.odds_source IS
    'Which odds provider supplied the bookmaker_odd for this prediction.
     Values: API_FOOTBALL | ODDS_API | the_odds_api | NO_ODDS';
