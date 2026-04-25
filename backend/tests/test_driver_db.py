import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import database
from driver_db import find_driver_candidates, cache_research_result, get_cached_research
from models import Driver

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    import database as db_mod
    db_mod.DB_PATH = tmp_path / "test.db"
    database.init_db()
    # Insert two test drivers
    with database.get_connection() as conn:
        conn.execute("""
            INSERT INTO drivers (manufacturer, model, type, fs_hz, qts, vas_liters,
            xmax_mm, sensitivity_db, power_rms_w, diameter_mm, price_usd,
            price_updated_date, datasheet_url, buy_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Dayton", "RS180-8", "woofer", 33.0, 0.32, 31.9, 9.5, 87.3, 75, 180, 59.98, "2026-01-01", None, None))
        conn.execute("""
            INSERT INTO drivers (manufacturer, model, type, fs_hz, qts, vas_liters,
            xmax_mm, sensitivity_db, power_rms_w, diameter_mm, price_usd,
            price_updated_date, datasheet_url, buy_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Dayton", "ND25FA-4", "tweeter", 1400.0, 0.0, 0.0, 0.5, 91.5, 50, 25, 24.98, "2026-01-01", None, None))

def test_find_woofers_returns_matching_type():
    results = find_driver_candidates(driver_type="woofer", budget_usd=200.0)
    assert len(results) == 1
    assert results[0].model == "RS180-8"

def test_find_candidates_respects_budget():
    results = find_driver_candidates(driver_type="woofer", budget_usd=50.0)
    assert len(results) == 0

def test_find_candidates_caps_at_five():
    with database.get_connection() as conn:
        for i in range(6):
            conn.execute("""
                INSERT INTO drivers (manufacturer, model, type, fs_hz, qts, vas_liters,
                xmax_mm, sensitivity_db, power_rms_w, diameter_mm, price_usd,
                price_updated_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("Test", f"W{i}", "woofer", 30.0, 0.3, 20.0, 8.0, 87.0, 80, 180, 50.0, "2026-01-01"))
    results = find_driver_candidates(driver_type="woofer", budget_usd=200.0)
    assert len(results) <= 5

def test_cache_and_retrieve_research():
    cache_research_result(
        query="ScanSpeak 18W",
        driver_model="18W/8531G00",
        source_url="https://example.com",
        ts_params={"fs_hz": 28.0, "qts": 0.30},
        price_usd=189.0
    )
    cached = get_cached_research("18W/8531G00")
    assert cached is not None
    assert cached["price_usd"] == 189.0
