-- ============================================================
-- Migration 003 — EV persistence fields
-- Run in Supabase SQL Editor before the next tracking cycle.
--
-- Adds missing EV / odds columns to the predictions table so
-- that save_prediction() can persist all EV pick data correctly.
-- All columns use IF NOT EXISTS — safe to re-run.
-- ============================================================

-- Bookmaker name (e.g. "Bet365", "Pinnacle")
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS bookmaker VARCHAR(100);

-- Market probability = model's estimated probability (0-1)
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS market_probability FLOAT;

-- Implied probability = 1 / bookmaker_odd  (0-1)
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS implied_probability FLOAT;

-- ev_percentage = EV expressed as percentage (+3.2 = +3.2% EV)
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS ev_percentage FLOAT;

-- edge_percentage = edge vs bookmaker expressed as percentage
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS edge_percentage FLOAT;

-- expected_value = absolute EV per unit staked
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS expected_value FLOAT;

-- probability_source = where model probability came from
--   e.g. "STATISTICAL_MODEL", "HISTORICAL", "LEAGUE_PROFILE"
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS probability_source VARCHAR(50);

-- ev_quality = qualitative grade of the EV pick
--   e.g. "EXCELLENT", "GOOD", "MARGINAL", "NEGATIVE"
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS ev_quality VARCHAR(20);

-- rejection_reason = why first EV pick was rejected (if no qualified pick)
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- Indexes for EV analysis queries
CREATE INDEX IF NOT EXISTS idx_predictions_bookmaker_odd
  ON predictions(bookmaker_odd)
  WHERE bookmaker_odd IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_predictions_ev_quality
  ON predictions(ev_quality)
  WHERE ev_quality IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_predictions_odds_source
  ON predictions(odds_source);

-- ── Back-fill existing rows ────────────────────────────────
-- Compute implied_probability for rows that already have bookmaker_odd
UPDATE predictions
  SET implied_probability = ROUND((1.0 / bookmaker_odd)::NUMERIC, 4)
WHERE bookmaker_odd IS NOT NULL
  AND bookmaker_odd >= 1.01
  AND implied_probability IS NULL;

-- Set ev_quality = 'UNKNOWN' for settled rows missing it
-- (so we can distinguish "scanner ran but no quality set" vs new rows)
-- Optional — comment out if you prefer NULLs:
-- UPDATE predictions
--   SET ev_quality = 'UNKNOWN'
-- WHERE ev_quality IS NULL AND status != 'PENDING';
