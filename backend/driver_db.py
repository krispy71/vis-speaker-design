import json
from typing import Optional
import database
from models import Driver


def find_driver_candidates(
    driver_type: str,
    budget_usd: float,
    diameter_mm_min: int = 0,
    diameter_mm_max: int = 999,
    limit: int = 5,
) -> list[Driver]:
    """Return up to `limit` drivers matching type and budget."""
    with database.get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM drivers
            WHERE type = ?
              AND price_usd <= ?
              AND diameter_mm >= ?
              AND diameter_mm <= ?
            ORDER BY sensitivity_db DESC
            LIMIT ?
        """, (driver_type, budget_usd, diameter_mm_min, diameter_mm_max, limit)).fetchall()
    return [Driver(**dict(row)) for row in rows]


def cache_research_result(
    query: str,
    driver_model: str,
    source_url: Optional[str],
    ts_params: dict,
    price_usd: float,
) -> None:
    """Store a Claude web-research result in driver_search_cache."""
    with database.get_connection() as conn:
        conn.execute("""
            INSERT INTO driver_search_cache
                (query, driver_model, source_url, ts_params_json, price_usd)
            VALUES (?, ?, ?, ?, ?)
        """, (query, driver_model, source_url, json.dumps(ts_params), price_usd))


def get_cached_research(driver_model: str) -> Optional[dict]:
    """Return the most recent cached research entry for a driver model."""
    with database.get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM driver_search_cache
            WHERE driver_model = ?
            ORDER BY fetched_at DESC
            LIMIT 1
        """, (driver_model,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["ts_params"] = json.loads(result["ts_params_json"])
    return result


def promote_cache_to_catalog(cache_id: int) -> None:
    """Promote a driver_search_cache entry to the drivers table if all required TS params are present."""
    with database.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM driver_search_cache WHERE id = ?", (cache_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Cache entry {cache_id} not found")
        ts = json.loads(row["ts_params_json"])
        required = {"fs_hz", "qts", "vas_liters", "xmax_mm", "sensitivity_db"}
        if not required.issubset(ts.keys()) or row["source_url"] is None:
            raise ValueError("Missing required TS params or datasheet URL — hold for manual review")
        conn.execute("""
            INSERT OR IGNORE INTO drivers
                (manufacturer, model, type, fs_hz, qts, vas_liters, xmax_mm,
                 sensitivity_db, power_rms_w, diameter_mm, price_usd,
                 price_updated_date, datasheet_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date('now'), ?)
        """, (
            ts.get("manufacturer", "Unknown"),
            row["driver_model"],
            ts.get("type", "woofer"),
            ts["fs_hz"], ts["qts"], ts["vas_liters"], ts["xmax_mm"],
            ts["sensitivity_db"],
            ts.get("power_rms_w", 0),
            ts.get("diameter_mm", 0),
            row["price_usd"],
            row["source_url"],
        ))
