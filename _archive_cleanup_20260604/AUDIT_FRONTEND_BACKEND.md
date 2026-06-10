# Audit Complet Frontend BetIQ ↔ Backend

Date : 2026-06-02  
Backend actuel : `app_flask.py` (phase 12 unifiée)

---

## 1. Root-Cause Analysis — Pourquoi les KPIs affichent 0

### Bug critique : double route `/api/diagnostics`
`app_flask.py` avait **deux** fonctions Flask sur la même URL :

| Ligne | Fonction | Champs retournés | État |
|-------|----------|-----------------|------|
| 1681 | `get_diagnostics()` Phase 12 | `total_ev_detected`, scan stats | Actif (premier enregistré) |
| 2196 | `api_diagnostics()` Phase 5 | `coverage_apifootball`, provider details | **Ignoré par Flask (doublon)** |

Résultat : le frontend recevait les champs de Phase 12 (sans `odds_coverage`, sans provider fields).

### Champs manquants dans Phase 12
Le Lovable lisant `response.odds_coverage` → `undefined` → **0%**  
Le Lovable lisant `response.bettable` → `undefined` → **0**  
Le Lovable lisant `response.ev_opportunities` → `undefined` → **0**

---

## 2. Tableau d'audit complet

### /api/diagnostics

| KPI affiché | Champ cherché par Lovable | Champ réel backend | Statut avant fix | Statut après fix |
|-------------|--------------------------|-------------------|-----------------|-----------------|
| Odds coverage % | `odds_coverage` | `coverage_apifootball` | ❌ ABSENT | ✅ AJOUTÉ |
| Fixtures today | `fixtures_today` | `total_fixtures_scanned` | ❌ ABSENT | ✅ AJOUTÉ |
| Fixtures with odds | `fixtures_with_odds` | Calculé depuis cache | ❌ ABSENT | ✅ AJOUTÉ |
| EV eligible | `ev_eligible_fixtures` | = `fixtures_with_odds` | ❌ ABSENT | ✅ AJOUTÉ |
| Bettable count | `bettable_count` | Calculé depuis cache | ❌ ABSENT | ✅ AJOUTÉ |
| Limited count | `limited_count` | Calculé depuis cache | ❌ ABSENT | ✅ AJOUTÉ |
| Research count | `research_count` | Calculé depuis cache | ❌ ABSENT | ✅ AJOUTÉ |
| EV opportunities | `ev_opportunities` | `total_ev_detected` | ❌ ABSENT | ✅ AJOUTÉ |
| S-Tier count | `total_s_tier` | `total_s_tier` | ✅ OK | ✅ OK |
| A-Tier count | `total_a_tier` | `total_a_tier` | ✅ OK | ✅ OK |
| Cache age | `cache_age_seconds` | `cache_age_seconds` | ✅ OK | ✅ OK |

### /api/bettable-universe

| KPI affiché | Champ cherché par Lovable | Champ réel backend | Statut avant fix | Statut après fix |
|-------------|--------------------------|-------------------|-----------------|-----------------|
| Bettable | `bettable_count` | `universe_breakdown.BETTABLE.count` | ❌ IMBRIQUÉ | ✅ TOP-LEVEL |
| Limited | `limited_count` | `universe_breakdown.LIMITED_BETTABLE.count` | ❌ IMBRIQUÉ | ✅ TOP-LEVEL |
| Research | `research_count` | `universe_breakdown.RESEARCH_ONLY.count` | ❌ IMBRIQUÉ | ✅ TOP-LEVEL |
| Total | `total_matches` | Calculé | ❌ ABSENT | ✅ AJOUTÉ |
| Odds coverage | `odds_coverage` | Calculé | ❌ ABSENT | ✅ AJOUTÉ |

### /api/data (par match — `match_info`)

| KPI / Champ | Champ Lovable | Champ backend | Statut |
|-------------|--------------|---------------|--------|
| EV picks qualifiés | `ev_qualified` | `match_info.ev_qualified` | ✅ EXISTANT (ajouté dernière session) |
| EV picks rejetés | `ev_rejected` | `match_info.ev_rejected` | ✅ EXISTANT |
| Tier niveau EV | `tier_level` | `match_info.tier_level` | ✅ EXISTANT |
| Source des cotes | `odds_source` | `match_info.odds_source` | ✅ EXISTANT |
| Qualité EV | `ev_quality` | `match_info.ev_quality` | ✅ EXISTANT |
| Régime de marché | `market_regime` | `match_info.market_regime` | ✅ EXISTANT |
| Meilleur marché | `best_market` | `match_info.best_market` | ✅ EXISTANT |
| Meilleur Over | `best_over_market` | `match_info.best_over_market` | ✅ EXISTANT |
| Meilleur Under | `best_under_market` | `match_info.best_under_market` | ✅ EXISTANT |
| Direction recommandée | `recommended_market_direction` | `match_info.recommended_market_direction` | ✅ EXISTANT |
| Profil offensif | `offensive_profile` | `match_info.offensive_profile` (JSON) | ✅ EXISTANT |
| Profil défensif | `defensive_profile` | `match_info.defensive_profile` (JSON) | ✅ EXISTANT |
| Marchés à éviter | `avoid_markets` | `match_info.avoid_markets` | ✅ EXISTANT |
| Raison du pick | `why_pick` | `match_info.why_pick` | ✅ EXISTANT |
| Pourquoi pas S-Tier | `why_not_pick` | `match_info.why_not_pick` | ✅ EXISTANT |
| Facteurs de risque | `risk_factors` | `match_info.risk_factors` | ✅ EXISTANT |
| Accès au marché | `market_access` | `match_info.market_access` | ✅ EXISTANT |
| Score priorité | `bettable_priority_score` | `match_info.bettable_priority_score` | ✅ EXISTANT |
| Score couverture | `odds_coverage_score` | `match_info.odds_coverage_score` | ✅ EXISTANT |
| Tier bettable | `bettable_tier` | `match_info.bettable_tier` | ✅ EXISTANT |

### /api/ev (POST — EV Calculator)

| Champ input | Attendu | Statut |
|-------------|---------|--------|
| `model_probability` | float 0-1 | ✅ OK |
| `bookmaker_odd` | float | ✅ OK |
| `market_type` | string | ✅ OK |

| Champ output (`ev`) | Source | Statut |
|---------------------|--------|--------|
| `ev_percentage` | `ev.ev_percentage` | ✅ OK |
| `edge_percentage` | `ev.edge_percentage` | ✅ OK |
| `market_probability` | `ev.market_probability` | ✅ OK |
| `implied_probability` | `ev.implied_probability` | ✅ OK |
| `bookmaker_odd` | `ev.bookmaker_odd` | ✅ OK |
| `sample_size` | `ev.sample_size` | ✅ OK |

### /api/edge-discovery

| Champ | Statut |
|-------|--------|
| `is_ready` | ✅ OK |
| `summary` | ✅ OK |
| `edge_discovery` | ✅ OK |
| `danger_report` | ✅ OK |

---

## 3. Composants cassés (avant fix)

1. **Dashboard KPI cards** — `odds_coverage`, `bettable_count`, `ev_opportunities`, `fixtures_with_odds`
2. **Bettable Universe page** — `bettable_count`, `limited_count`, `research_count`, `total_matches`, `odds_coverage`
3. **Diagnostics page** — Tous les champs de provider (actifs sur doublon éliminé)
4. **Match cards EV section** — `ev_qualified`, `ev_rejected`, `ev_quality`, `odds_source` (champs non utilisés car Lovable ne les connaissait pas)
5. **Match cards market regime** — `market_regime`, `best_over_market`, `best_under_market`, `recommended_market_direction` jamais affichés

---

## 4. KPIs à recalculer depuis les nouvelles données

Ces KPIs doivent être lus depuis leurs nouvelles sources post-fix :

| KPI | Ancienne source | Nouvelle source | Endpoint |
|-----|----------------|-----------------|----------|
| Odds coverage % | N/A (absent) | `diagnostics.odds_coverage` | `/api/diagnostics` |
| Bettable | `bettable-universe.universe_breakdown.BETTABLE.count` | `diagnostics.bettable_count` OU `bettable-universe.bettable_count` | `/api/diagnostics` |
| Limited | Absent | `diagnostics.limited_count` | `/api/diagnostics` |
| Research | Absent | `diagnostics.research_count` | `/api/diagnostics` |
| EV Opportunities | Absent | `diagnostics.ev_opportunities` (= `total_ev_detected`) | `/api/diagnostics` |
| EV per match | `ev_opportunities[]` (ancien) | `match_info.ev_qualified[]` (nouveau) | `/api/data` |
| Bookmaker odd (EV) | `ev_opportunities[0].bookmaker_odd` | `ev_qualified[0].bookmaker_odd` | `/api/data` |
| EV% | `ev_opportunities[0].ev` | `ev_qualified[0].ev_percentage` | `/api/data` |
| Edge% | `ev_opportunities[0].edge` | `ev_qualified[0].edge_percentage` | `/api/data` |
| Market probability | N/A | `ev_qualified[0].market_probability` | `/api/data` |
| Implied probability | N/A | `ev_qualified[0].implied_probability` | `/api/data` |
| Odds source | N/A | `match_info.odds_source` | `/api/data` |
| EV quality | N/A | `match_info.ev_quality` | `/api/data` |

---

## 5. Fixes backend appliqués

1. **Duplicate route éliminé** : Phase 5 déplacée sur `/api/diagnostics/providers`
2. **`/api/diagnostics`** : ajout de `odds_coverage`, `fixtures_today`, `fixtures_with_odds`, `ev_eligible_fixtures`, `bettable_count`, `limited_count`, `research_count`, `ev_opportunities`
3. **`/api/bettable-universe`** : ajout de `bettable_count`, `limited_count`, `research_count`, `total_matches`, `odds_coverage` au top-level
4. **`/api/data` stats** : ajout de `odds_coverage`, `bettable_count`, `limited_count`, `research_count`

Voir le fichier `prompt_lovable_patch.md` pour le patch frontend complet.
