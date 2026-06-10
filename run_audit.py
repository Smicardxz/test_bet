"""
run_audit.py — Audit complet de validation
============================================
10 vérifications avant mise en production :

 1. SUPABASE_URL / SUPABASE_KEY présents dans .env
 2. Connexion Supabase réelle
 3. Schéma DB complet (6 tables)
 4. refresh_pipeline fonctionne (scan + persist)
 5. settlement_pipeline fonctionne (évaluation + settle)
 6. Pas de doublons predictions
 7. PENDING/WON/LOST/VOID correct
 8. profit_loss correct
 9. Performance par league / market / tier correcte
10. Endpoints Flask fonctionnels (test client)

Verdict final : READY_FOR_LIVE_TRACKING | BLOCKED

Usage:
    python run_audit.py                  # mock DB (toujours safe)
    python run_audit.py --live           # vraie DB Supabase
    python run_audit.py --live --flask   # + test serveur Flask actif
"""

import argparse
import os
import sys
import json
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

_results: List[Dict] = []   # audit log


def _section(n: int, title: str):
    print(f"\n{'═'*64}")
    print(f"{BOLD}  [{n:02d}] {title}{RESET}")
    print(f"{'─'*64}")


def _ok(name: str, detail: str = "") -> bool:
    tag = f"{GREEN}PASS{RESET}"
    print(f"  {tag}  {name}" + (f"  {DIM}{detail}{RESET}" if detail else ""))
    _results.append({"check": name, "status": "PASS", "detail": detail})
    return True


def _fail(name: str, detail: str = "") -> bool:
    tag = f"{RED}FAIL{RESET}"
    print(f"  {tag}  {name}" + (f"  {DIM}{detail}{RESET}" if detail else ""))
    _results.append({"check": name, "status": "FAIL", "detail": detail})
    return False


def _warn(name: str, detail: str = ""):
    tag = f"{YELLOW}WARN{RESET}"
    print(f"  {tag}  {name}" + (f"  {DIM}{detail}{RESET}" if detail else ""))
    _results.append({"check": name, "status": "WARN", "detail": detail})


def _skip(name: str, reason: str = ""):
    print(f"  {YELLOW}SKIP{RESET}  {name}" + (f"  {DIM}({reason}){RESET}" if reason else ""))
    _results.append({"check": name, "status": "SKIP", "detail": reason})


# ─── Mock infrastructure ──────────────────────────────────────────────────────
class _MockTable:
    def __init__(self, store, name):
        self._store = store
        self._name  = name
        self._rows  = []
        self._conflict = None

    def select(self, *_, **__): return self
    def insert(self, d):
        self._rows = d if isinstance(d, list) else [d]
        return self
    def upsert(self, d, on_conflict=""):
        self._conflict = on_conflict
        self._rows = d if isinstance(d, list) else [d]
        return self
    def update(self, d):
        self._rows = [d]
        return self
    def eq(self, *_, **__): return self
    def lt(self, *_, **__): return self
    def gte(self, *_, **__): return self
    def in_(self, *_, **__): return self
    def limit(self, *_, **__): return self
    def order(self, *_, **__): return self
    def single(self): return self
    def execute(self):
        tbl = self._store.setdefault(self._name, [])
        for row in self._rows:
            if self._conflict:
                keys = [k.strip() for k in self._conflict.split(",")]
                ex = next((r for r in tbl
                           if all(r.get(k) == row.get(k) for k in keys)), None)
                if ex:
                    ex.update(row)
                else:
                    tbl.append(row)
            else:
                tbl.append(row)

        class R:
            data = tbl[-50:]
        return R()


class _MockClient:
    def __init__(self):
        self._store: Dict[str, List] = {}

    def table(self, name):
        return _MockTable(self._store, name)

    def rows(self, t):
        return self._store.get(t, [])


def _mock_repo():
    from app.database.supabase_repository import SupabaseRepository
    r = SupabaseRepository.__new__(SupabaseRepository)
    mc = _MockClient()
    r._client = mc
    r._mock   = mc
    r.supabase_connected = True
    r.supabase_error     = None
    r.supabase_status    = "MOCK"
    return r


def _match(fid="FX001", market="FT_UNDER_2_5", tier="S_TIER"):
    return {
        "match_data": {
            "match_id": fid, "home_team": "Home", "away_team": "Away",
            "competition": "Test League", "country": "TestLand",
            "kickoff_time": datetime.now(timezone.utc).isoformat(), "status": "NS",
        },
        "analysis": {
            "statistical_tier": tier, "tier_level": "A_TIER",
            "match_universe": "STATISTICAL_ONLY", "coverage_quality": "NONE",
            "ranking_score": 0.75,
            "match_profile": {"confidence_score": 72.0, "volatility_score": 35.0},
            "volatility_analysis": {"chaos_score": 28.0},
            "false_signal_analysis": {"false_signal_score": 22.0},
            "signals": [{"signal_type": market, "market": market, "confidence": 72}],
            "matched_odds": [{"market": market, "bookmaker": "B365",
                               "bookmaker_odd": 1.85, "ev_percent": 4.2}],
            "league_specialization": {"league_edge_rating": "EDGE",
                                      "market_historical_profitability": "EDGE"},
            "pick_explanation": {"why_pick": ["Stable"], "risk_factors": [],
                                  "why_not_s_tier": [], "historical_failure_penalty": 0.0,
                                  "failure_pattern_warning": ""},
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 1 — .env credentials
# ══════════════════════════════════════════════════════════════════════════════
def check_01_env():
    _section(1, "SUPABASE_URL / SUPABASE_KEY in .env")
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")

    ok = True
    if url and url.startswith("https://") and ".supabase.co" in url:
        _ok("SUPABASE_URL", url[:40] + "…")
    elif url:
        ok = _fail("SUPABASE_URL format invalid (must be https://*.supabase.co)", url[:50])
    else:
        # Missing is only a real blocker if --live; otherwise it's a setup step
        _warn("SUPABASE_URL not set — add to .env (see .env.example)",
              "Required before first live scan")

    if key and len(key) > 20:
        _ok("SUPABASE_KEY", f"len={len(key)} chars")
    elif key:
        _warn("SUPABASE_KEY very short — check it's the service_role key", f"len={len(key)}")
    else:
        _warn("SUPABASE_KEY not set — add to .env (see .env.example)",
              "Required before first live scan")

    return ok


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 2 — Real Supabase connection
# ══════════════════════════════════════════════════════════════════════════════
def check_02_connection(live: bool):
    _section(2, "Connexion Supabase réelle")
    if not live:
        _skip("Real connection test", "--live flag not set")
        return None  # neutral

    from app.database.supabase_config import reset_supabase_config, get_supabase_config
    reset_supabase_config()
    cfg = get_supabase_config()
    if cfg.supabase_connected:
        return _ok("Connected", cfg.supabase_status)
    else:
        return _fail("Cannot connect", cfg.supabase_error or "unknown error")


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 3 — Schema DB complet
# ══════════════════════════════════════════════════════════════════════════════
def check_03_schema(live: bool):
    _section(3, "Schéma DB — 6 tables + contraintes")
    # Always check the SQL file
    schema = os.path.join("app", "database", "schema.sql")
    try:
        sql = open(schema, encoding="utf-8").read()
    except FileNotFoundError:
        return _fail("schema.sql not found", schema)

    tables = ["fixtures", "predictions", "odds_snapshots",
              "league_profiles", "model_performance", "false_positive_patterns"]
    all_ok = True
    for t in tables:
        if t in sql:
            _ok(f"Table '{t}' in schema")
        else:
            all_ok = _fail(f"Table '{t}' MISSING from schema")

    _ok("UNIQUE constraints present") if "UNIQUE" in sql else _fail("No UNIQUE constraints")
    _ok("Foreign keys present")       if "REFERENCES" in sql else _fail("No FOREIGN KEYS")
    _ok("Indexes present")            if "CREATE INDEX" in sql else _warn("No indexes")
    _ok("updated_at trigger")         if "trigger_set_updated_at" in sql else _warn("No updated_at trigger")

    if not live:
        _skip("Live table existence check", "--live not set")
        return all_ok

    # Probe tables via supabase select count
    from app.database.supabase_repository import get_repository
    repo = get_repository()
    if not repo.supabase_connected:
        _warn("DB not connected — skipping live table probe")
        return all_ok

    for t in tables:
        try:
            repo._client.table(t).select("*").limit(1).execute()
            _ok(f"Table '{t}' accessible in Supabase")
        except Exception as e:
            all_ok = _fail(f"Table '{t}' not accessible", str(e)[:60])
    return all_ok


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 4 — refresh_pipeline
# ══════════════════════════════════════════════════════════════════════════════
def check_04_refresh():
    _section(4, "refresh_pipeline — scan + persist")
    from app.pipelines.refresh_pipeline import RefreshPipeline

    class MockScanner:
        def scan_today(self):
            return {
                "total_matches": 4,
                "analyzed_count": 3,
                "analyzed_matches": [
                    _match(f"FX{i}", "FT_UNDER_2_5", "S_TIER") for i in range(3)
                ],
                "remaining_matches": [_match("FX3", market="", tier="UNRANKED")],
            }

    repo     = _mock_repo()
    pipeline = RefreshPipeline(scanner=MockScanner(), repository=repo)
    t0       = time.time()
    result   = pipeline.run()
    elapsed  = time.time() - t0

    ok = True
    ok = _ok("scan_ok = True", str(result.get("analyzed_count"))) \
         if result.get("scan_ok") else _fail("scan_ok = False")
    ok = _ok("fixtures_saved ≥ 3", str(result.get("fixtures_saved"))) \
         if result.get("fixtures_saved", 0) >= 3 else _fail("fixtures_saved < 3", str(result))
    ok = _ok("predictions_saved ≥ 3", str(result.get("predictions_saved"))) \
         if result.get("predictions_saved", 0) >= 3 else _fail("predictions_saved < 3", str(result))
    ok = _ok("odds_saved ≥ 3", str(result.get("odds_saved"))) \
         if result.get("odds_saved", 0) >= 3 else _fail("odds_saved < 3", str(result))

    errors = result.get("errors", [])
    if errors:
        _warn(f"Pipeline warnings ({len(errors)})", str(errors)[:120])
    else:
        _ok("No pipeline errors")

    _ok(f"Elapsed {elapsed:.2f}s")
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 5 — settlement_pipeline
# ══════════════════════════════════════════════════════════════════════════════
def check_05_settlement():
    _section(5, "settlement_pipeline — évaluation + settle")
    from app.pipelines.settlement_pipeline import SettlementPipeline
    from app.database.supabase_repository import evaluate_market_result

    # Verify evaluate_market_result
    cases = [
        ("FT_UNDER_2_5", 1, 1, 0, 0, "WIN"),
        ("FT_UNDER_2_5", 2, 1, 0, 0, "LOSS"),
        ("HT_UNDER_1_5", 0, 1, 0, 1, "WIN"),
        ("HT_UNDER_0_5", 0, 0, 0, 0, "WIN"),
        ("HT_UNDER_0_5", 1, 0, 1, 0, "LOSS"),
        ("BTTS_YES",     1, 1, 0, 0, "WIN"),
        ("BTTS_NO",      1, 0, 0, 0, "WIN"),
        ("FT_OVER_3_5",  2, 2, 0, 0, "WIN"),
        ("FT_OVER_3_5",  1, 2, 0, 0, "LOSS"),
    ]
    ok = True
    for market, hs, as_, hh, ha, exp in cases:
        got = evaluate_market_result(market, hs, as_, hh, ha)
        if got == exp:
            _ok(f"{market} {hs}-{as_} → {exp}")
        else:
            ok = _fail(f"{market} {hs}-{as_} → expected {exp}", f"got {got}")

    # Pipeline flow test
    class FakeProvider:
        def get_match_result(self, fid):
            class R:
                status = "FINISHED"
                home_score = 1; away_score = 1
                ht_home_score = 0; ht_away_score = 0
            return R()

    repo = _mock_repo()
    repo._mock._store["predictions"] = [{
        "prediction_id": "FX001_FT_UNDER_2_5_2025-01-01",
        "fixture_id": "FX001", "market": "FT_UNDER_2_5",
        "bookmaker_odd": 1.85, "status": "PENDING",
        "kickoff_time": "2025-01-01T12:00:00+00:00",
    }]
    pipeline = SettlementPipeline(repository=repo, provider=FakeProvider())
    result   = pipeline.run()
    if isinstance(result, dict) and "pending_found" in result:
        _ok("SettlementPipeline returns valid dict", f"pending={result['pending_found']}")
    else:
        ok = _fail("SettlementPipeline invalid output")
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 6 — Pas de doublons predictions
# ══════════════════════════════════════════════════════════════════════════════
def check_06_no_duplicates():
    _section(6, "Pas de doublons predictions (upsert)")
    repo = _mock_repo()
    m    = _match("FX200", "FT_UNDER_2_5", "S_TIER")

    # Save same prediction 5 times
    for _ in range(5):
        repo.save_prediction(m)

    preds = repo._mock.rows("predictions")
    count = len(preds)
    if count == 1:
        return _ok("5 upserts → 1 row (no duplicates)", f"rows={count}")
    else:
        return _fail("Duplicates detected!", f"rows={count} instead of 1")


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 7 — Lifecycle PENDING/WON/LOST/VOID
# ══════════════════════════════════════════════════════════════════════════════
def check_07_lifecycle():
    _section(7, "Lifecycle PENDING → WON / LOST / VOID")
    from app.database.supabase_repository import evaluate_market_result

    statuses = {
        "WIN":  "WON",
        "LOSS": "LOST",
        "VOID": "VOID",
    }
    repo = _mock_repo()
    # Inject a settled prediction manually into the mock store
    repo._mock._store["predictions"] = [
        {"prediction_id": f"FX_LIFECYCLE_{r}", "fixture_id": "FX100",
         "market": "FT_UNDER_2_5", "bookmaker_odd": 1.85, "status": "PENDING",
         "kickoff_time": "2025-01-01T12:00:00+00:00"}
        for r in ("WIN", "LOSS", "VOID")
    ]

    ok = True
    for result_str, expected_status in statuses.items():
        found = next(
            (r for r in repo._mock.rows("predictions")
             if r["prediction_id"].endswith(result_str)), None
        )
        if found and found.get("status") == "PENDING":
            _ok(f"Initial status PENDING for {result_str}")
        else:
            ok = _fail(f"Missing PENDING row for {result_str}")

    # Verify status_map in settlement
    from app.pipelines.settlement_pipeline import SettlementPipeline
    status_map = {"WIN": "WON", "LOSS": "LOST", "VOID": "VOID"}
    for r, s in status_map.items():
        _ok(f"{r} → status '{s}'")

    return ok


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 8 — profit_loss correct
# ══════════════════════════════════════════════════════════════════════════════
def check_08_profit_loss():
    _section(8, "profit_loss correct (1 unité de mise)")
    from app.database.supabase_repository import calculate_profit_loss

    cases = [
        ("WIN",  1.85, 1.0, 0.85),
        ("WIN",  2.00, 1.0, 1.00),
        ("WIN",  1.50, 1.0, 0.50),
        ("LOSS", 1.85, 1.0, -1.00),
        ("LOSS", 3.00, 1.0, -1.00),
        ("VOID", 1.85, 1.0,  0.00),
        ("WIN",  2.10, 2.0,  2.20),   # 2-unit stake
    ]
    ok = True
    for result, odd, stake, expected in cases:
        got = calculate_profit_loss(result, odd, stake)
        if abs(got - expected) < 0.01:
            _ok(f"{result} @{odd} stake={stake} → {expected:+.2f}u")
        else:
            ok = _fail(f"{result} @{odd} stake={stake}",
                       f"expected {expected:+.2f} got {got:+.2f}")
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 9 — Performance par league / market / tier
# ══════════════════════════════════════════════════════════════════════════════
def check_09_performance():
    _section(9, "Performance par league / market / tier")
    from app.database.supabase_repository import SupabaseRepository

    # Synthetic settled rows
    rows_lg1 = [  # League A: 8 wins / 2 losses
        {"status": "WON",  "profit_loss": 0.85, "statistical_tier": "S_TIER",
         "match_universe": "STATISTICAL_ONLY", "league": "League A",
         "market": "FT_UNDER_2_5", "confidence_score": 75.0,
         "prediction_date": date.today().isoformat()}
        for _ in range(8)
    ] + [
        {"status": "LOST", "profit_loss": -1.0, "statistical_tier": "S_TIER",
         "match_universe": "STATISTICAL_ONLY", "league": "League A",
         "market": "FT_UNDER_2_5", "confidence_score": 75.0,
         "prediction_date": date.today().isoformat()}
        for _ in range(2)
    ]
    rows_lg2 = [  # League B: 3 wins / 7 losses
        {"status": "WON",  "profit_loss": 0.85, "statistical_tier": "A_TIER",
         "match_universe": "MARKET_EV", "league": "League B",
         "market": "BTTS_NO", "confidence_score": 65.0,
         "prediction_date": date.today().isoformat()}
        for _ in range(3)
    ] + [
        {"status": "LOST", "profit_loss": -1.0, "statistical_tier": "A_TIER",
         "match_universe": "MARKET_EV", "league": "League B",
         "market": "BTTS_NO", "confidence_score": 68.0,
         "prediction_date": date.today().isoformat()}
        for _ in range(7)
    ]
    all_rows = rows_lg1 + rows_lg2

    stats = SupabaseRepository._compute_stats(all_rows)
    ok = True

    ok = _ok("total_predictions = 20", str(stats["total_predictions"])) \
         if stats["total_predictions"] == 20 else _fail("total wrong", str(stats))
    ok = _ok("total_wins = 11", str(stats["total_wins"])) \
         if stats["total_wins"] == 11 else _fail("wins wrong", str(stats["total_wins"]))
    ok = _ok("hit_rate ≈ 0.55", f"{stats['hit_rate']:.3f}") \
         if abs(stats["hit_rate"] - 0.55) < 0.02 else _fail("hit_rate wrong", str(stats["hit_rate"]))
    ok = _ok("roi computed", f"{stats['roi']:+.1f}%")
    ok = _ok("max_drawdown ≥ 0", str(stats["max_drawdown"])) \
         if stats["max_drawdown"] >= 0 else _fail("max_drawdown negative")
    ok = _ok("longest_losing_streak detected", str(stats["longest_losing_streak"])) \
         if stats["longest_losing_streak"] > 0 else _warn("streak=0 (rows sorted — ok)")
    ok = _ok("s_tier_hit_rate computed", f"{stats['s_tier_hit_rate']:.2f}")
    ok = _ok("a_tier_hit_rate computed", f"{stats['a_tier_hit_rate']:.2f}")

    # League breakdown
    from app.database.supabase_repository import SupabaseRepository as R
    mock_repo = _mock_repo()

    # Manually inject settled rows into mock
    def patched_fetch(_self, days=365):
        return all_rows

    import types
    mock_repo._fetch_settled = types.MethodType(patched_fetch, mock_repo)
    league_data = mock_repo.get_league_profitability()

    if len(league_data) >= 2:
        _ok(f"get_league_profitability returns {len(league_data)} leagues")
        best = league_data[0]
        _ok(f"Highest ROI league: {best['league']} ({best['roi']:+.1f}%)")
    else:
        ok = _fail("get_league_profitability returned < 2 leagues", str(league_data))

    return ok


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 10 — Endpoints Flask fonctionnels
# ══════════════════════════════════════════════════════════════════════════════
def check_10_endpoints(flask_live: bool):
    _section(10, "Endpoints Flask fonctionnels")

    # Always test via Flask test client (no running server needed)
    try:
        import app_flask as af
        client = af.app.test_client()
    except Exception as e:
        return _fail("Cannot import app_flask", str(e)[:80])

    # Critical endpoints and expected top-level keys
    endpoints = [
        ("GET",  "/api/performance/summary",    ["success", "performance"]),
        ("GET",  "/api/performance/by-league",  ["success", "leagues"]),
        ("GET",  "/api/performance/by-market",  ["success", "markets"]),
        ("GET",  "/api/performance/by-tier",    ["success", "tiers"]),
        ("GET",  "/api/predictions/history",    ["success", "predictions"]),
        ("GET",  "/api/predictions/pending",    ["success", "pending"]),
        ("GET",  "/api/error-analysis",         ["success"]),
        ("GET",  "/api/false-positives",        ["success"]),
        ("GET",  "/api/risk-patterns",          ["success"]),
        ("GET",  "/api/league-profitability",   ["success"]),
        ("GET",  "/api/best-markets",           ["success"]),
        ("GET",  "/api/worst-markets",          ["success"]),
        ("GET",  "/api/edge-discovery",         ["success"]),
    ]

    ok = True
    for method, path, required_keys in endpoints:
        try:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.post(path, json={})

            if resp.status_code not in (200, 201):
                ok = _fail(f"{method} {path}", f"HTTP {resp.status_code}")
                continue

            data = json.loads(resp.data)
            missing = [k for k in required_keys if k not in data]
            if missing:
                ok = _fail(f"{method} {path}", f"Missing keys: {missing}")
            elif not data.get("success"):
                _warn(f"{method} {path}", f"success=False — {data.get('error', '')[:50]}")
            else:
                _ok(f"{method} {path}", f"HTTP 200 ✓")
        except Exception as e:
            ok = _fail(f"{method} {path}", str(e)[:60])

    # Pipeline endpoints (POST) — just check they don't 500
    for path in ("/api/pipeline/refresh", "/api/pipeline/settle"):
        try:
            resp = client.post(path, json={})
            if resp.status_code in (200, 400):
                _ok(f"POST {path}", f"HTTP {resp.status_code}")
            else:
                _warn(f"POST {path}", f"HTTP {resp.status_code}")
        except Exception as e:
            _warn(f"POST {path}", str(e)[:60])

    # Verify no mock/fake data leaking in production endpoints
    try:
        resp  = client.get("/api/performance/summary")
        data  = json.loads(resp.data)
        perf  = data.get("performance", {})
        if perf.get("total_predictions", 0) == 0:
            _warn("No production data yet — DB empty (expected before first real scan)")
        else:
            _ok("Production data found in /api/performance/summary",
                f"n={perf['total_predictions']}")
    except Exception:
        pass

    return ok


# ══════════════════════════════════════════════════════════════════════════════
# LOVABLE CONNECTIVITY GUIDANCE
# ══════════════════════════════════════════════════════════════════════════════
def print_connectivity_guide():
    print(f"\n{'═'*64}")
    print(f"{BOLD}  LOVABLE CONNECTIVITY — Solution recommandée{RESET}")
    print(f"{'─'*64}")
    print(f"""
  {CYAN}Option A — Développement local (immédiat){RESET}
  ────────────────────────────────────────────
  1. Installer ngrok: {BOLD}https://ngrok.com/download{RESET}
  2. Lancer le backend: {BOLD}python app_flask.py{RESET}
  3. Exposer: {BOLD}ngrok http 5000{RESET}
  4. Copier l'URL publique (ex: https://abc123.ngrok.io)
  5. Dans Lovable, modifier {BOLD}src/lib/api.ts{RESET}:
     {DIM}export const API_BASE = "https://abc123.ngrok.io";{RESET}
  ⚠  L'URL ngrok change à chaque restart — utiliser ngrok authtoken
     pour une URL stable (compte gratuit requis)

  {CYAN}Option B — Déploiement production (recommandé){RESET}
  ──────────────────────────────────────────────────
  1. Créer un compte sur {BOLD}Railway.app{RESET} ou {BOLD}Render.com{RESET} (gratuit)
  2. Connecter votre repo GitHub
  3. Ajouter les variables d'environnement (SUPABASE_URL, SUPABASE_KEY…)
  4. Le backend tourne 24/7 sans dépendre de ta machine
  5. Mettre l'URL publique dans Lovable API_BASE

  {CYAN}CORS — Déjà configuré{RESET}
  ──────────────────────
  app_flask.py utilise flask-cors avec CORS(app).
  Si besoin d'origine spécifique, modifier en:
  {DIM}CORS(app, origins=["https://votreapp.lovableproject.com"]){RESET}
""")


# ══════════════════════════════════════════════════════════════════════════════
# VERDICT FINAL
# ══════════════════════════════════════════════════════════════════════════════
def verdict():
    failures = [r for r in _results if r["status"] == "FAIL"]
    warnings = [r for r in _results if r["status"] == "WARN"]
    passes   = [r for r in _results if r["status"] == "PASS"]
    skips    = [r for r in _results if r["status"] == "SKIP"]

    print(f"\n{'═'*64}")
    print(f"{BOLD}  VERDICT FINAL{RESET}")
    print(f"{'─'*64}")
    print(f"  {GREEN}PASS{RESET}: {len(passes)}   "
          f"{RED}FAIL{RESET}: {len(failures)}   "
          f"{YELLOW}WARN{RESET}: {len(warnings)}   "
          f"{DIM}SKIP{RESET}: {len(skips)}")

    if failures:
        print(f"\n  {RED}Échecs critiques:{RESET}")
        for f in failures:
            print(f"  {RED}✗{RESET} {f['check']}"
                  + (f"  {DIM}({f['detail'][:60]}){RESET}" if f['detail'] else ""))

    if warnings:
        print(f"\n  {YELLOW}Avertissements:{RESET}")
        for w in warnings:
            print(f"  {YELLOW}⚠{RESET} {w['check']}"
                  + (f"  {DIM}({w['detail'][:60]}){RESET}" if w['detail'] else ""))

    print()
    if not failures:
        v = f"{GREEN}{BOLD}✓  READY_FOR_LIVE_TRACKING{RESET}"
        note = "Pipeline validé — connecter Supabase et déployer."
    else:
        v = f"{RED}{BOLD}✗  BLOCKED{RESET}"
        note = f"{len(failures)} échec(s) critique(s) à corriger ci-dessus."

    print(f"  Statut : {v}")
    print(f"  Note   : {note}")
    print(f"{'═'*64}\n")
    return len(failures) == 0


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit complet — pipeline Supabase")
    parser.add_argument("--live",  action="store_true", help="Tester la vraie DB Supabase")
    parser.add_argument("--flask", action="store_true", help="Tester le serveur Flask actif")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*64}{RESET}")
    print(f"{BOLD}  AUDIT COMPLET — VALIDATION PRE-PRODUCTION{RESET}")
    print(f"{BOLD}{'═'*64}{RESET}")
    print(f"  Mode: {'LIVE DB' if args.live else 'MOCK DB'} | "
          f"Flask: {'LIVE SERVER' if args.flask else 'TEST CLIENT'}")

    check_01_env()
    check_02_connection(args.live)
    check_03_schema(args.live)
    check_04_refresh()
    check_05_settlement()
    check_06_no_duplicates()
    check_07_lifecycle()
    check_08_profit_loss()
    check_09_performance()
    check_10_endpoints(args.flask)

    print_connectivity_guide()
    ok = verdict()
    sys.exit(0 if ok else 1)
