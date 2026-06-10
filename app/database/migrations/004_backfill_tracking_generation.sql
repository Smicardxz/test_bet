-- ============================================================
-- Migration 004 — tracking_generation backfill with datetime
-- ============================================================
-- Backfills tracking_generation using created_at (full timestamp)
-- instead of prediction_date (date only).
--
-- Replace '2026-06-02T15:19:00+00:00' with your actual
-- TRACKING_RESET_AT value before running.
-- ============================================================

-- Step 1: Mark everything before the reset as LEGACY
UPDATE predictions
  SET tracking_generation = 'LEGACY'
WHERE created_at < '2026-06-02T15:19:00+00:00';

-- Step 2: Mark everything from the reset onward as POST_RESET
UPDATE predictions
  SET tracking_generation = 'POST_RESET'
WHERE created_at >= '2026-06-02T15:19:00+00:00';

-- Step 3: Verify counts
SELECT
  tracking_generation,
  COUNT(*) AS count
FROM predictions
GROUP BY tracking_generation;
