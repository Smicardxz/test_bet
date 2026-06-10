"""
Supabase Configuration — Phase 1
==================================
Reads SUPABASE_URL and SUPABASE_KEY from environment.
Never hardcodes credentials.
Exposes:  supabase_connected / supabase_error / supabase_status
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_URL_ENV = "SUPABASE_URL"
_KEY_ENV  = "SUPABASE_KEY"


class SupabaseConfig:
    """
    Validates Supabase credentials and holds a ready-to-use client.
    Fully non-blocking: any failure sets supabase_connected=False
    and allows the rest of the app to continue.
    """

    def __init__(self):
        self.url: Optional[str]    = os.getenv(_URL_ENV)
        self.key: Optional[str]    = os.getenv(_KEY_ENV)
        self.supabase_connected: bool         = False
        self.supabase_error: Optional[str]    = None
        self.supabase_status: str             = "NOT_CONFIGURED"
        self._client = None
        self._try_connect()

    # ─── Internal ──────────────────────────────────────────────────────────────
    def _try_connect(self) -> None:
        if not self.url:
            self.supabase_error  = f"{_URL_ENV} not set in .env"
            self.supabase_status = "NOT_CONFIGURED"
            return
        if not self.key:
            self.supabase_error  = f"{_KEY_ENV} not set in .env"
            self.supabase_status = "NOT_CONFIGURED"
            return
        if not self.url.startswith("https://"):
            self.supabase_error  = f"{_URL_ENV} must start with https://"
            self.supabase_status = "INVALID_URL"
            return

        try:
            from supabase import create_client  # optional dependency
            self._client = create_client(self.url, self.key)
            # Lightweight connectivity probe — fetch at most 1 row from fixtures
            self._client.table("fixtures").select("fixture_id").limit(1).execute()
            self.supabase_connected = True
            self.supabase_status    = "CONNECTED"
            logger.info(f"[SUPABASE] Connected → {self.url}")
        except ImportError:
            self.supabase_error  = (
                "supabase package not installed. "
                "Run: pip install supabase"
            )
            self.supabase_status = "PACKAGE_MISSING"
            logger.warning(f"[SUPABASE] {self.supabase_error}")
        except Exception as exc:
            exc_str = str(exc)
            # PGRST205 = table not found in schema cache → credentials OK,
            # but the SQL schema has not been deployed yet.
            if "PGRST205" in exc_str or "schema cache" in exc_str:
                self.supabase_connected = True
                self.supabase_status    = "CONNECTED_SCHEMA_MISSING"
                self.supabase_error     = (
                    "Credentials valid but tables not found. "
                    "Run app/database/schema.sql in Supabase SQL Editor."
                )
                logger.warning(f"[SUPABASE] Schema not deployed — run schema.sql")
            # 401/403 → invalid key
            elif "401" in exc_str or "403" in exc_str or "Invalid API" in exc_str:
                self.supabase_error  = "Invalid SUPABASE_KEY — use service_role key"
                self.supabase_status = "AUTH_ERROR"
                logger.warning(f"[SUPABASE] Auth error: {exc}")
            else:
                self.supabase_error  = exc_str[:300]
                self.supabase_status = "CONNECTION_ERROR"
                logger.warning(f"[SUPABASE] Connection failed: {exc}")

    # ─── Public API ────────────────────────────────────────────────────────────
    def get_client(self):
        """Return the supabase client or None."""
        return self._client

    def to_dict(self) -> dict:
        return {
            "supabase_connected": self.supabase_connected,
            "supabase_error":     self.supabase_error,
            "supabase_status":    self.supabase_status,
            "supabase_url_set":   bool(self.url),
            "supabase_key_set":   bool(self.key),
        }


# ─── Module singleton ─────────────────────────────────────────────────────────
_cfg: Optional[SupabaseConfig] = None


def get_supabase_config() -> SupabaseConfig:
    global _cfg
    if _cfg is None:
        _cfg = SupabaseConfig()
    return _cfg


def get_supabase_client():
    """Shortcut: return the ready client, or None."""
    return get_supabase_config().get_client()


def reset_supabase_config() -> None:
    """Force re-read of env vars — useful for tests."""
    global _cfg
    _cfg = None
