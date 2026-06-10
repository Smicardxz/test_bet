-- ============================================================
-- Migration: add multi-market regime columns to predictions
-- Run in Supabase SQL Editor (Dashboard → SQL Editor)
-- Safe to run multiple times (IF NOT EXISTS guards).
-- ============================================================

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

-- Optional indexes for dashboard filtering
CREATE INDEX IF NOT EXISTS idx_pred_market_regime
    ON predictions(market_regime);

CREATE INDEX IF NOT EXISTS idx_pred_recommended_dir
    ON predictions(recommended_market_direction);

CREATE INDEX IF NOT EXISTS idx_pred_best_over
    ON predictions(best_over_market);
