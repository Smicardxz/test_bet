# API Contract v2.0 — Lovable Ready

> **Date:** 2026-05-29  
> **Base URL:** `http://localhost:5000`  
> **CORS:** Enabled (`*`) for local/Lovable frontend development  
> **Data Source:** `api_football` (real data — no mock when `DATA_PROVIDER=api_football`)  

---

## 📋 Table of Contents

1. [GET /api/health](#1-get-apihealth)
2. [GET /api/dashboard/summary](#2-get-apidashboardsummary)
3. [GET /api/matches](#3-get-apimatches)
4. [POST /api/analyze_match](#4-post-apianalyze_match)
5. [GET /api/leagues/coverage](#5-get-apileaguescoverage)
6. [GET /api/data](#6-get-apidata-legacy)
7. [GET /api/refresh](#7-get-apirefresh)
8. [Common Types](#common-types)

---

## 1. GET /api/health

**Purpose:** System health check — lightweight, fast, no DB hit.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-05-29T10:30:00+00:00",
  "version": "2.0.0-lovable",
  "data_source": "api_football",
  "cache_age_seconds": 12.3,
  "cache_active": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"healthy"` or `"degraded"` |
| `timestamp` | `string` | ISO 8601 UTC |
| `version` | `string` | API version |
| `data_source` | `string` | `"api_football"` or `"mock"` |
| `cache_age_seconds` | `float \| null` | Seconds since last data refresh |
| `cache_active` | `boolean` | `true` if cache is still valid |

---

## 2. GET /api/dashboard/summary

**Purpose:** High-level KPIs for the dashboard header / market radar.

**Response:**
```json
{
  "success": true,
  "total_matches": 47,
  "target_matches": 47,
  "analyzed_matches": 5,
  "awaiting_matches": 42,
  "live_matches": 0,
  "finished_matches": 0,
  "opportunities_count": 2,
  "data_source": "api_football",
  "last_refresh": "2026-05-29T10:28:00",
  "is_real_data": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_matches` | `integer` | All matches fetched today |
| `target_matches` | `integer` | Matches that passed targeting filter |
| `analyzed_matches` | `integer` | Matches with deep analysis done |
| `awaiting_matches` | `integer` | Targeted but not yet analyzed |
| `live_matches` | `integer` | Currently live |
| `finished_matches` | `integer` | Already finished |
| `opportunities_count` | `integer` | Matches with `VALUE_DETECTED` best angle |
| `data_source` | `string` | `"api_football"` or `"mock"` |
| `last_refresh` | `string \| null` | ISO timestamp of last scan |
| `is_real_data` | `boolean` | `true` when using API-Football |

---

## 3. GET /api/matches

**Purpose:** List all matches with filtering, sorting, and pagination.

### Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | `string` | `"all"` | Filter: `upcoming`, `live`, `finished`, `all` |
| `country` | `string` | `""` | Exact country name match |
| `league` | `string` | `""` | Partial league name match (case-insensitive) |
| `confidence` | `float` | — | Minimum `confidence_score` (0–100) |
| `profile_type` | `string` | `""` | Filter by tag: `LOW_TEMPO`, `HIGH_SCORING`, `BTTS_PROFILE`, `defensive_clash`, etc. |
| `analyzed` | `string` | `""` | `"true"` or `"false"` |
| `limit` | `integer` | `50` | Max results per page |
| `offset` | `integer` | `0` | Pagination offset |

### Response

```json
{
  "success": true,
  "total": 47,
  "returned": 50,
  "offset": 0,
  "limit": 50,
  "matches": [
    {
      "fixture_id": "1234567",
      "home_team": "Arsenal",
      "away_team": "Chelsea",
      "home_team_id": "42",
      "away_team_id": "49",
      "country": "England",
      "league": "Premier League",
      "kickoff_time": "2026-05-29 15:00",
      "status": "UPCOMING",
      "target_type": "MAJOR",
      "profile_tags": ["LOW_TEMPO", "LOW_SCORING", "defensive_clash", "high_stability"],
      "best_angle": {
        "market": "HT_UNDER_1_5",
        "label": "HT Under 1.5",
        "confidence": 90,
        "fair_odd": 1.18,
        "market_odd": null,
        "sample_size": 20,
        "status": "VALUE_DETECTED",
        "edge_percent": 8.5
      },
      "interest_score": 68.0,
      "confidence_score": 82.0,
      "volatility_score": 35.0,
      "data_quality": "GOOD",
      "analyzed": true,
      "has_profile": true
    }
  ]
}
```

### Match Object

| Field | Type | Description |
|-------|------|-------------|
| `fixture_id` | `string` | Unique match identifier |
| `home_team` | `string` | Home team name |
| `away_team` | `string` | Away team name |
| `home_team_id` | `string` | Provider team ID |
| `away_team_id` | `string` | Provider team ID |
| `country` | `string` | Match country |
| `league` | `string` | Competition name |
| `kickoff_time` | `string` | Human-readable kickoff time |
| `status` | `string` | `UPCOMING`, `LIVE`, `FINISHED` |
| `target_type` | `string` | `MAJOR`, `BETTABLE_MINOR`, `EXTREME_OBSCURE` |
| `profile_tags` | `string[]` | Combined tags from profiling (tempo, scoring, specific profiles, characteristics) |
| `best_angle` | `BestAngle` | See below |
| `interest_score` | `float` | 0–100: how interesting the match is |
| `confidence_score` | `float` | 0–100: data reliability |
| `volatility_score` | `float` | 0–100: predictability (lower = more stable) |
| `data_quality` | `string` | `EXCELLENT`, `GOOD`, `FAIR`, `LIMITED`, `INSUFFICIENT`, `UNKNOWN` |
| `analyzed` | `boolean` | Whether deep analysis was run |
| `has_profile` | `boolean` | Whether a valid match_profile exists |

### BestAngle Object

| Field | Type | Description |
|-------|------|-------------|
| `market` | `string` | e.g. `HT_UNDER_1_5`, `FT_OVER_2_5` |
| `label` | `string` | Human-readable label |
| `confidence` | `integer` | 0–100 aggregate confidence |
| `fair_odd` | `float \| null` | Calculated fair odd |
| `market_odd` | `float \| null` | Bookmaker odd (null if not loaded) |
| `sample_size` | `integer` | Historical matches backing this angle |
| `status` | `string` | `VALUE_DETECTED`, `WAITING_FOR_ODDS`, `NO_VALUE`, `NOT_ANALYZED` |
| `edge_percent` | `float` | Bookmaker mispricing % (0 if no odds) |

---

## 4. POST /api/analyze_match

**Purpose:** Run deep analysis on a single match. Returns a **stable schema** regardless of data quality.

### Request Body

```json
{
  "fixture_id": "1234567",
  "home_team_id": "42",
  "away_team_id": "49",
  "home_team_name": "Arsenal",
  "away_team_name": "Chelsea",
  "league_name": "Premier League",
  "country": "England",
  "season": "2025"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `fixture_id` | ✅ | Match ID from provider |
| `home_team_id` | ✅ | Home team ID |
| `away_team_id` | ✅ | Away team ID |
| `home_team_name` | ❌ | Display name |
| `away_team_name` | ❌ | Display name |
| `league_name` | ❌ | For league profiling |
| `country` | ❌ | For league profiling |
| `season` | ❌ | Reserved for future use |

### Response — Stable Schema

```json
{
  "fixture_id": "1234567",
  "data_origin": "REAL",
  "analysis_status": "ANALYZABLE_NO_ODDS",
  "match_profile": {
    "profile_tags": ["LOW_TEMPO", "LOW_SCORING", "defensive_clash", "high_stability"],
    "interest_score": 68.0,
    "confidence_score": 82.0,
    "volatility_score": 35.0,
    "sample_size": 20,
    "summary": "LOW TEMPO | LOW SCORING | Interest 68/100"
  },
  "top_angles": [
    {
      "market": "HT_UNDER_1_5",
      "label": "HT Under 1.5",
      "hit_rate": 85.0,
      "fair_odd": 1.18,
      "sample_size": 20,
      "confidence": "HIGH",
      "edge_percent": 8.5,
      "why": ["Historical HT goals 0.85 avg", "80% under 1.5"]
    },
    {
      "market": "FT_UNDER_2_5",
      "label": "FT Under 2.5",
      "hit_rate": 70.0,
      "fair_odd": 1.43,
      "sample_size": 20,
      "confidence": "MEDIUM",
      "edge_percent": 0.0,
      "why": ["Defensive clash profile"]
    }
  ],
  "ht_analysis": [
    {
      "line": "U0.5",
      "hit_rate": 40.0,
      "under_count": 8,
      "over_count": 12,
      "sample_size": 20,
      "fair_odd": 2.5,
      "max_ht_goals": 3,
      "avg_ht_goals": 0.85
    },
    {
      "line": "U1.5",
      "hit_rate": 80.0,
      "under_count": 16,
      "over_count": 4,
      "sample_size": 20,
      "fair_odd": 1.25,
      "max_ht_goals": 3,
      "avg_ht_goals": 0.85
    }
  ],
  "ft_analysis": [
    {
      "line": "U1.5",
      "hit_rate": 55.0,
      "under_count": 11,
      "over_count": 9,
      "sample_size": 20,
      "fair_odd": 1.82,
      "max_goals": 4,
      "avg_goals": 1.95
    },
    {
      "line": "U2.5",
      "hit_rate": 70.0,
      "under_count": 14,
      "over_count": 6,
      "sample_size": 20,
      "fair_odd": 1.43,
      "max_goals": 4,
      "avg_goals": 1.95
    }
  ],
  "recent_history": [
    {"match_number": 1, "total_goals": 2, "ht_goals": 1},
    {"match_number": 2, "total_goals": 1, "ht_goals": 0},
    {"match_number": 3, "total_goals": 3, "ht_goals": 1}
  ],
  "h2h": ["H2H match 1", "H2H match 2"],
  "warnings": [],
  "errors": []
}
```

### AnalysisStatus Enum

| Value | Meaning |
|-------|---------|
| `ANALYZED` | Full analysis with odds detected |
| `ANALYZABLE_NO_ODDS` | Analysis complete, waiting for bookmaker odds |
| `DATA_INSUFFICIENT` | Not enough historical data |
| `ERROR` | Internal error during analysis |

### TopAngles Object

| Field | Type | Description |
|-------|------|-------------|
| `market` | `string` | Machine-readable market code |
| `label` | `string` | Human-readable label |
| `hit_rate` | `float` | Historical hit rate % |
| `fair_odd` | `float \| null` | Calculated fair odd |
| `sample_size` | `integer` | Number of historical matches |
| `confidence` | `string` | `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN` |
| `edge_percent` | `float` | Bookmaker mispricing % (0 if no market odd) |
| `why` | `string[]` | Human-readable reasons |

---

## 5. GET /api/leagues/coverage

**Purpose:** Show which countries and leagues are covered today.

**Response:**

```json
{
  "success": true,
  "countries": [
    {
      "country": "England",
      "leagues": ["Premier League", "Championship"],
      "league_count": 2,
      "matches_today": 8,
      "analyzed_count": 3,
      "coverage_level": "FULL",
      "target_type": "MAJOR"
    },
    {
      "country": "Ethiopia",
      "leagues": ["Premier League"],
      "league_count": 1,
      "matches_today": 4,
      "analyzed_count": 1,
      "coverage_level": "MINIMAL",
      "target_type": "EXTREME_OBSCURE"
    }
  ],
  "total_leagues": 3,
  "total_matches": 12
}
```

### CountryCoverage Object

| Field | Type | Description |
|-------|------|-------------|
| `country` | `string` | Country name |
| `leagues` | `string[]` | List of league names |
| `league_count` | `integer` | Number of leagues |
| `matches_today` | `integer` | Total matches today |
| `analyzed_count` | `integer` | Matches with analysis |
| `coverage_level` | `string` | `FULL`, `PARTIAL`, `MINIMAL` |
| `target_type` | `string` | `MAJOR`, `BETTABLE_MINOR`, `EXTREME_OBSCURE` |

---

## 6. GET /api/data (Legacy)

**Purpose:** Original endpoint for the existing HTML dashboard.

> **Note:** This endpoint is kept for backward compatibility. For new Lovable frontends, prefer the dedicated endpoints above (`/api/dashboard/summary`, `/api/matches`, `/api/analyze_match`).

**Response:** Large nested object with `categories`, `stats`, `filters`, `diagnostic`.

---

## 7. GET /api/refresh

**Purpose:** Force cache invalidation and trigger a fresh data scan.

**Response:**
```json
{
  "success": true,
  "message": "Cache cleared"
}
```

---

## Common Types

### `MatchStatus` Enum

- `UPCOMING` — Match has not started
- `LIVE` — Match is currently in progress
- `FINISHED` — Match has ended

### `TargetType` Enum

- `MAJOR` — Top-tier leagues (Premier League, La Liga, Bundesliga, etc.)
- `BETTABLE_MINOR` — Lower divisions, semi-pro, regional leagues with odds
- `EXTREME_OBSCURE` — Youth, women, very small countries (high edge potential)

### `DataQuality` Enum

- `EXCELLENT` — ≥15 FT + ≥15 HT samples
- `GOOD` — ≥10 FT + ≥10 HT samples
- `FAIR` — ≥5 FT samples
- `LIMITED` — <5 FT samples
- `INSUFFICIENT` — Not enough data to profile
- `UNKNOWN` — Not analyzed yet

### `AngleStatus` Enum

- `VALUE_DETECTED` — Edge > 5% detected
- `WAITING_FOR_ODDS` — Profile exists but no bookmaker odds loaded
- `NO_VALUE` — Analyzed but no exploitable edge found
- `NOT_ANALYZED` — Match not yet processed

---

## 🎨 Lovable Frontend Views Mapping

| Lovable View | Recommended Endpoints |
|-------------|----------------------|
| **Market Radar** | `GET /api/dashboard/summary` + `GET /api/matches?status=upcoming&analyzed=true` |
| **Match Explorer** | `GET /api/matches` with filters (`country`, `profile_type`, `confidence`) |
| **Match Detail** | `POST /api/analyze_match` (full analysis) or `GET /api/matches` + existing profile |
| **Data Diagnostics** | `GET /api/health` + `GET /api/leagues/coverage` |

---

## 🔐 Mock Policy

When `DATA_PROVIDER=api_football` (production / real mode):

- `data_origin` is always `"REAL"`
- No synthetic/mock data is injected
- `mock_usage: false` in all responses
- Historical data comes from API-Football
- Bookmaker odds come from API-Football (when loaded)

---

## 📝 Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-05-29 | Stable contract for Lovable. Added `/api/health`, `/api/dashboard/summary`, `/api/matches`, `/api/leagues/coverage`. Stabilized `POST /api/analyze_match` schema. Added CORS. |
