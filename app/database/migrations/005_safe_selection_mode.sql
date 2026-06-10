-- ============================================================
-- Migration 005 — Safe Selection Mode fields
-- ============================================================
-- Adds selection_mode and selection_reason columns to predictions table.
-- Used by SAFE_SELECTION_MODE to filter toxic picks from live ROI.

ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS selection_mode TEXT DEFAULT 'LIVE',
  ADD COLUMN IF NOT EXISTS selection_reason TEXT DEFAULT '';

-- Create index for filtering by selection_mode
CREATE INDEX IF NOT EXISTS idx_selection_mode
  ON predictions(selection_mode);

-- Backfill existing rows with default values
UPDATE predictions
  SET selection_mode = 'LIVE',
      selection_reason = 'MIGRATED_PRE_SAFE_MODE'
WHERE selection_mode IS NULL OR selection_mode = '';
