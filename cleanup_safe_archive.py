from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / f"_archive_cleanup_{datetime.now().strftime('%Y%m%d')}"

KEEP_EXACT = {
    "start.py",
    "app_flask.py",
    "requirements.txt",
    ".env",
    ".env.example",
    "package.json",
    "package-lock.json",
    "vite.config.ts",
    "tsconfig.json",
    "README.md",

    # Core audits / reports still useful
    "audit_report_consistency.py",
    "audit_probability_persistence.py",
    "audit_safe_selection.py",
    "audit_shadow_vs_safe.py",
    "audit_toxic_patterns.py",
    "audit_tier_quality.py",
    "audit_event_mode.py",
    "audit_event_mode_cycle_integration.py",
    "validate_event_mode_complete.py",
    "audit_ngrok_front_connectivity.py",
    "audit_performance_report_consistency.py",
    "SAFE_SELECTION_FINAL_REPORT.py",
    "TIER_FORENSIC_REPORT.md",
}

KEEP_DIRS = {
    "app",
    "scripts",
    "src",
    "public",
    "node_modules",  # not archived automatically
    ".git",
    "app/database/migrations",
}

ARCHIVE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".cache",
}

ARCHIVE_EXTENSIONS = {
    ".log",
    ".tmp",
    ".bak",
    ".old",
    ".csv",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}

ARCHIVE_PREFIXES = {
    "prompt_",
    "AUDIT_",
    "REPORT_",
    "IMPLEMENTATION_",
    "DEBUG_",
}

KEEP_MIGRATION_KEYWORDS = {
    "schema",
    "tracking_generation",
    "ev_persistence",
    "safe_selection",
    "shadow_tier",
    "event",
    "odds",
    "multimarket",
    "bettable",
    "backfill_tracking",
    "run_all_pending",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_inside_keep_dir(path: Path) -> bool:
    r = rel(path)
    for d in KEEP_DIRS:
        if r == d or r.startswith(d + "/"):
            return True
    return False


def should_keep(path: Path) -> bool:
    name = path.name
    r = rel(path)

    if name in KEEP_EXACT:
        return True

    if r.startswith("app/database/migrations/"):
        lower = name.lower()
        return any(k in lower for k in KEEP_MIGRATION_KEYWORDS)

    if r.startswith(("app/", "scripts/", "src/", "public/")):
        return True

    return False


def should_archive(path: Path) -> tuple[bool, str]:
    name = path.name
    r = rel(path)

    if path == ARCHIVE or r.startswith("_archive_cleanup_"):
        return False, "archive folder"

    if should_keep(path):
        return False, "keep"

    if path.is_dir() and name in ARCHIVE_DIR_NAMES:
        return True, "cache/build directory"

    if path.is_file() and path.suffix.lower() in ARCHIVE_EXTENSIONS:
        return True, f"temporary/export file {path.suffix}"

    if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
        if name not in KEEP_EXACT:
            return True, "old documentation/text file"

    if path.is_file() and name.startswith(tuple(ARCHIVE_PREFIXES)):
        return True, "old generated report/prompt"

    if path.is_file() and name.startswith("audit_") and name not in KEEP_EXACT:
        return True, "old audit script"

    if path.is_file() and name.startswith(("test_", "debug_", "fix_", "verify_")):
        return True, "temporary helper script"

    return False, "manual review / keep"


def collect_candidates() -> list[tuple[Path, str]]:
    candidates = []

    for path in ROOT.rglob("*"):
        if path == ARCHIVE:
            continue

        r = rel(path)

        if r.startswith((".git/", "node_modules/", "_archive_cleanup_")):
            continue

        if path.is_dir():
            ok, reason = should_archive(path)
            if ok:
                candidates.append((path, reason))
            continue

        ok, reason = should_archive(path)
        if ok:
            candidates.append((path, reason))

    # Avoid moving files inside directories already selected
    selected_dirs = [p for p, _ in candidates if p.is_dir()]
    filtered = []
    for p, reason in candidates:
        if p.is_file() and any(str(p).startswith(str(d) + os.sep) for d in selected_dirs):
            continue
        filtered.append((p, reason))

    return filtered


def move_to_archive(candidates: list[tuple[Path, str]]) -> None:
    ARCHIVE.mkdir(exist_ok=True)

    report_lines = [
        "# Cleanup Report",
        "",
        f"Archive folder: `{ARCHIVE.name}`",
        "",
        "## Archived files",
        "",
    ]

    for path, reason in candidates:
        target = ARCHIVE / rel(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        print(f"ARCHIVE: {rel(path)}  ({reason})")
        shutil.move(str(path), str(target))
        report_lines.append(f"- `{rel(path)}` — {reason}")

    (ARCHIVE / "CLEANUP_REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")


def main() -> None:
    dry_run = "--apply" not in os.sys.argv
    candidates = collect_candidates()

    print("=" * 70)
    print("SAFE CLEANUP ARCHIVE")
    print("=" * 70)
    print(f"Root     : {ROOT}")
    print(f"Archive  : {ARCHIVE.name}")
    print(f"Mode     : {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"Files/dirs to archive: {len(candidates)}")
    print()

    for path, reason in candidates[:300]:
        print(f"{rel(path):70}  {reason}")

    if len(candidates) > 300:
        print(f"... +{len(candidates) - 300} more")

    print()
    if dry_run:
        print("No files moved.")
        print("Run with:")
        print("python cleanup_safe_archive.py --apply")
        return

    move_to_archive(candidates)
    print()
    print("Archive complete.")
    print("Now validate:")
    print("python -m py_compile start.py app_flask.py")
    print("python audit_report_consistency.py")
    print("python audit_safe_selection.py")
    print("python scripts/performance_report.py --since-reset")


if __name__ == "__main__":
    main()
