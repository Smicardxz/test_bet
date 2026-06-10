-- ============================================================
-- RUN ALL PENDING MIGRATIONS — paste this in Supabase SQL Editor
-- All statements are idempotent (IF NOT EXISTS / IF EXISTS guards).
-- Safe to re-run if some migrations were already applied.
-- ============================================================


-- ══════════════════════════════════════════════════════════════
-- 002 — tracking_generation
-- ROOT CAUSE OF predictions_saved=0 — MUST be applied first
-- ══════════════════════════════════════════════════════════════

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS tracking_generation VARCHAR(20) DEFAULT 'POST_RESET'
    CHECK (tracking_generation IN ('LEGACY', 'POST_RESET'));

CREATE INDEX IF NOT EXISTS idx_predictions_generation
  ON predictions(tracking_generation);

-- Back-fill all existing rows as LEGACY
UPDATE predictions
  SET tracking_generation = 'LEGACY'
WHERE tracking_generation IS NULL;


-- ══════════════════════════════════════════════════════════════
-- add_odds_source — odds provider column
-- ══════════════════════════════════════════════════════════════

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS odds_source TEXT DEFAULT 'NO_ODDS';

CREATE INDEX IF NOT EXISTS idx_predictions_odds_source
  ON predictions(odds_source);


-- ══════════════════════════════════════════════════════════════
-- add_multimarket_columns — multi-market regime fields
-- ══════════════════════════════════════════════════════════════

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS market_regime                TEXT,
  ADD COLUMN IF NOT EXISTS best_market                  TEXT,
  ADD COLUMN IF NOT EXISTS secondary_market             TEXT,
  ADD COLUMN IF NOT EXISTS best_over_market             TEXT,
  ADD COLUMN IF NOT EXISTS best_under_market            TEXT,
  ADD COLUMN IF NOT EXISTS recommended_market_direction TEXT,
  ADD COLUMN IF NOT EXISTS offensive_profile            JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS defensive_profile            JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS avoid_markets                JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS market_generation_stats      JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS rejection_reasons_by_market  JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_pred_market_regime
  ON predictions(market_regime);

CREATE INDEX IF NOT EXISTS idx_pred_recommended_dir
  ON predictions(recommended_market_direction);

CREATE INDEX IF NOT EXISTS idx_pred_best_over
  ON predictions(best_over_market);


-- ══════════════════════════════════════════════════════════════
-- add_bettable_universe_columns — bettable universe fields
-- ══════════════════════════════════════════════════════════════

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS market_access            TEXT    DEFAULT 'RESEARCH_ONLY',
  ADD COLUMN IF NOT EXISTS bettable_priority_score  INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS odds_coverage_score      INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS market_liquidity_score   INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS bettable_tier            TEXT;

CREATE INDEX IF NOT EXISTS idx_pred_market_access
  ON predictions(market_access);

CREATE INDEX IF NOT EXISTS idx_pred_bettable_prio
  ON predictions(bettable_priority_score DESC);

CREATE INDEX IF NOT EXISTS idx_pred_bettable_tier
  ON predictions(bettable_tier);


-- ══════════════════════════════════════════════════════════════
-- 003 — EV persistence fields (bookmaker_odd enrichment)
-- Safe to re-run if already applied.
-- ══════════════════════════════════════════════════════════════

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS bookmaker            VARCHAR(100);

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS market_probability   FLOAT;

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS implied_probability  FLOAT;

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS ev_percentage        FLOAT;

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS edge_percentage      FLOAT;

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS expected_value       FLOAT;

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS probability_source   VARCHAR(50);

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS ev_quality           VARCHAR(20);

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS rejection_reason     TEXT;

CREATE INDEX IF NOT EXISTS idx_predictions_bookmaker_odd
  ON predictions(bookmaker_odd)
  WHERE bookmaker_odd IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_predictions_ev_quality
  ON predictions(ev_quality)
  WHERE ev_quality IS NOT NULL;

-- Back-fill implied_probability for rows that already have bookmaker_odd
UPDATE predictions
  SET implied_probability = ROUND((1.0 / bookmaker_odd)::NUMERIC, 4)
WHERE bookmaker_odd IS NOT NULL
  AND bookmaker_odd >= 1.01
  AND implied_probability IS NULL;


-- ══════════════════════════════════════════════════════════════
-- DONE — all migrations applied
-- Run: python audit_ev_persistence.py --all
-- to verify predictions are now visible.
-- ══════════════════════════════════════════════════════════════
