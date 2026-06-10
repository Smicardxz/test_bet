"""
audit_today_market_availability.py — Market Availability Diagnostic (READ-ONLY)
=================================================================================
Answers concretely:
  1. What fixtures exist today in API-Football?
  2. Which ones are covered by The Odds API?
  3. Which ones are BETTABLE / LIMITED / RESEARCH_ONLY?
  4. Is today a good EV day, or are we just tracking?

Usage:
    python audit_today_market_availability.py
    python audit_today_market_availability.py --date 2026-06-03
"""

import os
import sys
import argparse
from collections import defaultdict
from datetime import datetime, timezone, date

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

# ─── Console colors ────────────────────────────────────────────────────────────
G   = "\033[92m"
Y   = "\033[93m"
R   = "\033[91m"
B   = "\033[94m"
C   = "\033[96m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"


def sec(title: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {BLD}{title}{X}")
    print(f"{'─' * 70}")


def bar(n: int, total: int, width: int = 28) -> str:
    filled = int(round(n / max(total, 1) * width))
    return "█" * filled + "░" * (width - filled)


def pct(n: int, d: int) -> str:
    return f"{n/d*100:5.1f}%" if d else "  N/A "


# ─── Competition categorizer ───────────────────────────────────────────────────

_INTL_KEYWORDS = {
    "world cup", "euro", "nations league", "copa america", "africa cup",
    "afcon", "asian cup", "concacaf", "qualifying", "olympics", "confederation"
}
_FRIENDLY_KEYWORDS = {"friendly", "amical", "test match", "club friendly"}
_YOUTH_KEYWORDS = {"u17", "u18", "u19", "u20", "u21", "u23", "youth", "junior", "sub-"}
_WOMEN_KEYWORDS = {"women", "femenin", "feminin", "frauen", "donne", "vrouwen", "women's"}
_OBSCURE_COUNTRIES = {
    "Kenya", "Ethiopia", "Mali", "Sudan", "Uganda", "Tanzania", "Rwanda",
    "Zambia", "Zimbabwe", "Mozambique", "Malawi", "Ghana", "Nigeria",
    "Senegal", "Cameroon", "Ivory Coast", "Bhutan", "Kyrgyzstan",
    "Mongolia", "Maldives", "Laos", "Myanmar", "Cambodia", "Papua New Guinea",
    "Guatemala", "Nicaragua", "El Salvador", "Honduras", "Panama", "Haiti",
    "Jamaica", "Trinidad",
}


def categorize_match(league: str, country: str) -> str:
    """Return one of: INTERNATIONAL, FRIENDLY, YOUTH, WOMEN, MINOR_BETTABLE, OBSCURE"""
    lg = league.lower()
    c  = country
    if any(k in lg for k in _INTL_KEYWORDS):
        return "INTERNATIONAL"
    if any(k in lg for k in _FRIENDLY_KEYWORDS):
        return "FRIENDLY"
    if any(k in lg for k in _WOMEN_KEYWORDS):
        return "WOMEN"
    if any(k in lg for k in _YOUTH_KEYWORDS):
        return "YOUTH"
    if c in _OBSCURE_COUNTRIES:
        return "OBSCURE"
    return "MINOR_BETTABLE"


# ─── Market access estimator via LeagueTargetingService ───────────────────────

def _get_targeting_svc():
    from app.services.targeting.league_targeting_service import LeagueTargetingService
    return LeagueTargetingService()


def _coverage_label(country: str, league: str, svc) -> tuple:
    """Returns (market_access, target_score, coverage_priority)"""
    try:
        profile = svc.analyze_competition(league, country)
        prio = profile.coverage_priority
        score = profile.target_score
        if prio == "A":
            access = "BETTABLE"
        elif prio == "B":
            access = "LIMITED"
        else:
            access = "RESEARCH_ONLY"
        return access, score, prio
    except Exception:
        return "RESEARCH_ONLY", 0.0, "C"


# ─── Odds API sport key resolver ───────────────────────────────────────────────

def _resolve_sport_key(league: str, country: str) -> str:
    try:
        from app.providers.odds.external_odds_provider import TheOddsAPIProvider
        return TheOddsAPIProvider.resolve_sport_key(league, country) or ""
    except Exception:
        return ""


# ─── API-Football fixtures for today ──────────────────────────────────────────

def _fetch_today_fixtures(target_date: str) -> list:
    """Fetch today's fixtures from API-Football. Returns list of dicts."""
    api_key = os.environ.get("API_FOOTBALL_KEY", "")
    api_url = os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io").rstrip("/")
    if not api_key:
        print(f"  {Y}API_FOOTBALL_KEY absent — impossible de récupérer les fixtures.{X}")
        return []
    import requests
    try:
        resp = requests.get(
            f"{api_url}/fixtures",
            params={"date": target_date, "timezone": "UTC"},
            headers={"x-apisports-key": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", [])
    except Exception as exc:
        print(f"  {R}API-Football error: {exc}{X}")
        return []


# ─── Odds API events count ─────────────────────────────────────────────────────

def _fetch_odds_api_events() -> dict:
    """Fetch event counts from The Odds API per sport key."""
    odds_key = os.environ.get("ODDS_API_KEY", "")
    odds_url  = os.environ.get("ODDS_API_URL", "https://api.the-odds-api.com/v4").rstrip("/")
    if not odds_key:
        return {"status": "MISSING_KEY", "events_by_sport": {}, "total": 0, "quota_remaining": None}

    from app.providers.odds.external_odds_provider import SOCCER_SPORT_KEYS
    import requests

    events_by_sport: dict = {}
    quota_remaining = None
    total = 0

    for sk in SOCCER_SPORT_KEYS:
        try:
            r = requests.get(
                f"{odds_url}/sports/{sk}/odds",
                params={"regions": "eu", "markets": "totals", "oddsFormat": "decimal"},
                headers={"x-api-key": odds_key},
                timeout=8,
            )
            qr = r.headers.get("x-requests-remaining")
            if qr:
                quota_remaining = int(qr)
            if r.status_code == 200:
                events = r.json() or []
                n = len(events)
                if n > 0:
                    events_by_sport[sk] = {"events": events, "count": n}
                    total += n
            elif r.status_code == 422:
                pass  # sport not available today
            else:
                pass
        except Exception:
            pass

    return {
        "status": "OK" if events_by_sport else "NO_EVENTS",
        "events_by_sport": events_by_sport,
        "total": total,
        "quota_remaining": quota_remaining,
    }


# ─── Verdict ───────────────────────────────────────────────────────────────────

def _verdict(total_fix: int, bettable: int, odds_matched: int, odds_total: int) -> str:
    if total_fix == 0:
        return "NO_EV_DAY_BUT_TRACKING_OK"
    if odds_matched == 0 and odds_total == 0:
        return "NO_EV_DAY_BUT_TRACKING_OK"
    odds_pct = odds_matched / max(bettable, 1) * 100
    if bettable >= 10 and odds_matched >= 5 and odds_pct >= 20:
        return "GOOD_EV_DAY"
    if total_fix < 20:
        return "LOW_MATCH_VOLUME"
    if bettable < 5:
        return "MOSTLY_RESEARCH_ONLY"
    if odds_matched == 0:
        return "LOW_ODDS_COVERAGE"
    return "LOW_ODDS_COVERAGE"


# ─── Main ──────────────────────────────────────────────────────────────────────

def run(target_date: str) -> dict:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'═' * 70}")
    print(f"  {BLD}AUDIT MARKET AVAILABILITY — {target_date}  (run: {now_str}){X}")
    print(f"{'═' * 70}")

    # ── Load services ──────────────────────────────────────────────────────────
    print(f"\n  {D}Chargement des services...{X}")
    try:
        svc = _get_targeting_svc()
        print(f"  {G}✓ LeagueTargetingService OK{X}")
    except Exception as exc:
        print(f"  {R}✗ LeagueTargetingService: {exc}{X}")
        svc = None

    # ── API-Football fixtures ──────────────────────────────────────────────────
    sec("PHASE 1 — FIXTURES API-FOOTBALL AUJOURD'HUI")

    raw_fixtures = _fetch_today_fixtures(target_date)
    total_api = len(raw_fixtures)

    if total_api == 0:
        print(f"\n  {Y}Aucun fixture trouvé pour {target_date}.{X}")
        print(f"  Causes : API_FOOTBALL_KEY absent / jour sans matchs / date future.")
    else:
        print(f"\n  {C}{total_api}{X} fixtures trouvés dans API-Football pour {target_date}")

    # ── Categorize and score each fixture ─────────────────────────────────────
    categories: dict = defaultdict(list)
    access_counts: dict = defaultdict(int)
    by_sport_key: dict = defaultdict(list)

    for fix in raw_fixtures:
        league_obj = fix.get("league", {})
        league_name = league_obj.get("name", "?")
        country     = league_obj.get("country", "?")
        teams       = fix.get("teams", {})
        home        = teams.get("home", {}).get("name", "?")
        away        = teams.get("away", {}).get("name", "?")
        status_obj  = fix.get("fixture", {}).get("status", {})
        status      = status_obj.get("short", "NS") if isinstance(status_obj, dict) else "NS"

        category = categorize_match(league_name, country)

        if svc:
            access, score, prio = _coverage_label(country, league_name, svc)
        else:
            access, score, prio = "RESEARCH_ONLY", 0.0, "C"

        is_friendly = category == "FRIENDLY"
        risk_tag = "FRIENDLY_VOLATILITY" if is_friendly else None

        sport_key = _resolve_sport_key(league_name, country)

        entry = {
            "home": home, "away": away,
            "league": league_name, "country": country,
            "category": category, "status": status,
            "market_access": access, "target_score": score,
            "coverage_priority": prio, "risk_tag": risk_tag,
            "sport_key": sport_key,
        }
        categories[category].append(entry)
        access_counts[access] += 1
        if sport_key:
            by_sport_key[sport_key].append(entry)

    # ── Category breakdown ─────────────────────────────────────────────────────
    cat_colors = {
        "MINOR_BETTABLE":  G,
        "FRIENDLY":        Y,
        "INTERNATIONAL":   B,
        "YOUTH":           C,
        "WOMEN":           C,
        "OBSCURE":         R,
    }
    cat_labels = {
        "INTERNATIONAL":  "A. International / Mondial",
        "FRIENDLY":       "B. Amicaux",
        "MINOR_BETTABLE": "C. Ligues nationales mineures",
        "YOUTH":          "E. Youth / U19-U21",
        "WOMEN":          "F. Femmes",
        "OBSCURE":        "G. Ultra obscure / research only",
    }

    print(f"\n  {'Catégorie':<35} {'N':>4}  {'%':>6}  Bar")
    print(f"  {'-'*35} {'-'*4}  {'-'*6}  {'-'*28}")
    for cat, label in cat_labels.items():
        cnt = len(categories.get(cat, []))
        col = cat_colors.get(cat, X)
        print(f"  {col}{label:<35}{X} {cnt:>4}  {pct(cnt, max(total_api,1))}  {col}{bar(cnt, max(total_api,1))}{X}")

    # ── Market access distribution ─────────────────────────────────────────────
    print(f"\n  {'Market Access':<20} {'N':>4}  {'%':>6}  Bar")
    print(f"  {'-'*20} {'-'*4}  {'-'*6}  {'-'*28}")
    for acc, col in [("BETTABLE", G), ("LIMITED", Y), ("RESEARCH_ONLY", R)]:
        cnt = access_counts.get(acc, 0)
        print(f"  {col}{acc:<20}{X} {cnt:>4}  {pct(cnt, max(total_api,1))}  {col}{bar(cnt, max(total_api,1))}{X}")

    # ── Odds API events ────────────────────────────────────────────────────────
    sec("PHASE 2 — ODDS API COVERAGE")

    print(f"\n  {D}Fetching The Odds API events (peut prendre quelques secondes)...{X}")
    odds_data = _fetch_odds_api_events()
    total_odds_events = odds_data["total"]
    quota = odds_data.get("quota_remaining")

    if odds_data["status"] == "MISSING_KEY":
        print(f"\n  {Y}ODDS_API_KEY absent — couverture inconnue.{X}")
        odds_matched = 0
    else:
        print(f"\n  {C}{total_odds_events}{X} events The Odds API (matchs avec odds disponibles)")
        if quota is not None:
            col = G if quota > 50 else (Y if quota > 10 else R)
            print(f"  Quota restant       : {col}{quota}{X}")
        print(f"\n  Par sport_key :")
        for sk, d in sorted(odds_data["events_by_sport"].items(), key=lambda x: -x[1]["count"])[:15]:
            fc = len(by_sport_key.get(sk, []))
            print(f"    {D}{sk:<45}{X}  {C}{d['count']:>3}{X} odds events  /{fc} fixtures ciblés")

    # ── Cross-match: fixtures vs odds ──────────────────────────────────────────
    sec("PHASE 3 — CROSS-MATCHING FIXTURES ↔ ODDS")

    # Count fixtures that have a sport_key with at least 1 odds event
    matched_fixtures = []
    unmatched_fixtures = []
    for fix in [f for cat in categories.values() for f in cat]:
        sk = fix["sport_key"]
        has_odds_sport = sk and sk in odds_data.get("events_by_sport", {})
        fix["has_odds_sport"] = has_odds_sport
        if has_odds_sport:
            matched_fixtures.append(fix)
        else:
            unmatched_fixtures.append(fix)

    odds_matched = len(matched_fixtures)
    bettable_count = access_counts.get("BETTABLE", 0)
    limited_count  = access_counts.get("LIMITED", 0)
    research_count = access_counts.get("RESEARCH_ONLY", 0)

    print(f"\n  Total fixtures aujourd'hui    : {C}{total_api}{X}")
    print(f"  Fixtures avec sport_key Odds  : {G if odds_matched > 0 else R}{odds_matched}{X}  ({pct(odds_matched, max(total_api,1))})")
    print(f"  Fixtures BETTABLE (scoring)   : {G}{bettable_count}{X}")
    print(f"  Fixtures LIMITED              : {Y}{limited_count}{X}")
    print(f"  Fixtures RESEARCH_ONLY        : {R}{research_count}{X}")
    print(f"  Odds API events total         : {C}{total_odds_events}{X}")

    # ── Top BETTABLE fixtures ──────────────────────────────────────────────────
    if matched_fixtures:
        top_bet = [f for f in matched_fixtures if f["market_access"] == "BETTABLE"]
        top_bet.sort(key=lambda x: -x["target_score"])
        if top_bet:
            print(f"\n  {G}Top BETTABLE avec odds :{X}")
            print(f"  {'Country':<16}  {'League':<30}  {'Score':>5}  {'Category'}")
            print(f"  {'-'*16}  {'-'*30}  {'-'*5}  {'-'*16}")
            for f in top_bet[:15]:
                print(f"  {G}{f['country']:<16}{X}  {f['league']:<30}  {f['target_score']:>5.1f}  {f['category']}")

    # ── Friendlies ─────────────────────────────────────────────────────────────
    friendlies = categories.get("FRIENDLY", [])
    if friendlies:
        print(f"\n  {Y}Amicaux détectés ({len(friendlies)}) — tag FRIENDLY_VOLATILITY :{X}")
        for f in friendlies[:8]:
            print(f"    {D}{f['country']:<16}{X} {f['league']}")

    # ── Phase 4: Calendar reality check ───────────────────────────────────────
    sec("PHASE 4 — CALENDAR REALITY CHECK")

    verdict = _verdict(total_api, bettable_count, odds_matched, total_odds_events)

    verdict_col = {
        "GOOD_EV_DAY":              G,
        "LOW_MATCH_VOLUME":         Y,
        "LOW_ODDS_COVERAGE":        Y,
        "MOSTLY_RESEARCH_ONLY":     R,
        "NO_EV_DAY_BUT_TRACKING_OK": R,
    }
    vcol = verdict_col.get(verdict, X)

    print(f"\n  TODAY_STATUS = {vcol}{BLD}{verdict}{X}\n")

    checks = [
        (total_api >= 30,     f"Assez de matchs aujourd'hui ?",        f"{total_api} fixtures",          "≥ 30"),
        (bettable_count >= 10, f"Assez de matchs bettables ?",          f"{bettable_count} BETTABLE",     "≥ 10"),
        (odds_matched >= 5,   f"Assez d'odds disponibles ?",           f"{odds_matched} matchés",        "≥ 5"),
        (total_odds_events >= 10, f"Volume odds API suffisant ?",       f"{total_odds_events} events",    "≥ 10"),
    ]

    for ok, question, actual, target in checks:
        sym = f"{G}✓{X}" if ok else f"{R}✗{X}"
        col = G if ok else R
        print(f"  {sym}  {question:<40} {col}{actual}{X}  (cible {target})")

    print(f"\n  Diagnostic :")
    if verdict == "GOOD_EV_DAY":
        print(f"  {G}→ Bonne journée. Lancer python start.py pour un run sérieux.{X}")
    elif verdict == "LOW_MATCH_VOLUME":
        print(f"  {Y}→ Peu de matchs aujourd'hui. Tracking OK mais EV limité.{X}")
        print(f"  {Y}   Revenir demain ou attendre le prochain cycle (midweek/weekend).{X}")
    elif verdict == "LOW_ODDS_COVERAGE":
        if odds_data["status"] == "MISSING_KEY":
            print(f"  {Y}→ ODDS_API_KEY manquant — ajouter dans .env pour activer l'EV réel.{X}")
        else:
            print(f"  {Y}→ Odds absents sur les marchés ciblés aujourd'hui.{X}")
            print(f"  {Y}   Pas de problème modèle — c'est le calendrier.{X}")
    elif verdict == "MOSTLY_RESEARCH_ONLY":
        print(f"  {R}→ Majorité de ligues sans couverture bookmaker.{X}")
        print(f"  {R}   LeagueTargetingService doit être recalibré (déjà en cours).{X}")
    else:
        print(f"  {R}→ Journée tracking uniquement. Aucun marché bettable disponible.{X}")
        print(f"  {R}   Ce n'est PAS un problème de modèle — c'est le calendrier du jour.{X}")
        print(f"  {Y}   Verdict: NO_EV_MARKET_AVAILABLE_TODAY{X}")

    # ── Return summary dict ────────────────────────────────────────────────────
    result = {
        "date":             target_date,
        "total_fixtures":   total_api,
        "bettable":         bettable_count,
        "limited":          limited_count,
        "research_only":    research_count,
        "odds_api_events":  total_odds_events,
        "odds_matched":     odds_matched,
        "verdict":          verdict,
    }

    print(f"\n{'═' * 70}\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit market availability for a given date")
    parser.add_argument("--date", default=date.today().isoformat(), help="Date ISO (default: today)")
    args = parser.parse_args()
    run(args.date)
