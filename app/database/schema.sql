-- ============================================================
-- Betting Intelligence — Supabase PostgreSQL Schema
-- Phase 2
--
-- Run this in your Supabase SQL editor (Dashboard → SQL Editor)
-- All tables use service_role key — configure RLS after setup.
-- ============================================================

-- ── Helpers ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ===========================================================================
-- 1. FIXTURES
-- Raw match data: status, scores, kickoff
-- ===========================================================================
CREATE TABLE IF NOT EXISTS fixtures (
    id              BIGSERIAL PRIMARY KEY,
    fixture_id      VARCHAR(60)  UNIQUE NOT NULL,
    home_team       VARCHAR(255) NOT NULL,
    away_team       VARCHAR(255) NOT NULL,
    home_team_id    VARCHAR(60),
    away_team_id    VARCHAR(60),
    league          VARCHAR(255) NOT NULL,
    country         VARCHAR(100),
    kickoff_time    TIMESTAMPTZ,
    status          VARCHAR(50)  DEFAULT 'NS',
    -- Final scores (populated after settlement)
    home_score      SMALLINT,
    away_score      SMALLINT,
    ht_home_score   SMALLINT,
    ht_away_score   SMALLINT,
    -- Universe / Coverage
    match_universe  VARCHAR(50)  DEFAULT 'STATISTICAL_ONLY',
    coverage_quality VARCHAR(20) DEFAULT 'NONE',
    -- Timestamps
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fixtures_league        ON fixtures(league);
CREATE INDEX IF NOT EXISTS idx_fixtures_kickoff       ON fixtures(kickoff_time);
CREATE INDEX IF NOT EXISTS idx_fixtures_status        ON fixtures(status);

CREATE TRIGGER trg_fixtures_updated_at
  BEFORE UPDATE ON fixtures
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- ===========================================================================
-- 2. PREDICTIONS
-- One row per (fixture × market × prediction_date)
-- Lifecycle: PENDING → WON | LOST | VOID | ERROR
-- ===========================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id                  BIGSERIAL PRIMARY KEY,
    prediction_id       VARCHAR(200) UNIQUE NOT NULL, -- fixture_id + market + date
    fixture_id          VARCHAR(60)  REFERENCES fixtures(fixture_id) ON DELETE CASCADE,
    home_team           VARCHAR(255),
    away_team           VARCHAR(255),
    league              VARCHAR(255),
    country             VARCHAR(100),
    kickoff_time        TIMESTAMPTZ,
    prediction_date     DATE         DEFAULT CURRENT_DATE,
    -- Market
    market              VARCHAR(100) NOT NULL,
    -- Tiers
    statistical_tier    VARCHAR(50),
    ev_tier             VARCHAR(50),
    match_universe      VARCHAR(50),
    coverage_quality    VARCHAR(20),
    -- Model scores
    model_probability   FLOAT,
    fair_odd            FLOAT,
    bookmaker_odd       FLOAT,
    edge_percent        FLOAT,
    ev_percent          FLOAT,
    confidence_score    FLOAT,
    volatility_score    FLOAT,
    chaos_score         FLOAT,
    false_signal_score  FLOAT,
    ranking_score       FLOAT,
    -- League Specialization Engine
    league_edge_rating              VARCHAR(50)  DEFAULT 'NO_DATA',
    market_historical_profitability VARCHAR(50)  DEFAULT 'NO_DATA',
    -- Error Analysis Engine
    historical_failure_penalty  FLOAT        DEFAULT 0,
    failure_pattern_warning     TEXT         DEFAULT '',
    why_pick                    JSONB        DEFAULT '[]',
    risk_factors                JSONB        DEFAULT '[]',
    why_not_s_tier              JSONB        DEFAULT '[]',
    -- Lifecycle (Phase 6)
    status              VARCHAR(20)  DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING','WON','LOST','VOID','ERROR')),
    -- Settlement result
    final_result        VARCHAR(10)
                        CHECK (final_result IN ('WIN','LOSS','VOID') OR final_result IS NULL),
    actual_home_score   SMALLINT,
    actual_away_score   SMALLINT,
    actual_ht_home_score SMALLINT,
    actual_ht_away_score SMALLINT,
    profit_loss         FLOAT,       -- in units (stake = 1.0)
    settled_at          TIMESTAMPTZ,
    settlement_notes    TEXT,
    -- Timestamps
    created_at          TIMESTAMPTZ  DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  DEFAULT NOW()
);

-- Natural key for deduplication
CREATE UNIQUE INDEX IF NOT EXISTS uix_predictions_key
    ON predictions(fixture_id, market, prediction_date);

CREATE INDEX IF NOT EXISTS idx_predictions_status       ON predictions(status);
CREATE INDEX IF NOT EXISTS idx_predictions_date         ON predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_predictions_league       ON predictions(league);
CREATE INDEX IF NOT EXISTS idx_predictions_market       ON predictions(market);
CREATE INDEX IF NOT EXISTS idx_predictions_tier         ON predictions(statistical_tier);
CREATE INDEX IF NOT EXISTS idx_predictions_kickoff      ON predictions(kickoff_time);

CREATE TRIGGER trg_predictions_updated_at
  BEFORE UPDATE ON predictions
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- ===========================================================================
-- 3. ODDS_SNAPSHOTS
-- Bookmaker odds at scan time — multiple per fixture
-- ===========================================================================
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    fixture_id      VARCHAR(60)  REFERENCES fixtures(fixture_id) ON DELETE CASCADE,
    market          VARCHAR(100) NOT NULL,
    bookmaker       VARCHAR(100),
    bookmaker_odd   FLOAT,
    fair_odd        FLOAT,
    ev_percent      FLOAT,
    market_mapping_confidence FLOAT,
    odds_status     VARCHAR(50),
    snapshot_time   TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_odds_fixture     ON odds_snapshots(fixture_id);
CREATE INDEX IF NOT EXISTS idx_odds_snapshot    ON odds_snapshots(snapshot_time);


-- ===========================================================================
-- 4. LEAGUE_PROFILES
-- Aggregated performance per league (updated after settlement)
-- ===========================================================================
CREATE TABLE IF NOT EXISTS league_profiles (
    id                  BIGSERIAL PRIMARY KEY,
    league              VARCHAR(255) NOT NULL,
    country             VARCHAR(100) NOT NULL DEFAULT '',
    -- Prediction stats
    total_predictions   INTEGER     DEFAULT 0,
    total_wins          INTEGER     DEFAULT 0,
    total_losses        INTEGER     DEFAULT 0,
    total_void          INTEGER     DEFAULT 0,
    hit_rate            FLOAT       DEFAULT 0,
    roi                 FLOAT       DEFAULT 0,
    total_profit_loss   FLOAT       DEFAULT 0,
    -- Analysis metrics
    avg_goals           FLOAT,
    btts_rate           FLOAT,
    under_2_5_rate      FLOAT,
    volatility_score    FLOAT,
    reliability_score   FLOAT,
    -- LSE data
    best_markets        JSONB       DEFAULT '[]',
    worst_markets       JSONB       DEFAULT '[]',
    edge_score          FLOAT       DEFAULT 0,
    -- EAE data
    false_positive_count INTEGER    DEFAULT 0,
    false_positive_rate  FLOAT      DEFAULT 0,
    -- Timestamps
    last_updated        TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(league, country)
);

CREATE INDEX IF NOT EXISTS idx_lp_roi       ON league_profiles(roi DESC);
CREATE INDEX IF NOT EXISTS idx_lp_edge      ON league_profiles(edge_score DESC);


-- ===========================================================================
-- 5. MODEL_PERFORMANCE
-- Periodic performance snapshots (DAILY / ALL_TIME)
-- ===========================================================================
CREATE TABLE IF NOT EXISTS model_performance (
    id              BIGSERIAL PRIMARY KEY,
    period_type     VARCHAR(20)  DEFAULT 'DAILY'
                    CHECK (period_type IN ('DAILY','WEEKLY','MONTHLY','ALL_TIME')),
    period_start    DATE,
    period_end      DATE,
    -- Overall stats
    total_predictions   INTEGER  DEFAULT 0,
    total_settled       INTEGER  DEFAULT 0,
    total_wins          INTEGER  DEFAULT 0,
    total_losses        INTEGER  DEFAULT 0,
    total_void          INTEGER  DEFAULT 0,
    hit_rate            FLOAT    DEFAULT 0,
    roi                 FLOAT    DEFAULT 0,
    total_profit_loss   FLOAT    DEFAULT 0,
    -- By tier
    s_tier_total        INTEGER  DEFAULT 0,
    s_tier_wins         INTEGER  DEFAULT 0,
    s_tier_hit_rate     FLOAT    DEFAULT 0,
    a_tier_total        INTEGER  DEFAULT 0,
    a_tier_wins         INTEGER  DEFAULT 0,
    a_tier_hit_rate     FLOAT    DEFAULT 0,
    -- Quality
    false_positive_count INTEGER DEFAULT 0,
    false_positive_rate  FLOAT   DEFAULT 0,
    max_drawdown        FLOAT    DEFAULT 0,
    longest_losing_streak INTEGER DEFAULT 0,
    -- Universe breakdown
    stat_only_count     INTEGER  DEFAULT 0,
    market_ev_count     INTEGER  DEFAULT 0,
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(period_type, period_start)
);

CREATE TRIGGER trg_perf_updated_at
  BEFORE UPDATE ON model_performance
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- ===========================================================================
-- 6. FALSE_POSITIVE_PATTERNS
-- Persists EAE patterns so they survive server restarts
-- ===========================================================================
CREATE TABLE IF NOT EXISTS false_positive_patterns (
    id              BIGSERIAL PRIMARY KEY,
    league          VARCHAR(255) NOT NULL,
    country         VARCHAR(100) NOT NULL DEFAULT '',
    market          VARCHAR(100) NOT NULL,
    failure_reason  VARCHAR(100) NOT NULL,
    profile_tags    JSONB        DEFAULT '[]',
    -- Stats
    occurrence_count    INTEGER  DEFAULT 0,
    total_losses        INTEGER  DEFAULT 0,
    fp_rate             FLOAT    DEFAULT 0,
    avg_confidence      FLOAT    DEFAULT 0,
    avg_volatility      FLOAT    DEFAULT 0,
    penalty             FLOAT    DEFAULT 0,
    -- Timestamps
    last_updated        TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(league, country, market, failure_reason)
);

CREATE INDEX IF NOT EXISTS idx_fpp_league   ON false_positive_patterns(league);
CREATE INDEX IF NOT EXISTS idx_fpp_market   ON false_positive_patterns(market);
CREATE INDEX IF NOT EXISTS idx_fpp_reason   ON false_positive_patterns(failure_reason);
CREATE INDEX IF NOT EXISTS idx_fpp_fp_rate  ON false_positive_patterns(fp_rate DESC);
