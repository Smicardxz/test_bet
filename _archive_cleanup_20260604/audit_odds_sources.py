"""
audit_odds_sources.py — Odds Source Coverage Comparison (READ-ONLY)
====================================================================
Compares real odds coverage between:
  - The Odds API   (ODDS_API_KEY)
  - API-Football Odds  (/odds?date=...)

For today's fixtures, measures:
  - How many have odds on each source
  - Coverage % per source
  - Coverage per league and per country
  - Coverage gain = API-Football Odds - The Odds API

Focus regions: Scandinavia, Japan, China, South America, 2nd divisions.

Usage:
    python audit_odds_sources.py
    python audit_odds_sources.py --date 2026-06-03
"""

import os
import sys
import argparse
import time
from collections import defaultdict
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

# ─── Colors ───────────────────────────────────────────────────────────────────
G   = "\033[92m"
Y   = "\033[93m"
R   = "\033[91m"
B   = "\033[94m"
C   = "\033[96m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"


def sec(title: str) -> None:
    print(f"\n{'═' * 72}")
    print(f"  {BLD}{title}{X}")
    print(f"{'─' * 72}")


def bar(n: int, total: int, width: int = 22) -> str:
    filled = int(round(n / max(total, 1) * width))
    return "█" * filled + "░" * (width - filled)


def pct(n: int, d: int) -> str:
    return f"{n/d*100:5.1f}%" if d else "  N/A "


# ─── API-Football: fetch fixtures ─────────────────────────────────────────────

def fetch_fixtures(target_date: str, api_key: str, api_url: str) -> list:
    if not api_key:
        return []
    import requests
    try:
        r = requests.get(
            f"{api_url}/fixtures",
            params={"date": target_date, "timezone": "UTC"},
            headers={"x-apisports-key": api_key},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("response", [])
    except Exception as exc:
        print(f"  {R}API-Football fixtures error: {exc}{X}")
        return []


# ─── API-Football: fetch odds by date ─────────────────────────────────────────

def fetch_apifootball_odds(target_date: str, api_key: str, api_url: str) -> dict:
    """
    Fetch all odds for today via API-Football /odds?date=...
    Returns dict: {fixture_id: {bookmakers: [...], markets: set()}}
    """
    if not api_key:
        return {}
    import requests
    try:
        # Page 1
        params = {"date": target_date, "page": 1}
        r = requests.get(
            f"{api_url}/odds",
            params=params,
            headers={"x-apisports-key": api_key},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("response", [])
        paging = data.get("paging", {})
        total_pages = paging.get("total", 1)

        # Fetch remaining pages (usually 1-3 for a day)
        for page in range(2, min(total_pages + 1, 6)):
            try:
                time.sleep(0.3)
                r2 = requests.get(
                    f"{api_url}/odds",
                    params={"date": target_date, "page": page},
                    headers={"x-apisports-key": api_key},
                    timeout=15,
                )
                r2.raise_for_status()
                results.extend(r2.json().get("response", []))
            except Exception:
                break

        # Parse into fixture_id -> coverage info
        coverage: dict = {}
        for item in results:
            fix_obj = item.get("fixture", {})
            fix_id  = fix_obj.get("id")
            league_obj = item.get("league", {})
            bookmakers = item.get("bookmakers", [])

            if not fix_id:
                continue

            bk_names: set  = set()
            mkt_names: set = set()
            for bk in bookmakers:
                bk_names.add(bk.get("name", "?"))
                for bet in bk.get("bets", []):
                    mkt_names.add(bet.get("name", "?"))

            coverage[str(fix_id)] = {
                "fixture_id":  fix_id,
                "league":      league_obj.get("name", "?"),
                "country":     league_obj.get("country", "?"),
                "bookmakers":  bk_names,
                "markets":     mkt_names,
                "bk_count":    len(bk_names),
            }

        return coverage

    except Exception as exc:
        print(f"  {Y}API-Football /odds error: {exc}{X}")
        print(f"  {D}(Peut nécessiter un plan premium){X}")
        return {}


# ─── The Odds API: fetch events ───────────────────────────────────────────────

def fetch_odds_api_events(odds_key: str, odds_url: str) -> dict:
    """
    Fetch all soccer events from The Odds API.
    Returns dict: {sport_key: [events]}
    """
    if not odds_key:
        return {}

    import requests
    from app.providers.odds.external_odds_provider import SOCCER_SPORT_KEYS

    events_by_sport: dict = {}
    quota_used = 0

    for sk in SOCCER_SPORT_KEYS:
        try:
            r = requests.get(
                f"{odds_url}/sports/{sk}/odds",
                params={"regions": "eu", "markets": "h2h,totals", "oddsFormat": "decimal"},
                headers={"x-api-key": odds_key},
                timeout=8,
            )
            quota_left = r.headers.get("x-requests-remaining")
            quota_used_h = r.headers.get("x-requests-used")
            if r.status_code == 200:
                events = r.json() or []
                if events:
                    events_by_sport[sk] = events
                time.sleep(0.15)
            elif r.status_code == 422:
                pass  # sport not listed today
        except Exception:
            pass

    return events_by_sport


def _normalize(name: str) -> str:
    return (
        name.lower()
        .replace("fc ", "").replace(" fc", "")
        .replace("cf ", "").replace(" cf", "")
        .strip()
    )


def _match_event_to_fixture(home: str, away: str, events: list, window_min: float = 180) -> bool:
    """Quick fuzzy check: is this fixture present in an event list?"""
    from difflib import SequenceMatcher
    h_n = _normalize(home)
    a_n = _normalize(away)
    for ev in events:
        eh = _normalize(ev.get("home_team", ""))
        ea = _normalize(ev.get("away_team", ""))
        s_h = SequenceMatcher(None, h_n, eh).ratio()
        s_a = SequenceMatcher(None, a_n, ea).ratio()
        if (s_h + s_a) / 2 >= 0.60:
            return True
    return False


# ─── Focus regions ─────────────────────────────────────────────────────────────

FOCUS_REGIONS = {
    "Scandinavie":     {"Finland", "Sweden", "Norway", "Denmark", "Iceland"},
    "Japon":           {"Japan"},
    "Chine":           {"China"},
    "Amerique du Sud": {"Brazil", "Argentina", "Colombia", "Chile", "Peru",
                        "Uruguay", "Paraguay", "Ecuador", "Bolivia", "Venezuela"},
    "UK / Irlande":    {"England", "Scotland", "Ireland", "Wales"},
    "Europe de l'Est": {"Poland", "Czech Republic", "Slovakia", "Romania",
                        "Croatia", "Serbia", "Slovenia", "Ukraine", "Hungary"},
}

SECOND_DIV_KEYWORDS = {
    "serie b", "championship", "segunda", "2. bundesliga", "ligue 2",
    "segunda liga", "superettan", "obos-ligaen", "fortuna liga", "liga i",
    "ykkönen", "ykkonen", "j2", "j3", "k2 league", "superettan",
    "mls next pro", "usl championship", "primera nacional",
}


def _is_second_div(league_name: str) -> bool:
    ln = league_name.lower()
    return any(k in ln for k in SECOND_DIV_KEYWORDS)


# ─── Main ──────────────────────────────────────────────────────────────────────

def run(target_date: str) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'═' * 72}")
    print(f"  {BLD}AUDIT ODDS SOURCES — {target_date}  (run: {now_str}){X}")
    print(f"  {D}Sources comparées : The Odds API vs API-Football /odds{X}")
    print(f"{'═' * 72}")

    # ── Keys ──────────────────────────────────────────────────────────────────
    API_KEY  = os.environ.get("API_FOOTBALL_KEY", "")
    API_URL  = os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io").rstrip("/")
    ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
    ODDS_URL = os.environ.get("ODDS_API_URL", "https://api.the-odds-api.com/v4").rstrip("/")

    print(f"\n  API_FOOTBALL_KEY : {G+'OK'+X if API_KEY else R+'MANQUANT'+X}")
    print(f"  ODDS_API_KEY     : {G+'OK'+X if ODDS_KEY else R+'MANQUANT'+X}")

    # ─── STEP 1 — Fetch today's fixtures ───────────────────────────────────────
    sec("STEP 1 — FIXTURES API-FOOTBALL AUJOURD'HUI")
    print(f"\n  {D}Fetching fixtures...{X}")
    fixtures = fetch_fixtures(target_date, API_KEY, API_URL)
    total_fx = len(fixtures)

    if not fixtures:
        print(f"\n  {Y}Aucun fixture trouvé. Vérifier API_FOOTBALL_KEY ou la date.{X}")
        return

    print(f"  {C}{total_fx}{X} fixtures trouvés")

    # Build lookup: fixture_id -> fixture data
    fx_by_id: dict = {}
    for fix in fixtures:
        fid = str(fix.get("fixture", {}).get("id", ""))
        lg  = fix.get("league", {})
        teams = fix.get("teams", {})
        fx_by_id[fid] = {
            "fixture_id": fid,
            "league":     lg.get("name", "?"),
            "country":    lg.get("country", "?"),
            "home":       teams.get("home", {}).get("name", "?"),
            "away":       teams.get("away", {}).get("name", "?"),
            "has_odds_apifb": False,
            "has_odds_oddsapi": False,
            "apifb_bk_count":  0,
            "apifb_markets":   set(),
        }

    # ─── STEP 2 — API-Football Odds ────────────────────────────────────────────
    sec("STEP 2 — API-FOOTBALL /odds COVERAGE")
    print(f"\n  {D}Fetching /odds?date={target_date} (peut prendre 10-20s selon plan)...{X}")

    apifb_odds = fetch_apifootball_odds(target_date, API_KEY, API_URL)
    n_apifb = len(apifb_odds)

    if n_apifb == 0:
        print(f"  {Y}Aucun odds API-Football trouvé.{X}")
        print(f"  {D}Causes possibles :{X}")
        print(f"    - Plan gratuit (endpoint /odds limité ou non disponible)")
        print(f"    - Pas d'odds publiés pour {target_date}")
        print(f"    - Cache (les odds ne sont pas toujours dispo le jour J)")
        apifb_available = False
    else:
        apifb_available = True
        print(f"  {G}{n_apifb}{X} fixtures avec odds API-Football")

        # Mark fixtures
        for fid, od in apifb_odds.items():
            if fid in fx_by_id:
                fx_by_id[fid]["has_odds_apifb"]  = True
                fx_by_id[fid]["apifb_bk_count"]  = od["bk_count"]
                fx_by_id[fid]["apifb_markets"]    = od["markets"]

        # Bookmakers found
        all_bks: set = set()
        all_mkts: set = set()
        for od in apifb_odds.values():
            all_bks  |= od["bookmakers"]
            all_mkts |= od["markets"]

        print(f"  Bookmakers vus : {C}{len(all_bks)}{X}  — {', '.join(sorted(all_bks)[:8])}")
        print(f"  Marchés vus    : {C}{len(all_mkts)}{X}  — {', '.join(sorted(all_mkts)[:6])}")

    # ─── STEP 3 — The Odds API ─────────────────────────────────────────────────
    sec("STEP 3 — THE ODDS API COVERAGE")

    if not ODDS_KEY:
        print(f"\n  {Y}ODDS_API_KEY absent — The Odds API ignoré.{X}")
        oddsapi_available = False
        events_by_sport: dict = {}
    else:
        print(f"\n  {D}Fetching The Odds API ({len(fixtures)} fixtures, sport keys ciblés)...{X}")
        from app.providers.odds.external_odds_provider import TheOddsAPIProvider, SOCCER_SPORT_KEYS

        # Resolve sport keys needed for today's fixtures
        needed_sks: set = set()
        for fid, fx in fx_by_id.items():
            sk = TheOddsAPIProvider.resolve_sport_key(fx["league"], fx["country"])
            if sk:
                needed_sks.add(sk)

        events_by_sport = fetch_odds_api_events(ODDS_KEY, ODDS_URL)
        oddsapi_available = bool(events_by_sport)

        total_oddsapi_events = sum(len(v) for v in events_by_sport.values())
        print(f"\n  {C}{total_oddsapi_events}{X} events The Odds API  "
              f"({len(events_by_sport)} sport keys)")

        # Per sport key
        print(f"\n  {'Sport Key':<45}  {'Events':>6}  {'Targeted':>8}")
        print(f"  {'-'*45}  {'-'*6}  {'-'*8}")
        for sk in sorted(events_by_sport.keys()):
            n_ev = len(events_by_sport[sk])
            targeted = sk in needed_sks
            tcol = G if targeted else D
            print(f"  {tcol}{sk:<45}{X}  {C}{n_ev:>6}{X}  "
                  f"{'YES' if targeted else 'no':>8}")

        # Cross-match per fixture (fuzzy)
        all_events_flat = [ev for evs in events_by_sport.values() for ev in evs]
        for fid, fx in fx_by_id.items():
            # Rough check: is the league sport_key present in events_by_sport?
            sk = TheOddsAPIProvider.resolve_sport_key(fx["league"], fx["country"])
            if sk and sk in events_by_sport:
                # Try fuzzy match on team names
                if _match_event_to_fixture(fx["home"], fx["away"], events_by_sport[sk]):
                    fx["has_odds_oddsapi"] = True

    # ─── STEP 4 — Comparison matrix ────────────────────────────────────────────
    sec("STEP 4 — COMPARISON MATRIX")

    all_fx = list(fx_by_id.values())
    n_both  = sum(1 for f in all_fx if f["has_odds_apifb"] and f["has_odds_oddsapi"])
    n_apifb_only = sum(1 for f in all_fx if f["has_odds_apifb"] and not f["has_odds_oddsapi"])
    n_oddsapi_only = sum(1 for f in all_fx if f["has_odds_oddsapi"] and not f["has_odds_apifb"])
    n_neither = sum(1 for f in all_fx if not f["has_odds_apifb"] and not f["has_odds_oddsapi"])
    n_any = sum(1 for f in all_fx if f["has_odds_apifb"] or f["has_odds_oddsapi"])

    print(f"\n  {'Source':<35}  {'Fixtures avec odds':>18}  {'Coverage':>8}")
    print(f"  {'-'*35}  {'-'*18}  {'-'*8}")
    print(f"  {G}The Odds API{X:<31}  "
          f"{sum(1 for f in all_fx if f['has_odds_oddsapi']):>18}  "
          f"{pct(sum(1 for f in all_fx if f['has_odds_oddsapi']), total_fx):>8}")
    print(f"  {B}API-Football /odds{X:<28}  "
          f"{n_apifb:>18}  "
          f"{pct(n_apifb, total_fx):>8}")
    print(f"  {C}Union (au moins 1 source){X:<22}  "
          f"{n_any:>18}  "
          f"{pct(n_any, total_fx):>8}")
    print(f"  {D}Aucune source (no odds){X:<28}  "
          f"{n_neither:>18}  "
          f"{pct(n_neither, total_fx):>8}")

    n_oddsapi_total = sum(1 for f in all_fx if f["has_odds_oddsapi"])
    coverage_gain = n_apifb - n_oddsapi_total
    gain_col = G if coverage_gain > 0 else (Y if coverage_gain == 0 else R)
    print(f"\n  {BLD}Coverage Gain (API-FB - OddsAPI) = {gain_col}{coverage_gain:+d} fixtures{X}")

    if not apifb_available:
        print(f"\n  {Y}Note: API-Football /odds indisponible — gain non calculable.{X}")
        print(f"  {Y}Seul The Odds API est comparé.{X}")

    # ─── STEP 5 — Per country ──────────────────────────────────────────────────
    sec("STEP 5 — COVERAGE PAR PAYS")

    country_stats: dict = defaultdict(lambda: {
        "total": 0, "odds_apifb": 0, "odds_oddsapi": 0, "leagues": set()
    })
    for fx in all_fx:
        c = fx["country"]
        country_stats[c]["total"]        += 1
        country_stats[c]["leagues"].add(fx["league"])
        if fx["has_odds_apifb"]:
            country_stats[c]["odds_apifb"]   += 1
        if fx["has_odds_oddsapi"]:
            country_stats[c]["odds_oddsapi"] += 1

    # Sort by total desc
    country_sorted = sorted(country_stats.items(), key=lambda x: -x[1]["total"])

    print(f"\n  {'Country':<22}  {'Fix':>3}  {'TheOdds%':>8}  {'APIFB%':>7}  {'Gain':>5}  Ligues")
    print(f"  {'-'*22}  {'-'*3}  {'-'*8}  {'-'*7}  {'-'*5}  {'-'*5}")
    for country, s in country_sorted[:30]:
        tot = s["total"]
        p_odds = s["odds_oddsapi"] / tot * 100
        p_apifb = s["odds_apifb"] / tot * 100
        gain = s["odds_apifb"] - s["odds_oddsapi"]
        gcol = G if gain > 0 else (D if gain == 0 else R)
        bcolor = G if p_odds >= 50 else (Y if p_odds >= 20 else R)
        print(f"  {country:<22}  {tot:>3}  "
              f"{bcolor}{p_odds:>7.0f}%{X}  "
              f"{p_apifb:>6.0f}%  "
              f"{gcol}{gain:>+5d}{X}  "
              f"{D}{len(s['leagues'])}{X}")

    # ─── STEP 6 — Per league (top leagues with no odds) ────────────────────────
    sec("STEP 6 — LIGUES SANS ODDS (les deux sources)")

    no_odds: list = []
    for fx in all_fx:
        if not fx["has_odds_apifb"] and not fx["has_odds_oddsapi"]:
            no_odds.append(fx)

    league_no_odds: dict = defaultdict(lambda: {"country": "", "count": 0})
    for fx in no_odds:
        lg = fx["league"]
        league_no_odds[lg]["country"] = fx["country"]
        league_no_odds[lg]["count"] += 1

    lo_sorted = sorted(league_no_odds.items(), key=lambda x: -x[1]["count"])
    print(f"\n  {n_neither} fixtures sans aucun odds ({pct(n_neither, total_fx)})\n")
    print(f"  {'League':<40}  {'Country':<18}  {'Fixtures':>8}")
    print(f"  {'-'*40}  {'-'*18}  {'-'*8}")
    for lg, d in lo_sorted[:20]:
        print(f"  {R}{lg:<40}{X}  {d['country']:<18}  {d['count']:>8}")

    # ─── STEP 7 — Focus regions ────────────────────────────────────────────────
    sec("STEP 7 — FOCUS REGIONS")

    for region, countries in FOCUS_REGIONS.items():
        region_fx = [fx for fx in all_fx if fx["country"] in countries]
        if not region_fx:
            continue
        tot = len(region_fx)
        n_oa = sum(1 for f in region_fx if f["has_odds_oddsapi"])
        n_af = sum(1 for f in region_fx if f["has_odds_apifb"])
        n_any_r = sum(1 for f in region_fx if f["has_odds_oddsapi"] or f["has_odds_apifb"])
        best = "OddsAPI" if n_oa >= n_af else ("APIFB" if n_af > 0 else "None")

        print(f"\n  {B}{region}{X} ({tot} fixtures)")
        print(f"    The Odds API     : {G if n_oa>0 else R}{n_oa}/{tot}{X}  ({pct(n_oa,tot)})")
        print(f"    API-Football     : {G if n_af>0 else R}{n_af}/{tot}{X}  ({pct(n_af,tot)})")
        print(f"    Union            : {C}{n_any_r}/{tot}{X}  ({pct(n_any_r,tot)})")

        if region_fx:
            # Show leagues in this region
            lg_set = sorted({f["league"] for f in region_fx})
            for lg in lg_set[:6]:
                lg_fx = [f for f in region_fx if f["league"] == lg]
                n_lg_oa = sum(1 for f in lg_fx if f["has_odds_oddsapi"])
                n_lg_af = sum(1 for f in lg_fx if f["has_odds_apifb"])
                oa_col = G if n_lg_oa > 0 else R
                af_col = G if n_lg_af > 0 else R
                print(f"      {D}{lg:<35}{X}  "
                      f"OddsAPI:{oa_col}{n_lg_oa}{X}  APIFB:{af_col}{n_lg_af}{X}")

    # ─── STEP 8 — Second divisions ─────────────────────────────────────────────
    sec("STEP 8 — DIVISIONS SECONDAIRES")

    second_div = [fx for fx in all_fx if _is_second_div(fx["league"])]
    if not second_div:
        print(f"\n  {D}Aucune division secondaire détectée aujourd'hui.{X}")
    else:
        tot_sd = len(second_div)
        n_sd_oa = sum(1 for f in second_div if f["has_odds_oddsapi"])
        n_sd_af = sum(1 for f in second_div if f["has_odds_apifb"])
        print(f"\n  {tot_sd} fixtures en 2ème division")
        print(f"    The Odds API : {G if n_sd_oa>0 else R}{n_sd_oa}/{tot_sd}{X}  ({pct(n_sd_oa,tot_sd)})")
        print(f"    API-Football : {G if n_sd_af>0 else R}{n_sd_af}/{tot_sd}{X}  ({pct(n_sd_af,tot_sd)})")
        print()
        print(f"  {'League':<38}  {'Country':<16}  {'OddsAPI':>7}  {'APIFB':>5}")
        print(f"  {'-'*38}  {'-'*16}  {'-'*7}  {'-'*5}")
        seen = {}
        for fx in second_div:
            lg = fx["league"]
            if lg not in seen:
                seen[lg] = {"country": fx["country"], "oa": 0, "af": 0, "n": 0}
            seen[lg]["n"]  += 1
            seen[lg]["oa"] += int(fx["has_odds_oddsapi"])
            seen[lg]["af"] += int(fx["has_odds_apifb"])
        for lg, d in sorted(seen.items(), key=lambda x: -x[1]["n"])[:15]:
            oa_col = G if d["oa"] > 0 else R
            af_col = G if d["af"] > 0 else R
            print(f"  {lg:<38}  {d['country']:<16}  "
                  f"{oa_col}{d['oa']:>4}/{d['n']}{X}  "
                  f"{af_col}{d['af']:>2}/{d['n']}{X}")

    # ─── STEP 9 — Recommendation ────────────────────────────────────────────────
    sec("STEP 9 — RECOMMANDATION SOURCE")

    print()
    total_oa = sum(1 for f in all_fx if f["has_odds_oddsapi"])
    total_af_c = n_apifb

    if not apifb_available and not oddsapi_available:
        print(f"  {R}Aucune source d'odds fonctionnelle aujourd'hui.{X}")
        print(f"  {Y}-> NO_EV_MARKET_AVAILABLE_TODAY{X}")
    elif not apifb_available:
        print(f"  Source recommandée     : {G}The Odds API{X} (seule disponible)")
        print(f"  Coverage               : {pct(total_oa, total_fx)}")
    elif not oddsapi_available:
        print(f"  Source recommandée     : {G}API-Football /odds{X} (seule disponible)")
        print(f"  Coverage               : {pct(total_af_c, total_fx)}")
    else:
        winner = "API-Football" if total_af_c >= total_oa else "The Odds API"
        loser  = "The Odds API" if winner == "API-Football" else "API-Football"
        print(f"  Source la plus large   : {G}{winner}{X}")
        print(f"  Coverage winner        : {G}{pct(max(total_af_c,total_oa), total_fx)}{X}")
        print(f"  Coverage {loser:<14}: {Y}{pct(min(total_af_c,total_oa), total_fx)}{X}")
        print(f"  Coverage Gain          : {G if coverage_gain>0 else Y}{coverage_gain:+d} fixtures{X}")
        print(f"\n  {D}Stratégie optimale : utiliser les DEUX en union -> {pct(n_any, total_fx)} coverage{X}")

    print(f"\n{'═' * 72}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit odds source coverage")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Date ISO (default: today)")
    args = parser.parse_args()
    run(args.date)
