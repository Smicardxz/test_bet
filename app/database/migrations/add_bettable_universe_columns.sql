-- ============================================================
-- Migration: add bettable universe columns to predictions
-- Run in Supabase SQL Editor (Dashboard → SQL Editor)
-- Safe to run multiple times (IF NOT EXISTS guards).
-- ============================================================

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS market_access            TEXT    DEFAULT 'RESEARCH_ONLY',
    ADD COLUMN IF NOT EXISTS bettable_priority_score  INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS odds_coverage_score      INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS market_liquidity_score   INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS bettable_tier            TEXT;

-- Indexes for dashboard filtering
CREATE INDEX IF NOT EXISTS idx_pred_market_access
    ON predictions(market_access);

CREATE INDEX IF NOT EXISTS idx_pred_bettable_prio
    ON predictions(bettable_priority_score DESC);

CREATE INDEX IF NOT EXISTS idx_pred_bettable_tier
    ON predictions(bettable_tier);
