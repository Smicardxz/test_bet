"""
odds_coverage_report.py — Diagnostic The Odds API
===================================================

Objectif : comprendre POURQUOI aucune cote ne matche.

Ce script est autonome (pas besoin du serveur Flask).
Il lit directement la clé ODDS_API_KEY depuis .env.

Rapport généré : odds_coverage_report.json

Sections :
  1. Clé API & quota
  2. Sports soccer disponibles (The Odds API catalogue)
  3. Ligues scannées aujourd'hui (API-Football) — couvertes ou non
  4. Événements récupérés par sport_key
  5. Bookmakers et marchés disponibles
  6. Noms d'équipes : The Odds API vs API-Football
  7. Mapping failures avec raison précise
  8. Recommandations

Usage :
    python odds_coverage_report.py
    python odds_coverage_report.py --url http://localhost:5000   # pour les matchs scannés
    python odds_coverage_report.py --no-flask                    # sans Flask (sport catalogue seulement)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# ─── Charger .env sans dépendances ────────────────────────────────────────────
def _load_env(path: str = ".env"):
    """Charge les variables d'env depuis .env (sans python-dotenv requis)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

_load_env()

# ─── Config ───────────────────────────────────────────────────────────────────
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "").strip()
ODDS_API_BASE = os.getenv("ODDS_API_URL", "https://api.the-odds-api.com/v4").rstrip("/")
DEFAULT_FLASK = "http://localhost:5000"

# Même mappings que external_odds_provider.py
SOCCER_SPORT_KEYS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_france_ligue1",
    "soccer_italy_serie_a",
    "soccer_netherlands_eredivisie",
    "soccer_portugal_primeira_liga",
    "soccer_turkey_super_league",
    "soccer_belgium_first_div",
    "soccer_england_efl_champ",
    "soccer_scotland_premiership",
    "soccer_brazil_campeonato",
    "soccer_argentina_primera_division",
    "soccer_usa_mls",
    "soccer_mexico_ligamx",
    "soccer_denmark_superliga",
    "soccer_norway_eliteserien",
    "soccer_sweden_allsvenskan",
    "soccer_poland_ekstraklasa",
    "soccer_greece_super_league",
    "soccer_japan_j_league",
]

COUNTRY_TO_SPORT_KEY: Dict[str, str] = {
    "england":     "soccer_epl",
    "spain":       "soccer_spain_la_liga",
    "germany":     "soccer_germany_bundesliga",
    "france":      "soccer_france_ligue1",
    "italy":       "soccer_italy_serie_a",
    "netherlands": "soccer_netherlands_eredivisie",
    "portugal":    "soccer_portugal_primeira_liga",
    "turkey":      "soccer_turkey_super_league",
    "belgium":     "soccer_belgium_first_div",
    "scotland":    "soccer_scotland_premiership",
    "brazil":      "soccer_brazil_campeonato",
    "argentina":   "soccer_argentina_primera_division",
    "usa":         "soccer_usa_mls",
    "mexico":      "soccer_mexico_ligamx",
    "denmark":     "soccer_denmark_superliga",
    "norway":      "soccer_norway_eliteserien",
    "sweden":      "soccer_sweden_allsvenskan",
    "poland":      "soccer_poland_ekstraklasa",
    "greece":      "soccer_greece_super_league",
    "japan":       "soccer_japan_j_league",
}

LEAGUE_TO_SPORT_KEY: Dict[str, str] = {
    "premier league":          "soccer_epl",
    "la liga":                 "soccer_spain_la_liga",
    "bundesliga":              "soccer_germany_bundesliga",
    "ligue 1":                 "soccer_france_ligue1",
    "serie a":                 "soccer_italy_serie_a",
    "eredivisie":              "soccer_netherlands_eredivisie",
    "primeira liga":           "soccer_portugal_primeira_liga",
    "super lig":               "soccer_turkey_super_league",
    "jupiler":                 "soccer_belgium_first_div",
    "pro league":              "soccer_belgium_first_div",
    "efl championship":        "soccer_england_efl_champ",
    "english championship":    "soccer_england_efl_champ",
    "premiership":             "soccer_scotland_premiership",
    "brasileirao":             "soccer_brazil_campeonato",
    "liga profesional":        "soccer_argentina_primera_division",
    "primera division":        "soccer_argentina_primera_division",
    "mls":                     "soccer_usa_mls",
    "liga mx":                 "soccer_mexico_ligamx",
    "superliga":               "soccer_denmark_superliga",
    "eliteserien":             "soccer_norway_eliteserien",
    "allsvenskan":             "soccer_sweden_allsvenskan",
    "ekstraklasa":             "soccer_poland_ekstraklasa",
    "super league 1":          "soccer_greece_super_league",
    "greek super league":      "soccer_greece_super_league",
    "j1 league":               "soccer_japan_j_league",
    "j league":                "soccer_japan_j_league",
}

# Couleurs console
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

quota_remaining: Optional[int] = None


# ─── HTTP helpers ─────────────────────────────────────────────────────────────
def _odds_get(endpoint: str, params: dict = None) -> Optional[any]:
    """GET vers The Odds API. Retourne None si erreur."""
    global quota_remaining
    if not ODDS_API_KEY:
        return None
    p = dict(params or {})
    p["apiKey"] = ODDS_API_KEY
    qs = "&".join(f"{k}={v}" for k, v in p.items())
    url = f"{ODDS_API_BASE}{endpoint}?{qs}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            remaining = resp.headers.get("x-requests-remaining")
            if remaining:
                try:
                    quota_remaining = int(remaining)
                except Exception:
                    pass
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        code = e.code
        if code == 401:
            print(f"  {RED}✗ 401 Unauthorized — ODDS_API_KEY invalide ou expirée{RESET}")
        elif code == 422:
            print(f"  {YELLOW}⚠ 422 sport non supporté: {endpoint}{RESET}")
        elif code == 429:
            print(f"  {RED}✗ 429 Quota épuisé{RESET}")
        else:
            print(f"  {YELLOW}⚠ HTTP {code} sur {endpoint}{RESET}")
        return None
    except Exception as e:
        print(f"  {YELLOW}⚠ Erreur réseau: {e}{RESET}")
        return None


def _flask_get(url: str) -> Optional[dict]:
    """GET vers Flask API."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


# ─── Matching ─────────────────────────────────────────────────────────────────
def _normalize(name: str) -> str:
    return (
        name.lower()
        .replace("fc ", "").replace(" fc", "")
        .replace("cf ", "").replace(" cf", "")
        .replace("sc ", "").replace(" sc", "")
        .replace("  ", " ").strip()
    )


def _fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def resolve_sport_key(competition: str, country: str) -> Optional[str]:
    """Même logique que external_odds_provider.resolve_sport_key."""
    import re
    comp_lc = (competition or "").lower().strip()
    ctry_lc = (country or "").lower().strip()

    if ctry_lc:
        sk = COUNTRY_TO_SPORT_KEY.get(ctry_lc)
        if sk:
            return sk

    for fragment, sport_key in LEAGUE_TO_SPORT_KEY.items():
        pattern = r'\b' + re.escape(fragment) + r'(\b|$)'
        if re.search(pattern, comp_lc):
            return sport_key

    return None


def find_best_match(home: str, away: str, all_events: Dict[str, List[dict]]) -> dict:
    """Cherche le meilleur match dans tous les événements. Retourne un dict de résultat."""
    best = {"score": 0.0, "event": None, "sport_key": None}
    for sk, events in all_events.items():
        for ev in events:
            sh = _fuzzy(home, ev.get("home_team", ""))
            sa = _fuzzy(away, ev.get("away_team", ""))
            combined = (sh + sa) / 2.0
            if combined > best["score"]:
                best = {
                    "score": combined,
                    "event": ev,
                    "sport_key": sk,
                    "score_home": sh,
                    "score_away": sa,
                }
    return best


# ─── Sections du rapport ──────────────────────────────────────────────────────

def section_api_status() -> dict:
    """Vérifie la clé API et la quota."""
    print(f"\n{BOLD}[1/7] Statut clé API{RESET}")
    if not ODDS_API_KEY:
        print(f"  {RED}✗ ODDS_API_KEY absente dans .env{RESET}")
        print(f"  {YELLOW}  → Ajoute ODDS_API_KEY=<ta_clé> dans .env{RESET}")
        return {"key_present": False, "key_length": 0, "quota_remaining": None, "error": "MISSING_KEY"}

    print(f"  {GREEN}✓ ODDS_API_KEY présente (longueur: {len(ODDS_API_KEY)}){RESET}")

    # Test avec un appel léger
    data = _odds_get("/sports", {"all": "false"})
    if data is None:
        return {"key_present": True, "key_length": len(ODDS_API_KEY), "quota_remaining": quota_remaining, "error": "API_UNREACHABLE"}

    print(f"  {GREEN}✓ API accessible | Quota restant: {quota_remaining}{RESET}")
    return {
        "key_present": True,
        "key_length": len(ODDS_API_KEY),
        "quota_remaining": quota_remaining,
        "error": None,
    }


def section_soccer_sports(all_sports: list) -> dict:
    """Liste les sports soccer disponibles dans le catalogue de The Odds API."""
    print(f"\n{BOLD}[2/7] Sports soccer disponibles (The Odds API){RESET}")

    soccer_sports = [s for s in (all_sports or []) if "soccer" in s.get("key", "").lower()]
    active = [s for s in soccer_sports if s.get("active")]
    inactive = [s for s in soccer_sports if not s.get("active")]

    print(f"  Total soccer: {len(soccer_sports)} ({len(active)} actifs, {len(inactive)} inactifs)")

    in_our_list = [s for s in soccer_sports if s["key"] in SOCCER_SPORT_KEYS]
    not_in_our_list = [s for s in soccer_sports if s["key"] not in SOCCER_SPORT_KEYS]

    print(f"  Dans notre mapping: {len(in_our_list)}")
    print(f"  {YELLOW}Non couverts dans notre mapping: {len(not_in_our_list)}{RESET}")
    for s in not_in_our_list[:10]:
        print(f"    {YELLOW}+ {s['key']} ({s.get('title','?')}){RESET}")

    return {
        "total_soccer_sports": len(soccer_sports),
        "active_soccer_sports": len(active),
        "in_our_mapping": [s["key"] for s in in_our_list],
        "not_in_our_mapping": [{"key": s["key"], "title": s.get("title", "")} for s in not_in_our_list],
        "all_soccer_sports": [
            {"key": s["key"], "title": s.get("title", ""), "active": s.get("active", False)}
            for s in sorted(soccer_sports, key=lambda x: x["key"])
        ],
    }


def section_fetch_events() -> Tuple[Dict[str, List[dict]], dict]:
    """Fetche les événements pour tous les sport_keys."""
    print(f"\n{BOLD}[3/7] Événements récupérés (sport_keys){RESET}")

    events_by_sport: Dict[str, List[dict]] = {}
    sport_summary = []
    total_events = 0

    for sk in SOCCER_SPORT_KEYS:
        print(f"  Fetching {sk}...", end=" ", flush=True)
        data = _odds_get(
            f"/sports/{sk}/odds",
            {"regions": "eu", "markets": "h2h,totals", "oddsFormat": "decimal", "dateFormat": "iso"},
        )
        if data and isinstance(data, list):
            events_by_sport[sk] = data
            total_events += len(data)
            print(f"{GREEN}{len(data)} events{RESET}")
            sport_summary.append({"sport_key": sk, "events": len(data), "status": "OK"})
        else:
            print(f"{YELLOW}0 events{RESET}")
            sport_summary.append({"sport_key": sk, "events": 0, "status": "EMPTY_OR_ERROR"})
        time.sleep(0.15)  # petit délai pour éviter rate-limiting

    print(f"\n  {BOLD}Total événements: {total_events} dans {len(events_by_sport)} sport_keys{RESET}")
    print(f"  Quota restant: {quota_remaining}")

    return events_by_sport, {
        "total_events": total_events,
        "sport_keys_with_data": len(events_by_sport),
        "quota_used_this_run": len(SOCCER_SPORT_KEYS),
        "quota_remaining_after": quota_remaining,
        "by_sport": sport_summary,
    }


def section_bookmakers_markets(events_by_sport: Dict[str, List[dict]]) -> dict:
    """Extrait bookmakers et marchés vus dans les événements."""
    print(f"\n{BOLD}[4/7] Bookmakers et marchés disponibles{RESET}")

    bookmakers: set = set()
    markets: set = set()
    totals_lines: set = set()

    for events in events_by_sport.values():
        for ev in events:
            for bk in ev.get("bookmakers", []):
                bookmakers.add(bk.get("title", "?"))
                for mkt in bk.get("markets", []):
                    mk = mkt.get("key", "")
                    markets.add(mk)
                    if mk == "totals":
                        for oc in mkt.get("outcomes", []):
                            pt = oc.get("point")
                            if pt is not None:
                                totals_lines.add(float(pt))

    print(f"  Bookmakers: {len(bookmakers)}")
    for b in sorted(bookmakers):
        print(f"    • {b}")
    print(f"\n  Marchés: {sorted(markets)}")
    print(f"  Lignes totals disponibles: {sorted(totals_lines)}")

    return {
        "bookmakers": sorted(bookmakers),
        "markets": sorted(markets),
        "totals_lines": sorted(totals_lines),
    }


def section_league_coverage(scanned_matches: list, events_by_sport: Dict[str, List[dict]]) -> dict:
    """Analyse la couverture par ligue — pour chaque ligue scannée, est-elle dans The Odds API ?"""
    print(f"\n{BOLD}[5/7] Couverture ligue (matchs scannés vs The Odds API){RESET}")

    # Ligue → sport_key résolu
    league_map: Dict[str, dict] = {}
    for m in scanned_matches:
        league  = m.get("league", "?")
        country = m.get("country", "?")
        key = f"{league}|{country}"
        if key not in league_map:
            sk = resolve_sport_key(league, country)
            has_events = bool(events_by_sport.get(sk)) if sk else False
            league_map[key] = {
                "league":       league,
                "country":      country,
                "sport_key":    sk,
                "has_events":   has_events,
                "match_count":  0,
                "coverage_status": (
                    "COVERED"       if has_events else
                    "KEY_RESOLVED_NO_EVENTS" if sk else
                    "NOT_IN_MAPPING"
                ),
            }
        league_map[key]["match_count"] += 1

    covered     = [v for v in league_map.values() if v["coverage_status"] == "COVERED"]
    no_mapping  = [v for v in league_map.values() if v["coverage_status"] == "NOT_IN_MAPPING"]
    no_events   = [v for v in league_map.values() if v["coverage_status"] == "KEY_RESOLVED_NO_EVENTS"]

    print(f"  Ligues uniques scannées: {len(league_map)}")
    print(f"  {GREEN}Couvertes par The Odds API: {len(covered)}{RESET}")
    if covered:
        for v in sorted(covered, key=lambda x: -x["match_count"]):
            print(f"    {GREEN}✓{RESET} {v['league']} ({v['country']}) → {v['sport_key']} [{v['match_count']} matchs]")

    print(f"  {RED}Sans sport_key (pas dans notre mapping): {len(no_mapping)}{RESET}")
    for v in sorted(no_mapping, key=lambda x: -x["match_count"]):
        print(f"    {RED}✗{RESET} {v['league']} ({v['country']}) → AUCUN KEY [{v['match_count']} matchs]")

    if no_events:
        print(f"  {YELLOW}Key résolu mais sans événements: {len(no_events)}{RESET}")
        for v in no_events:
            print(f"    {YELLOW}~{RESET} {v['league']} ({v['country']}) → {v['sport_key']} [0 events]")

    return {
        "total_unique_leagues": len(league_map),
        "covered_count": len(covered),
        "not_in_mapping_count": len(no_mapping),
        "key_resolved_no_events_count": len(no_events),
        "leagues": sorted(league_map.values(), key=lambda x: x["league"]),
    }


def section_team_mapping(scanned_matches: list, events_by_sport: Dict[str, List[dict]]) -> dict:
    """Pour chaque match scanné, tente le mapping et détaille les échecs."""
    print(f"\n{BOLD}[6/7] Mapping équipes (API-Football → The Odds API){RESET}")

    if not events_by_sport:
        print(f"  {YELLOW}Aucun événement récupéré — impossible de tester le mapping{RESET}")
        return {"attempts": [], "success": 0, "failed": 0, "no_events_for_league": 0}

    results = []
    success_count = failed_count = no_league_count = 0

    for m in scanned_matches:
        league  = m.get("league", "")
        country = m.get("country", "")
        home    = m.get("home_team", "")
        away    = m.get("away_team", "")

        if not home or not away:
            continue

        sk = resolve_sport_key(league, country)

        # Cas 1: Ligue pas dans notre mapping
        if not sk:
            no_league_count += 1
            results.append({
                "match":            f"{home} vs {away}",
                "league":           league,
                "country":          country,
                "home_api":         home,
                "away_api":         away,
                "sport_key":        None,
                "failure_reason":   "NO_SPORT_KEY",
                "failure_detail":   f"Ligue '{league}' ({country}) absente de COUNTRY_TO_SPORT_KEY et LEAGUE_TO_SPORT_KEY",
                "best_odds_match":  None,
                "best_score":       0.0,
                "status":           "FAILED",
            })
            continue

        # Cas 2: Sport_key résolu mais pas d'événements
        sport_events = events_by_sport.get(sk, [])
        if not sport_events:
            no_league_count += 1
            results.append({
                "match":            f"{home} vs {away}",
                "league":           league,
                "country":          country,
                "home_api":         home,
                "away_api":         away,
                "sport_key":        sk,
                "failure_reason":   "NO_EVENTS_FOR_SPORT",
                "failure_detail":   f"sport_key '{sk}' résolu mais 0 événements récupérés de The Odds API",
                "best_odds_match":  None,
                "best_score":       0.0,
                "status":           "FAILED",
            })
            continue

        # Cas 3: Cherche le meilleur match dans les événements
        best = find_best_match(home, away, {sk: sport_events})
        score = best.get("score", 0.0)
        event = best.get("event")

        entry = {
            "match":      f"{home} vs {away}",
            "league":     league,
            "country":    country,
            "home_api":   home,
            "away_api":   away,
            "sport_key":  sk,
            "best_score": round(score, 3),
            "home_score": round(best.get("score_home", 0), 3),
            "away_score": round(best.get("score_away", 0), 3),
        }

        if event:
            entry["home_odds_api"] = event.get("home_team", "")
            entry["away_odds_api"] = event.get("away_team", "")
            entry["commence_time"] = event.get("commence_time", "")

        if score >= 0.80:
            entry["status"] = "MATCHED"
            entry["failure_reason"] = None
            entry["failure_detail"] = None
            success_count += 1
        elif score >= 0.50:
            entry["status"] = "UNCERTAIN"
            entry["failure_reason"] = "LOW_NAME_SIMILARITY"
            entry["failure_detail"] = (
                f"Score {score:.2f} (seuil 0.80): "
                f"API-Football='{home}' / '{away}' — "
                f"Odds='{event.get('home_team','')}' / '{event.get('away_team','')}'"
                if event else f"Score trop bas: {score:.2f}"
            )
            failed_count += 1
        else:
            entry["status"] = "FAILED"
            entry["failure_reason"] = "NO_MATCH_FOUND"
            entry["failure_detail"] = (
                f"Aucun événement The Odds API ne correspond à '{home}' vs '{away}'. "
                f"Meilleur score: {score:.2f}. "
                f"Meilleure correspondance: '{event.get('home_team','')} vs {event.get('away_team','')}'"
                if event else "Aucun événement dans le cache"
            )
            failed_count += 1

        results.append(entry)

    # Affichage
    total = len(results)
    print(f"  Tentatives: {total} | {GREEN}Matched: {success_count}{RESET} | {RED}Failed: {failed_count}{RESET} | No league: {no_league_count}")

    # Top failures
    failures = [r for r in results if r["status"] in ("FAILED", "UNCERTAIN")]
    if failures:
        print(f"\n  {BOLD}Échecs de mapping:{RESET}")
        for r in failures[:15]:
            reason = r.get("failure_reason", "?")
            detail = (r.get("failure_detail") or "")[:90]
            print(f"  {RED}✗{RESET} {r['match'][:45]}")
            print(f"    Raison: {reason} — {detail}")

    return {
        "total_attempts": total,
        "success": success_count,
        "uncertain": len([r for r in results if r["status"] == "UNCERTAIN"]),
        "failed": failed_count,
        "no_league_coverage": no_league_count,
        "attempts": results,
    }


def section_recommendations(league_coverage: dict, mapping: dict) -> list:
    """Génère des recommandations actionnables."""
    print(f"\n{BOLD}[7/7] Recommandations{RESET}")

    recs = []

    # Clé absente
    if not ODDS_API_KEY:
        recs.append({
            "priority": "CRITICAL",
            "issue": "ODDS_API_KEY manquante",
            "action": "Ajouter ODDS_API_KEY=<ta_clé> dans le fichier .env",
        })

    # Ligues non couvertes
    not_in_mapping = [v for v in league_coverage.get("leagues", [])
                      if v["coverage_status"] == "NOT_IN_MAPPING"]
    if not_in_mapping:
        top_missing = sorted(not_in_mapping, key=lambda x: -x["match_count"])[:5]
        missing_names = [f"{v['league']} ({v['country']})" for v in top_missing]
        recs.append({
            "priority": "HIGH",
            "issue": f"{len(not_in_mapping)} ligues scannées absentes du mapping COUNTRY_TO_SPORT_KEY / LEAGUE_TO_SPORT_KEY",
            "top_missing": missing_names,
            "action": (
                "Ajouter ces pays/ligues dans COUNTRY_TO_SPORT_KEY ou LEAGUE_TO_SPORT_KEY "
                "dans external_odds_provider.py SI elles existent dans The Odds API."
            ),
        })

    # Mapping fuzzy trop bas
    failed_mapping = mapping.get("failed", 0)
    total_mapping = mapping.get("total_attempts", 1)
    if total_mapping > 0 and failed_mapping / total_mapping > 0.5:
        recs.append({
            "priority": "MEDIUM",
            "issue": f"Taux d'échec mapping trop élevé: {failed_mapping}/{total_mapping}",
            "action": (
                "Vérifier les noms d'équipes: API-Football utilise des noms différents de The Odds API. "
                "Envisager un alias mapping (home_team_aliases dict) pour les équipes récurrentes."
            ),
        })

    # Diagnostic fondamental: ligues non couvertes par The Odds API
    if not_in_mapping:
        major_leagues_missing = [
            v for v in not_in_mapping
            if v["country"].lower() in ("kenya", "zimbabwe", "vietnam", "ukraine", "cambodia")
               or any(kw in v["league"].lower() for kw in ("u17", "u19", "u20", "women", "feminin", "youth"))
        ]
        if major_leagues_missing:
            recs.append({
                "priority": "INFO",
                "issue": "Ligues mineures/jeunes/féminines scannées mais non couvertes par The Odds API",
                "detail": (
                    "C'est NORMAL: The Odds API couvre principalement les top leagues européennes + MLS/Brésil/Argentine. "
                    "Kenya Super League, U17-19-20, Women's leagues = pas disponibles dans The Odds API. "
                    "ev_tier=WAITING_FOR_ODDS est correct pour ces ligues — ce n'est PAS un bug."
                ),
                "action": (
                    "Pour ces ligues, statistical_tier reste valide pour l'évaluation du modèle. "
                    "Pour l'EV: considérer d'autres sources d'odds (Betfair, Pinnacle) pour ces marchés de niche."
                ),
            })

    # Quota
    if quota_remaining is not None and quota_remaining < 50:
        recs.append({
            "priority": "HIGH",
            "issue": f"Quota The Odds API critique: {quota_remaining} appels restants",
            "action": "Réduire la fréquence des scans ou upgrader le plan The Odds API",
        })

    for r in recs:
        color = RED if r["priority"] == "CRITICAL" else YELLOW if r["priority"] in ("HIGH", "MEDIUM") else CYAN
        print(f"  {color}[{r['priority']}]{RESET} {r['issue']}")
        if "action" in r:
            print(f"    → {r['action'][:100]}")

    return recs


# ─── Main ─────────────────────────────────────────────────────────────────────
def run_report(flask_url: Optional[str] = DEFAULT_FLASK) -> dict:
    now = datetime.now(timezone.utc)
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  ODDS COVERAGE REPORT — {now.strftime('%Y-%m-%d %H:%M UTC')}{RESET}")
    print(f"{BOLD}  Objectif: comprendre pourquoi aucune cote ne matche{RESET}")
    print(f"{BOLD}{'═'*66}{RESET}")

    report = {
        "generated_at": now.isoformat(),
        "odds_api_base": ODDS_API_BASE,
        "key_present": bool(ODDS_API_KEY),
    }

    # 1. Statut clé
    report["api_status"] = section_api_status()
    if not ODDS_API_KEY:
        report["conclusion"] = "MISSING_KEY — impossible d'analyser sans ODDS_API_KEY"
        _save_report(report)
        return report

    # 2. Catalogue des sports (1 seul appel)
    all_sports = _odds_get("/sports", {"all": "false"}) or []
    report["soccer_sports"] = section_soccer_sports(all_sports)

    # 3. Fetch événements
    events_by_sport, fetch_stats = section_fetch_events()
    report["events_fetch"] = fetch_stats
    report["api_status"]["quota_remaining_after_fetch"] = quota_remaining

    # 4. Bookmakers & marchés
    report["bookmakers_markets"] = section_bookmakers_markets(events_by_sport)

    # 5-7. Nécessite les matchs scannés
    scanned_matches = []
    if flask_url:
        print(f"\n  Récupération des matchs scannés depuis {flask_url}...")
        data = _flask_get(f"{flask_url}/api/matches?limit=500")
        if data and data.get("success"):
            scanned_matches = data.get("matches") or []
            print(f"  {GREEN}✓ {len(scanned_matches)} matchs récupérés depuis Flask{RESET}")
        else:
            print(f"  {YELLOW}⚠ Flask non disponible ou sans matchs — analyse de couverture partielle{RESET}")

    report["scanned_matches_count"] = len(scanned_matches)

    if scanned_matches:
        report["league_coverage"] = section_league_coverage(scanned_matches, events_by_sport)
        report["team_mapping"] = section_team_mapping(scanned_matches, events_by_sport)
    else:
        print(f"\n  {YELLOW}Pas de matchs scannés — ligues/mapping non analysés{RESET}")
        print(f"  Lance le serveur Flask et relance: python odds_coverage_report.py")
        report["league_coverage"] = {}
        report["team_mapping"] = {}

    report["recommendations"] = section_recommendations(
        report.get("league_coverage", {}),
        report.get("team_mapping", {}),
    )

    # Conclusion
    covered = report.get("league_coverage", {}).get("covered_count", 0)
    total_lg = report.get("league_coverage", {}).get("total_unique_leagues", 0)
    mapped = report.get("team_mapping", {}).get("success", 0)
    attempted = report.get("team_mapping", {}).get("total_attempts", 0)

    no_league_count = report.get("team_mapping", {}).get("no_league_coverage", 0)
    coverage_pct = covered / total_lg if total_lg > 0 else 0.0
    no_league_pct = no_league_count / attempted if attempted > 0 else 0.0

    if total_lg == 0:
        report["conclusion"] = "Pas de matchs scannés à analyser."
    elif covered == 0:
        report["conclusion"] = (
            f"COVERAGE_GAP: 0/{total_lg} ligues scannées couvertes par The Odds API. "
            "Les ligues détectées sont hors du périmètre de The Odds API (ligues mineures/africaines/jeunes/off-season). "
            "Ce n'est PAS un bug — c'est un mismatch de périmètre. "
            "ev_tier=WAITING_FOR_ODDS est correct. statistical_tier reste valide."
        )
    elif no_league_pct >= 0.80:
        report["conclusion"] = (
            f"COVERAGE_GAP DOMINANT: {covered}/{total_lg} ligues couvertes ({coverage_pct:.0%}), "
            f"mais {no_league_count}/{attempted} matchs ({no_league_pct:.0%}) sont dans des ligues sans coverage The Odds API. "
            f"Matchés: {mapped}/{attempted - no_league_count} matchs dans les ligues couvertes. "
            "Cause principale: ligues scannées majoritairement hors périmètre The Odds API."
        )
    elif mapped == 0 and attempted > 0:
        report["conclusion"] = (
            f"MAPPING_ISSUE: {covered}/{total_lg} ligues couvertes mais 0/{attempted - no_league_count} équipes matchées. "
            "Les noms d'équipes sont trop différents entre API-Football et The Odds API. "
            "Vérifier le fuzzy matching et envisager un alias dict."
        )
    else:
        report["conclusion"] = (
            f"OK: {covered}/{total_lg} ligues couvertes ({coverage_pct:.0%}), "
            f"{mapped}/{attempted} équipes matchées."
        )

    _save_report(report)
    return report


def _save_report(report: dict):
    path = "odds_coverage_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  {GREEN}✓ Rapport sauvegardé: {path}{RESET}")
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  CONCLUSION{RESET}")
    print(f"  {report.get('conclusion', '?')}")
    print(f"{BOLD}{'═'*66}{RESET}\n")


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Odds Coverage Report — diagnostic The Odds API")
    parser.add_argument("--url",      default=DEFAULT_FLASK, help="URL Flask API (pour les matchs scannés)")
    parser.add_argument("--no-flask", action="store_true",   help="Ne pas contacter Flask (analyse API seulement)")
    args = parser.parse_args()

    flask_url = None if args.no_flask else args.url
    run_report(flask_url=flask_url)
