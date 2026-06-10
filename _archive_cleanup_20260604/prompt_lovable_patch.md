# PATCH LOVABLE — Bindings frontend BetIQ (Fix KPIs à 0)

## Contexte du bug

Le dashboard affichait `odds coverage = 0%`, `bettable = 0`, `ev opportunities = 0`
malgré un backend actif avec `fixtures_today = 80`, `odds_coverage = 46.2%`, `bettable = 22`.

**Cause racine** : les noms de champs utilisés par le frontend ne correspondaient plus
aux champs exposés par le backend.

---

## TÂCHE

Sans modifier aucun style, aucune mise en page, aucun moteur backend :
corriger **uniquement les bindings de données** dans tous les composants listés ci-dessous.

---

## 1. API Endpoints — Configuration correcte

```typescript
const API_BASE = "http://127.0.0.1:5000/api";

const ENDPOINTS = {
  data:            `${API_BASE}/data`,           // scan complet + liste matches
  diagnostics:     `${API_BASE}/diagnostics`,    // KPIs dashboard (UNIFIÉ)
  bettableUniverse:`${API_BASE}/bettable-universe`,
  edgeDiscovery:   `${API_BASE}/edge-discovery`,
  ev:              `${API_BASE}/ev`,             // POST
  perfSummary:     `${API_BASE}/performance/summary`,
  perfByLeague:    `${API_BASE}/performance/by-league`,
  perfByMarket:    `${API_BASE}/performance/by-market`,
  perfByTier:      `${API_BASE}/performance/by-tier`,
  predHistory:     `${API_BASE}/predictions/history`,
  predPending:     `${API_BASE}/predictions/pending`,
  // Provider details only (pas pour le dashboard)
  diagnosticsProviders: `${API_BASE}/diagnostics/providers`,
};
```

---

## 2. Dashboard — KPI Cards

Corriger les bindings de chaque KPI card.
**Source** : `GET /api/diagnostics`

```typescript
// AVANT (cassé)
const oddsCoverage = data.odds_coverage_pct;      // undefined → 0
const bettable     = data.bettable;               // undefined → 0
const evOpps       = data.ev_opportunities_count; // undefined → 0

// APRÈS (correct)
interface DiagnosticsResponse {
  success:              boolean;
  fixtures_today:       number;   // ex: 80
  fixtures_with_odds:   number;   // ex: 37
  ev_eligible_fixtures: number;   // ex: 37
  odds_coverage:        number;   // ex: 46.2  (POURCENTAGE, pas décimal)
  bettable_count:       number;   // ex: 22
  limited_count:        number;   // ex: 18
  research_count:       number;   // ex: 40
  ev_opportunities:     number;   // ex: 12  (matches avec EV détecté)
  total_ev_detected:    number;   // identique à ev_opportunities
  total_s_tier:         number;
  total_a_tier:         number;
  total_watchlist:      number;
  total_analyzed:       number;
  cache_age_seconds:    number | null;
}

const diag = await fetch(ENDPOINTS.diagnostics).then(r => r.json());

// KPI cards
const oddsCoverage  = diag.odds_coverage;         // 46.2 → afficher "46.2%"
const bettableCount = diag.bettable_count;        // 22
const limitedCount  = diag.limited_count;         // 18
const researchCount = diag.research_count;        // 40
const evOpps        = diag.ev_opportunities;      // 12
const fixturesTotal = diag.fixtures_today;        // 80
const withOdds      = diag.fixtures_with_odds;    // 37
```

---

## 3. Bettable Universe Page

**Source** : `GET /api/bettable-universe`

```typescript
// AVANT (cassé — accès imbriqué)
const bettable = data.universe_breakdown?.BETTABLE?.count;   // fragile
const limited  = data.universe_breakdown?.LIMITED_BETTABLE?.count;

// APRÈS (correct — champs top-level)
interface BettableUniverseResponse {
  success:         boolean;
  total_matches:   number;        // 80
  bettable_count:  number;        // 22
  limited_count:   number;        // 18
  research_count:  number;        // 40
  odds_coverage:   number;        // 46.2 %
  universe_breakdown: Record<string, { count: number; pct: number }>;
  bettable_matches: BettableMatch[];
  top_leagues_with_odds:    LeagueRow[];
  top_leagues_without_odds: LeagueRow[];
  country_coverage: CountryRow[];
}

const bu = await fetch(ENDPOINTS.bettableUniverse).then(r => r.json());
const bettableCount = bu.bettable_count;
const limitedCount  = bu.limited_count;
const researchCount = bu.research_count;
const totalMatches  = bu.total_matches;
const oddsCoverage  = bu.odds_coverage;   // %
```

---

## 4. Match Cards — Champs EV (nouveau modèle)

**Source** : `GET /api/data` → `categories.*[].match_info`

```typescript
// Structure d'un match_info (champs EV/market nouveaux)
interface MatchInfo {
  // Anciens champs (inchangés)
  home_team:           string;
  away_team:           string;
  competition:         string;
  analysis_status:     string;
  interest_score:      number;
  confidence_score:    number;
  volatility_score:    number;
  best_pick:           BestPick | null;
  profile_tags:        string[];
  waiting_for_odds:    boolean;

  // Champs marché (existants mais non affichés)
  market_regime:                 string | null;
  best_market:                   string | null;
  best_over_market:              string | null;
  best_under_market:             string | null;
  recommended_market_direction:  string | null;
  avoid_markets:                 string[];
  offensive_profile:             object | null;
  defensive_profile:             object | null;

  // Nouveaux champs EV (ajoutés — à brancher)
  tier_level:      string | null;   // "S_TIER" | "A_TIER" | "WATCHLIST" | null
  ev_quality:      string | null;   // "EXCELLENT" | "GOOD" | "MARGINAL" | null
  odds_source:     string | null;   // "API_FOOTBALL" | "ODDS_API" | "NO_ODDS"

  // EV picks qualifiés (liste — 0 à N entrées)
  ev_qualified: EVPick[];
  // EV picks rejetés
  ev_rejected:  EVPick[];

  // Bettable Universe
  market_access:           string;  // "BETTABLE" | "LIMITED_BETTABLE" | "RESEARCH_ONLY"
  bettable_priority_score: number;
  bettable_tier:           string | null;

  // Explanation Engine
  why_pick:     string[];
  why_not_pick: string[];
  risk_factors: string[];
}

interface EVPick {
  market:              string;
  bookmaker_odd:       number;
  market_probability:  number;  // probabilité modèle (0-1)
  implied_probability: number;  // 1/cote bookmaker (0-1)
  ev_percentage:       number;  // EV en % (positif = value)
  edge_percentage:     number;  // edge vs bookmaker
  sample_size:         number;
  bookmaker:           string;
  ev_grade:            string;  // "A+" | "A" | "B" | "C"
}
```

### Affichage EV picks dans une match card

```typescript
function EVSection({ match }: { match: MatchInfo }) {
  const qualified = match.ev_qualified ?? [];
  const rejected  = match.ev_rejected  ?? [];

  if (!match.odds_source || match.odds_source === "NO_ODDS") {
    return <Badge variant="outline">No odds — Statistical only</Badge>;
  }

  return (
    <div>
      <div className="text-xs text-muted-foreground mb-1">
        Source: {match.odds_source}  •  Quality: {match.ev_quality ?? "—"}
      </div>
      {qualified.map((pick, i) => (
        <EVPickRow key={i} pick={pick} qualified={true} />
      ))}
      {qualified.length === 0 && (
        <span className="text-muted-foreground text-xs">
          No EV picks ({rejected.length} rejected)
        </span>
      )}
    </div>
  );
}

function EVPickRow({ pick, qualified }: { pick: EVPick; qualified: boolean }) {
  return (
    <div className={`flex gap-2 text-sm ${qualified ? "text-green-600" : "text-muted-foreground"}`}>
      <span className="font-medium">{pick.market}</span>
      <span>@{pick.bookmaker_odd.toFixed(2)}</span>
      <span>EV: {pick.ev_percentage.toFixed(1)}%</span>
      <span>Edge: {pick.edge_percentage.toFixed(1)}%</span>
      <Badge variant={qualified ? "default" : "secondary"}>{pick.ev_grade}</Badge>
    </div>
  );
}
```

---

## 5. Market Regime Section (match card)

```typescript
function MarketRegimeSection({ match }: { match: MatchInfo }) {
  if (!match.market_regime) return null;

  return (
    <div className="mt-2 border-t pt-2">
      <div className="text-xs font-semibold text-muted-foreground mb-1">Market Intelligence</div>
      <div className="flex flex-wrap gap-1 text-xs">
        {match.market_regime && (
          <Badge variant="outline">Regime: {match.market_regime}</Badge>
        )}
        {match.best_market && (
          <Badge variant="outline" className="text-green-700">Best: {match.best_market}</Badge>
        )}
        {match.best_over_market && (
          <Badge variant="outline">Over: {match.best_over_market}</Badge>
        )}
        {match.best_under_market && (
          <Badge variant="outline">Under: {match.best_under_market}</Badge>
        )}
        {match.recommended_market_direction && (
          <Badge variant="secondary">→ {match.recommended_market_direction}</Badge>
        )}
      </div>
      {match.avoid_markets && match.avoid_markets.length > 0 && (
        <div className="mt-1 text-xs text-red-500">
          Avoid: {match.avoid_markets.join(", ")}
        </div>
      )}
    </div>
  );
}
```

---

## 6. Bettable Tier Badge (match card)

```typescript
function BettableTierBadge({ match }: { match: MatchInfo }) {
  const colorMap: Record<string, string> = {
    "BETTABLE":           "bg-green-100 text-green-800",
    "LIMITED_BETTABLE":   "bg-yellow-100 text-yellow-800",
    "RESEARCH_ONLY":      "bg-gray-100 text-gray-600",
  };
  const cls = colorMap[match.market_access] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {match.market_access?.replace("_", " ") ?? "Research"}
      {match.bettable_priority_score > 0 && (
        <span className="ml-1 opacity-70">({match.bettable_priority_score.toFixed(0)})</span>
      )}
    </span>
  );
}
```

---

## 7. EV Calculator — bindings de la réponse

**Source** : `POST /api/ev`

```typescript
// Corps de la requête (inchangé)
const body = {
  model_probability: 0.72,
  bookmaker_odd:     1.85,
  market_type:       "FT_UNDER_2_5",
  sample_size:       30,
};

// Réponse
interface EVResponse {
  success: boolean;
  ev: {
    market_probability:  number;   // = model_probability
    implied_probability: number;   // = 1 / bookmaker_odd
    bookmaker_odd:       number;
    ev_percentage:       number;   // EV en %
    edge_percentage:     number;   // edge net
    sample_size:         number;
    ev_grade:            string;   // "A+" | "A" | "B" | "C" | "NEGATIVE"
    is_value_bet:        boolean;
  };
}

// AVANT (cassé)
const ev  = result.ev_percent;    // undefined
const edge = result.edge;         // undefined

// APRÈS (correct)
const res  = await fetch(ENDPOINTS.ev, { method: "POST", body: JSON.stringify(body) }).then(r => r.json());
const ev   = res.ev.ev_percentage;        // 3.2
const edge = res.ev.edge_percentage;      // 5.1
const impliedProb = res.ev.implied_probability; // 0.54
const modelProb   = res.ev.market_probability;  // 0.72
const isValue     = res.ev.is_value_bet;        // true
```

---

## 8. Diagnostics Page — Provider Details

Pour la page Diagnostics (détail provider), utiliser le nouvel endpoint dédié :

```typescript
// AVANT (cassé — même URL que dashboard)
const diag = await fetch(`${API_BASE}/diagnostics`).then(r => r.json());
const primary  = diag.odds_provider_primary;   // peut être absent

// APRÈS (correct — endpoint dédié providers)
const providers = await fetch(ENDPOINTS.diagnosticsProviders).then(r => r.json());
const primary   = providers.odds_provider_primary;
const secondary = providers.odds_provider_secondary;
const status    = providers.odds_provider_status;
const covAF     = providers.coverage_apifootball;   // %
const covOA     = providers.coverage_oddsapi;       // %
const matchedAF = providers.matched_odds_apifootball;
const matchedOA = providers.matched_odds_oddsapi;
```

---

## 9. Performance / History

```typescript
// Performance summary (avec filtre reset optionnel)
GET /api/performance/summary?days=30
GET /api/performance/summary?since_reset=true   // only POST_RESET picks

// Response
interface PerformanceSummary {
  performance: {
    total_wins:         number;
    total_losses:       number;
    total_void:         number;
    hit_rate:           number;   // 0-1
    roi:                number;   // %
    total_profit_loss:  number;
    max_drawdown:       number;
    ev_total:           number;
    ev_wins:            number;
    ev_roi:             number;
  };
  tracking_reset_at:   string | null;
  report_reset_filter: boolean;
}

// Prediction history (avec tracking_generation)
GET /api/predictions/history?limit=50
GET /api/predictions/history?since_reset=true

// Chaque prédiction inclut maintenant :
interface Prediction {
  prediction_id:       string;
  home_team:           string;
  away_team:           string;
  market:              string;
  status:              "PENDING" | "WON" | "LOST" | "VOID";
  profit_loss:         number | null;
  tracking_generation: "POST_RESET" | "LEGACY" | null;
  prediction_date:     string;
}
```

---

## 10. Auto-refresh recommandé

```typescript
// Rafraîchir les diagnostics toutes les 5 minutes (pas le scan)
const refreshDiagnostics = async () => {
  const diag = await fetch(ENDPOINTS.diagnostics).then(r => r.json());
  setOddsCoverage(diag.odds_coverage);
  setBettableCount(diag.bettable_count);
  setEvOpps(diag.ev_opportunities);
  setFixturesToday(diag.fixtures_today);
};

useEffect(() => {
  refreshDiagnostics();
  const interval = setInterval(refreshDiagnostics, 5 * 60 * 1000);
  return () => clearInterval(interval);
}, []);
```

---

## Résumé des composants à patcher

| Composant | Action | Champ corrigé |
|-----------|--------|---------------|
| Dashboard KPI — Odds Coverage | Lire `diag.odds_coverage` | `odds_coverage` |
| Dashboard KPI — Bettable | Lire `diag.bettable_count` | `bettable_count` |
| Dashboard KPI — Limited | Lire `diag.limited_count` | `limited_count` |
| Dashboard KPI — Research | Lire `diag.research_count` | `research_count` |
| Dashboard KPI — EV Opportunities | Lire `diag.ev_opportunities` | `ev_opportunities` |
| Dashboard KPI — Fixtures w/ odds | Lire `diag.fixtures_with_odds` | `fixtures_with_odds` |
| Bettable Universe — Counts | Lire `bu.bettable_count` etc. | top-level fields |
| Match Card — EV Section | Utiliser `match.ev_qualified[]` | `ev_qualified` |
| Match Card — EV Champs | `ev_percentage`, `edge_percentage`, etc. | voir §4 |
| Match Card — Market Regime | Afficher les nouveaux champs market | voir §5 |
| Match Card — Bettable Tier | `market_access`, `bettable_priority_score` | voir §6 |
| EV Calculator | Lire `res.ev.ev_percentage` | `ev_percentage` |
| Diagnostics Detail | Utiliser `/api/diagnostics/providers` | endpoint dédié |
| Prediction History | Lire `tracking_generation` | `tracking_generation` |
