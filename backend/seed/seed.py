# backend/seed/seed.py
"""
Run this script once to populate the drivers table from drivers.json.
Run annually to refresh pricing: python3 seed/seed.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import database

def seed_drivers():
    database.init_db()
    seed_file = Path(__file__).parent / "drivers.json"
    drivers = json.loads(seed_file.read_text())

    with database.get_connection() as conn:
        existing = {
            row["model"] for row in conn.execute("SELECT model FROM drivers").fetchall()
        }
        inserted = 0
        for d in drivers:
            if d["model"] not in existing:
                conn.execute("""
                    INSERT INTO drivers (
                        manufacturer, model, type, fs_hz, qts, vas_liters,
                        xmax_mm, sensitivity_db, power_rms_w, diameter_mm,
                        price_usd, price_updated_date, datasheet_url, buy_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d["manufacturer"], d["model"], d["type"], d["fs_hz"],
                    d["qts"], d["vas_liters"], d["xmax_mm"], d["sensitivity_db"],
                    d["power_rms_w"], d["diameter_mm"], d["price_usd"],
                    d["price_updated_date"], d.get("datasheet_url"), d.get("buy_url")
                ))
                inserted += 1
    print(f"Seeded {inserted} new drivers ({len(existing)} already present).")

if __name__ == "__main__":
    seed_drivers()
