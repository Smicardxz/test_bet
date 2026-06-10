-- ============================================================
-- Migration 002 — tracking_generation
-- Run in Supabase SQL Editor before using REPORT_RESET_FILTER.
--
-- Adds a tracking_generation label to every prediction row:
--   LEGACY     → created before TRACKING_RESET_AT
--   POST_RESET → created after TRACKING_RESET_AT (new tracking era)
--
-- After running this migration, set in .env:
--   TRACKING_RESET_AT=YYYY-MM-DD   (e.g. 2026-06-02)
--
-- Back-fill existing rows: all existing rows become LEGACY by default.
-- New rows saved after the reset date will be labelled POST_RESET.
-- ============================================================

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS tracking_generation VARCHAR(20) DEFAULT 'POST_RESET'
    CHECK (tracking_generation IN ('LEGACY', 'POST_RESET'));

CREATE INDEX IF NOT EXISTS idx_predictions_generation
  ON predictions(tracking_generation);

-- Back-fill all existing rows to LEGACY
-- (adjust the date to your actual reset point if needed)
UPDATE predictions
  SET tracking_generation = 'LEGACY'
WHERE tracking_generation IS NULL
   OR tracking_generation = 'POST_RESET';

-- Then re-mark rows from the new era once you know your reset date:
-- UPDATE predictions
--   SET tracking_generation = 'POST_RESET'
-- WHERE prediction_date >= '2026-06-02';   -- replace with your TRACKING_RESET_AT
