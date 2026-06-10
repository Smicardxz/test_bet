# PERFORMANCE_REPORT SAFE MODE CONSISTENCY AUDIT

**Date:** 2026-06-03
**Issue:** Report contradicts itself when SAFE_SELECTION_MODE=true

---

## Phase 1: Dataset Trace

### SAFE_MODE Banner (lines 177-200)
```python
q = (
    repo._client.table("predictions")
    .select("selection_mode", count="exact")
    .in_("status", ["WON", "LOST", "VOID"])
)
if _since:
    q = q.gte("created_at", cutoff)  # or prediction_date
rows = q.execute().data or []
live_safe = sum(1 for r in rows if r.get("selection_mode") == "LIVE_SAFE")
research = sum(1 for r in rows if r.get("selection_mode") == "RESEARCH")
total = len(rows)
```

**Query:** ALL settled predictions (NO selection_mode filter)
**Result:** LIVE_SAFE=2, RESEARCH=69, Total=71

---

### get_performance_summary (lines 202-205)
```python
if _since:
    summary = repo.get_performance_summary(since_date=_since)
else:
    summary = repo.get_performance_summary(days=days)
```

**Calls:** `repo.get_performance_summary()` → `_fetch_settled()`

**_fetch_settled in supabase_repository.py (lines 688-691):**
```python
safe_mode = os.environ.get("SAFE_SELECTION_MODE", "").lower() in ("1", "true", "yes")
if safe_mode:
    q = q.eq("selection_mode", "LIVE_SAFE")
```

**Query:** Filtered to LIVE_SAFE only when SAFE_MODE enabled
**Result:** Returns only LIVE_SAFE predictions

---

### Phase 1 Odds Audit (lines 229-239)
```python
wins     = int(summary.get("total_wins",   0))
losses   = int(summary.get("total_losses", 0))
void_    = int(summary.get("total_void",   0))
total_wl = wins + losses
```

**Source:** `summary` from `get_performance_summary` (LIVE_SAFE filtered)
**Result:** Shows only LIVE_SAFE counts

---

### Phase 6 Source Breakdown (lines 242-254)
```python
src_breakdown = _get_odds_source_breakdown(
    repo, days=days, since_date=_since if _since else None
)
```

**_get_odds_source_breakdown (lines 62-80):**
```python
q = repo._client.table("predictions").select(
    "odds_source,status,bookmaker_odd"
)
if since_date:
    q = q.gte("prediction_date", since_date)
else:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    q = q.gte("prediction_date", cutoff)
rows = (q.limit(5000).execute()).data or []
```

**Query:** ALL predictions (NO selection_mode filter)
**Result:** Shows ALL predictions breakdown

---

## Phase 2: Dataset Mixing Confirmed

| Section | Dataset | Filtered? |
|---------|---------|-----------|
| SAFE_MODE banner | ALL settled | NO |
| get_performance_summary | LIVE_SAFE only | YES |
| Phase 1 (Odds Audit) | LIVE_SAFE only | YES |
| Phase 2 (ROI) | LIVE_SAFE only | YES |
| Phase 6 (Source Breakdown) | ALL predictions | NO |

**Conclusion:** Datasets are mixed. Banner and Phase 6 use ALL, while Phases 1-2 use LIVE_SAFE only.

---

## Phase 3: Root Cause

**Location:** `app/database/supabase_repository.py` lines 688-691

```python
# Apply SAFE_SELECTION_MODE filter if enabled
safe_mode = os.environ.get("SAFE_SELECTION_MODE", "").lower() in ("1", "true", "yes")
if safe_mode:
    q = q.eq("selection_mode", "LIVE_SAFE")
```

**Problem:** The filter is applied in `_fetch_settled()` which is used by `get_performance_summary()`, but the banner query in `performance_report.py` does NOT use this filter.

**Result:**
- Banner: Total settled = 71 (ALL predictions)
- Phase 1: Settled total = 2 (LIVE_SAFE only)
- Contradiction: "Total settled = 71" but "Settled total = 0" (if no LIVE_SAFE settled)

---

## Phase 4: Fix Options

### Option A: All sections use LIVE_SAFE only

**Changes needed:**
1. Update banner query to filter by selection_mode = "LIVE_SAFE"
2. Update _get_odds_source_breakdown to filter by selection_mode = "LIVE_SAFE"
3. Add label "LIVE_SAFE only" to all sections

**Pros:** Consistent dataset throughout
**Cons:** Loses visibility into RESEARCH picks

### Option B: Clearly separate datasets

**Changes needed:**
1. Keep banner showing ALL breakdown
2. Add separate banner for LIVE_SAFE only
3. Label each phase with which dataset it uses:
   - Phase 1: "LIVE_SAFE settled"
   - Phase 2: "LIVE_SAFE ROI"
   - Phase 6: "ALL predictions breakdown"

**Pros:** Full visibility
**Cons:** More complex UI

**Recommended:** Option B (clear separation with labels)

---

## Phase 5: Implementation (Option B)

### Changes to performance_report.py

1. Update banner to show both ALL and LIVE_SAFE:
```python
if safe_mode:
    # Query ALL settled
    q_all = (
        repo._client.table("predictions")
        .select("selection_mode", count="exact")
        .in_("status", ["WON", "LOST", "VOID"])
    )
    if _since:
        cutoff = _since
        if "T" in cutoff:
            q_all = q_all.gte("created_at", cutoff)
        else:
            q_all = q_all.gte("prediction_date", cutoff)
    rows_all = q_all.execute().data or []
    live_safe = sum(1 for r in rows_all if r.get("selection_mode") == "LIVE_SAFE")
    research = sum(1 for r in rows_all if r.get("selection_mode") == "RESEARCH")
    total_all = len(rows_all)

    print(f"  {YELLOW}╔══ SAFE_SELECTION_MODE active ══════════════════════════════╗{RESET}")
    print(f"  {YELLOW}║{RESET}  ALL settled           : {CYAN}{total_all}{RESET}")
    print(f"  {YELLOW}║{RESET}  LIVE_SAFE picks       : {GREEN}{live_safe}{RESET}")
    print(f"  {YELLOW}║{RESET}  RESEARCH picks        : {RED}{research}{RESET}")
    print(f"  {YELLOW}╚════════════════════════════════════════════════════════════╝{RESET}\n")
    print(f"  {DIM}→ ROI and accuracy below use LIVE_SAFE picks only{RESET}\n")
```

2. Update Phase 1 label:
```python
print(f"  {BOLD}── PHASE 1 — Odds Audit (LIVE_SAFE only) {'─'*38}{RESET}")
```

3. Update _get_odds_source_breakdown to accept selection_mode filter:
```python
def _get_odds_source_breakdown(repo, days: int = 30, since_date: str = None, selection_mode: str = None) -> dict:
    ...
    q = repo._client.table("predictions").select(
        "odds_source,status,bookmaker_odd"
    )
    if selection_mode:
        q = q.eq("selection_mode", selection_mode)
    ...
```

4. Call with selection_mode filter:
```python
src_breakdown = _get_odds_source_breakdown(
    repo, days=days, since_date=_since if _since else None,
    selection_mode="LIVE_SAFE" if safe_mode else None
)
```

---

## Conclusion

**Root Cause:** SAFE_MODE banner queries ALL predictions while get_performance_summary filters to LIVE_SAFE only, creating dataset inconsistency.

**Fix:** Option B - Clearly separate datasets with labels showing which dataset each section uses.

**Status:** AUDIT COMPLETE — FIX READY (NOT IMPLEMENTED)
