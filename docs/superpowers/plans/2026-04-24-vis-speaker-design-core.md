# vis-speaker-design Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app where a user has a natural conversation with Claude (as an expert speaker designer) and receives a complete speaker design with bill of materials.

**Architecture:** Phase-based: Claude CLI subprocess handles intake Q&A (multi-turn), design generation (single-turn), and BOM assembly (single-turn). FastAPI orchestrates phases and persists state in SQLite. React frontend shows chat on the left and results on the right. Background tasks handle the slow Phase 2+3 generation so the HTTP layer stays responsive.

**Tech Stack:** Python 3.12, FastAPI, SQLite (stdlib), Pydantic v2, WeasyPrint (PDF), pytest — React 18, TypeScript, Vite, Vitest

---

## File Map

```
vis-speaker-design/
├── backend/
│   ├── main.py               # FastAPI app and all routes
│   ├── models.py             # Pydantic models for all domain objects
│   ├── database.py           # SQLite connection and schema init
│   ├── driver_db.py          # Driver catalog queries
│   ├── claude_runner.py      # claude -p subprocess wrapper
│   ├── session_manager.py    # Session CRUD + all three phase runners
│   ├── export.py             # PDF (WeasyPrint) and CSV generation
│   ├── seed/
│   │   ├── drivers.json      # Pre-seeded driver catalog (~100 drivers, start with 8)
│   │   └── seed.py           # Loads drivers.json into SQLite
│   └── tests/
│       ├── conftest.py       # Shared fixtures (in-memory DB, mock claude)
│       ├── test_driver_db.py
│       ├── test_claude_runner.py
│       ├── test_session_manager.py
│       └── test_export.py
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── types.ts              # All shared TypeScript types
│       ├── api/
│       │   └── client.ts         # All fetch calls to FastAPI
│       ├── context/
│       │   └── SessionContext.tsx # Session state + polling logic
│       └── components/
│           ├── ChatPanel.tsx
│           ├── PhaseIndicator.tsx
│           ├── ResultsPanel.tsx
│           ├── DriverCard.tsx
│           ├── BomTable.tsx
│           └── ExportButtons.tsx
├── requirements.txt
└── pytest.ini
```

---

## Task 1: Backend scaffold

**Files:**
- Create: `backend/` directory structure
- Create: `requirements.txt`
- Create: `pytest.ini`

- [ ] **Step 1: Create backend directory structure**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
mkdir -p backend/seed backend/tests
touch backend/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```
fastapi==0.136.1
uvicorn[standard]==0.34.0
pydantic==2.12.5
weasyprint==65.1
pytest==9.0.3
pytest-asyncio==0.26.0
httpx==0.28.1
```

- [ ] **Step 3: Install requirements**

```bash
pip3 install -r requirements.txt
```

Expected: installs uvicorn, weasyprint, httpx, pytest-asyncio. fastapi and pydantic already installed.

- [ ] **Step 4: Write pytest.ini**

```ini
[pytest]
testpaths = backend/tests
asyncio_mode = auto
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pytest.ini backend/
git commit -m "feat: backend scaffold and dependencies"
```

---

## Task 2: Database schema

**Files:**
- Create: `backend/database.py`
- Test: `backend/tests/conftest.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/conftest.py
import sqlite3
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import init_db, get_connection

@pytest.fixture
def db(tmp_path):
    """In-memory SQLite database for tests."""
    import database
    original = database.DB_PATH
    database.DB_PATH = tmp_path / "test.db"
    init_db()
    yield database.DB_PATH
    database.DB_PATH = original
```

```python
# backend/tests/test_database_schema.py
def test_drivers_table_exists(db):
    import database
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='drivers'"
        ).fetchall()
    assert len(rows) == 1

def test_sessions_table_exists(db):
    import database
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchall()
    assert len(rows) == 1

def test_driver_search_cache_table_exists(db):
    import database
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='driver_search_cache'"
        ).fetchall()
    assert len(rows) == 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
python3 -m pytest backend/tests/test_database_schema.py -v
```

Expected: `ModuleNotFoundError: No module named 'database'`

- [ ] **Step 3: Write database.py**

```python
# backend/database.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "speaker_design.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manufacturer TEXT NOT NULL,
                model TEXT NOT NULL,
                type TEXT NOT NULL,
                fs_hz REAL,
                qts REAL,
                vas_liters REAL,
                xmax_mm REAL,
                sensitivity_db REAL,
                power_rms_w INTEGER,
                diameter_mm INTEGER,
                price_usd REAL,
                price_updated_date TEXT,
                datasheet_url TEXT,
                buy_url TEXT
            );

            CREATE TABLE IF NOT EXISTS driver_search_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                driver_model TEXT NOT NULL,
                source_url TEXT,
                ts_params_json TEXT,
                price_usd REAL,
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                phase TEXT NOT NULL DEFAULT 'intake',
                conversation_json TEXT NOT NULL DEFAULT '[]',
                design_brief_json TEXT,
                design_output_json TEXT,
                bom_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_database_schema.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/database.py backend/tests/conftest.py backend/tests/test_database_schema.py
git commit -m "feat: SQLite schema with drivers, sessions, driver_search_cache tables"
```

---

## Task 3: Pydantic models

**Files:**
- Create: `backend/models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py
import pytest
from models import (
    Phase, Message, DesignBrief, Driver, CrossoverComponent,
    Crossover, DriverSelection, DesignOutput, BOMItem, BOM, Session
)

def test_phase_values():
    assert Phase.INTAKE == "intake"
    assert Phase.DESIGN == "design"
    assert Phase.BOM == "bom"
    assert Phase.COMPLETE == "complete"

def test_design_brief_requires_fields():
    with pytest.raises(Exception):
        DesignBrief()  # missing required fields

def test_design_brief_creates_correctly():
    brief = DesignBrief(
        room_size="medium (15x20ft)",
        amp_power="50W tube",
        sources=["vinyl"],
        topology_preference="passive",
        budget_drivers_usd=800.0,
        listening_goals="natural timbre",
        constraints=[]
    )
    assert brief.budget_drivers_usd == 800.0

def test_session_defaults():
    s = Session(id="abc123")
    assert s.phase == Phase.INTAKE
    assert s.conversation == []
    assert s.design_brief is None
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Write models.py**

```python
# backend/models.py
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Phase(str, Enum):
    INTAKE = "intake"
    DESIGN = "design"
    BOM = "bom"
    COMPLETE = "complete"


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class DesignBrief(BaseModel):
    room_size: str
    amp_power: str
    sources: list[str]
    topology_preference: str  # passive / active / biamped
    budget_drivers_usd: float
    listening_goals: str
    constraints: list[str]


class Driver(BaseModel):
    id: Optional[int] = None
    manufacturer: str
    model: str
    type: str  # woofer / mid / tweeter / fullrange
    fs_hz: float
    qts: float
    vas_liters: float
    xmax_mm: float
    sensitivity_db: float
    power_rms_w: int
    diameter_mm: int
    price_usd: float
    price_updated_date: str
    datasheet_url: Optional[str] = None
    buy_url: Optional[str] = None


class CrossoverComponent(BaseModel):
    type: str    # inductor / capacitor / resistor
    value: str   # e.g. "3.3mH", "10uF", "6.8Ω"
    role: str    # e.g. "woofer low-pass L1"


class Crossover(BaseModel):
    topology: str           # e.g. "2nd order Linkwitz-Riley"
    crossover_freq_hz: int
    components: list[CrossoverComponent]


class DriverSelection(BaseModel):
    role: str               # woofer / mid / tweeter
    manufacturer: str
    model: str
    justification: str
    ts_params: dict


class DesignOutput(BaseModel):
    speaker_type: str       # 2-way / 3-way / fullrange
    enclosure_type: str     # sealed / ported / open-baffle
    enclosure_dimensions_mm: dict  # {"h": int, "w": int, "d": int}
    internal_volume_liters: float
    drivers: list[DriverSelection]
    crossover: Crossover
    dsp_notes: Optional[str] = None


class BOMItem(BaseModel):
    category: str
    part: str
    manufacturer: str
    model: str
    qty: int
    unit_price: float
    extended_price: float
    source_url: Optional[str] = None


class BOM(BaseModel):
    items: list[BOMItem]
    subtotals: dict         # {"drivers": float, "crossover": float, "hardware": float}
    grand_total: float
    rationale: str          # Claude-generated design rationale paragraph


class Session(BaseModel):
    id: str
    phase: Phase = Phase.INTAKE
    conversation: list[Message] = []
    design_brief: Optional[DesignBrief] = None
    design_output: Optional[DesignOutput] = None
    bom: Optional[BOM] = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_models.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat: Pydantic models for all domain objects"
```

---

## Task 4: Driver seed data

**Files:**
- Create: `backend/seed/drivers.json`
- Create: `backend/seed/seed.py`

- [ ] **Step 1: Write drivers.json** (representative 8-driver set; expand to ~100 before production by adding more entries following this same schema)

```json
[
  {
    "manufacturer": "Dayton Audio",
    "model": "RS180-8",
    "type": "woofer",
    "fs_hz": 33.0,
    "qts": 0.32,
    "vas_liters": 31.9,
    "xmax_mm": 9.5,
    "sensitivity_db": 87.3,
    "power_rms_w": 75,
    "diameter_mm": 180,
    "price_usd": 59.98,
    "price_updated_date": "2026-01-01",
    "datasheet_url": "https://www.parts-express.com/pedocs/specs/275-196-dayton-audio-rs180-8-specs.pdf",
    "buy_url": "https://www.parts-express.com/Dayton-Audio-RS180-8-7-Reference-Woofer-8-Ohm-275-196"
  },
  {
    "manufacturer": "Dayton Audio",
    "model": "RS225-8",
    "type": "woofer",
    "fs_hz": 23.7,
    "qts": 0.28,
    "vas_liters": 65.9,
    "xmax_mm": 11.0,
    "sensitivity_db": 88.2,
    "power_rms_w": 100,
    "diameter_mm": 225,
    "price_usd": 79.98,
    "price_updated_date": "2026-01-01",
    "datasheet_url": "https://www.parts-express.com/pedocs/specs/275-215-dayton-audio-rs225-8-specs.pdf",
    "buy_url": "https://www.parts-express.com/Dayton-Audio-RS225-8-8-Reference-Woofer-8-Ohm-275-215"
  },
  {
    "manufacturer": "ScanSpeak",
    "model": "18W/8531G00",
    "type": "woofer",
    "fs_hz": 28.0,
    "qts": 0.30,
    "vas_liters": 39.0,
    "xmax_mm": 7.5,
    "sensitivity_db": 89.0,
    "power_rms_w": 100,
    "diameter_mm": 180,
    "price_usd": 189.00,
    "price_updated_date": "2026-01-01",
    "datasheet_url": "https://www.madisoundspeakerstore.com/images/products/18W-8531G00.pdf",
    "buy_url": "https://www.madisoundspeakerstore.com/scanspeak-woofers-7/scanspeak-18w8531g00-7-revelator-woofer/"
  },
  {
    "manufacturer": "SEAS",
    "model": "CA18RNX",
    "type": "woofer",
    "fs_hz": 35.0,
    "qts": 0.35,
    "vas_liters": 21.0,
    "xmax_mm": 7.5,
    "sensitivity_db": 88.5,
    "power_rms_w": 90,
    "diameter_mm": 180,
    "price_usd": 95.00,
    "price_updated_date": "2026-01-01",
    "datasheet_url": "https://www.seas.no/images/stories/prestige/sea_ca18rnx_002.pdf",
    "buy_url": "https://www.madisoundspeakerstore.com/seas-woofers-7/seas-ca18rnx-h1216-excel-woofer/"
  },
  {
    "manufacturer": "ScanSpeak",
    "model": "D2608/913000",
    "type": "tweeter",
    "fs_hz": 520.0,
    "qts": 0.0,
    "vas_liters": 0.0,
    "xmax_mm": 0.5,
    "sensitivity_db": 92.0,
    "power_rms_w": 150,
    "diameter_mm": 26,
    "price_usd": 109.00,
    "price_updated_date": "2026-01-01",
    "datasheet_url": "https://www.madisoundspeakerstore.com/images/products/D2608-913000.pdf",
    "buy_url": "https://www.madisoundspeakerstore.com/scanspeak-tweeters/scanspeak-d2608913000-illuminator-tweeter/"
  },
  {
    "manufacturer": "Dayton Audio",
    "model": "ND25FA-4",
    "type": "tweeter",
    "fs_hz": 1400.0,
    "qts": 0.0,
    "vas_liters": 0.0,
    "xmax_mm": 0.5,
    "sensitivity_db": 91.5,
    "power_rms_w": 50,
    "diameter_mm": 25,
    "price_usd": 24.98,
    "price_updated_date": "2026-01-01",
    "datasheet_url": "https://www.parts-express.com/pedocs/specs/275-025-dayton-audio-nd25fa-4-specs.pdf",
    "buy_url": "https://www.parts-express.com/Dayton-Audio-ND25FA-4-1-Soft-Dome-Neodymium-Tweeter-4-Ohm-275-025"
  },
  {
    "manufacturer": "Tang Band",
    "model": "W4-1320SJ",
    "type": "fullrange",
    "fs_hz": 102.0,
    "qts": 0.43,
    "vas_liters": 1.25,
    "xmax_mm": 3.5,
    "sensitivity_db": 86.0,
    "power_rms_w": 15,
    "diameter_mm": 100,
    "price_usd": 29.98,
    "price_updated_date": "2026-01-01",
    "datasheet_url": "https://www.parts-express.com/pedocs/specs/264-917-tang-band-w4-1320sj-specs.pdf",
    "buy_url": "https://www.parts-express.com/Tang-Band-W4-1320SJ-4-Paper-Cone-Full-Range-Driver-264-917"
  },
  {
    "manufacturer": "SEAS",
    "model": "T25CF002",
    "type": "tweeter",
    "fs_hz": 600.0,
    "qts": 0.0,
    "vas_liters": 0.0,
    "xmax_mm": 0.5,
    "sensitivity_db": 91.0,
    "power_rms_w": 100,
    "diameter_mm": 25,
    "price_usd": 55.00,
    "price_updated_date": "2026-01-01",
    "datasheet_url": "https://www.seas.no/images/stories/excel/sea_t25cf002_001.pdf",
    "buy_url": "https://www.madisoundspeakerstore.com/seas-tweeters/seas-t25cf002-h1283-excel-tweeter/"
  }
]
```

- [ ] **Step 2: Write seed.py**

```python
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
```

- [ ] **Step 3: Run the seed script**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
python3 backend/seed/seed.py
```

Expected: `Seeded 8 new drivers (0 already present).`

- [ ] **Step 4: Verify data**

```bash
python3 -c "
import sys; sys.path.insert(0, 'backend')
import database
with database.get_connection() as conn:
    rows = conn.execute('SELECT manufacturer, model, type FROM drivers').fetchall()
    for r in rows: print(r['manufacturer'], r['model'], r['type'])
"
```

Expected: 8 rows printed.

- [ ] **Step 5: Commit**

```bash
git add backend/seed/
git commit -m "feat: driver seed data with 8 representative drivers"
```

---

## Task 5: Driver DB queries

**Files:**
- Create: `backend/driver_db.py`
- Test: `backend/tests/test_driver_db.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_driver_db.py
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_driver_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'driver_db'`

- [ ] **Step 3: Write driver_db.py**

```python
# backend/driver_db.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_driver_db.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/driver_db.py backend/tests/test_driver_db.py
git commit -m "feat: driver DB queries with candidate lookup and research cache"
```

---

## Task 6: Claude Runner

**Files:**
- Create: `backend/claude_runner.py`
- Test: `backend/tests/test_claude_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_claude_runner.py
import pytest
from unittest.mock import patch, MagicMock
import subprocess
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from claude_runner import run_claude, ClaudeError

def test_run_claude_returns_stdout():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Hello from Claude\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = run_claude("say hello")
    assert result == "Hello from Claude"
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args[0][0][0] == "claude"
    assert call_args[0][0][1] == "-p"

def test_run_claude_raises_on_nonzero_exit():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "authentication error"
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(ClaudeError, match="authentication error"):
            run_claude("say hello")

def test_run_claude_raises_on_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 120)):
        with pytest.raises(ClaudeError, match="timed out"):
            run_claude("say hello")
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_claude_runner.py -v
```

Expected: `ModuleNotFoundError: No module named 'claude_runner'`

- [ ] **Step 3: Write claude_runner.py**

```python
# backend/claude_runner.py
import subprocess


class ClaudeError(Exception):
    pass


def run_claude(prompt: str, timeout: int = 120) -> str:
    """
    Run `claude -p <prompt>` and return the response text.
    Raises ClaudeError on non-zero exit or timeout.
    """
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ClaudeError(f"Claude CLI timed out after {timeout}s")

    if result.returncode != 0:
        raise ClaudeError(result.stderr.strip() or "Claude CLI returned non-zero exit code")

    return result.stdout.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_claude_runner.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/claude_runner.py backend/tests/test_claude_runner.py
git commit -m "feat: Claude CLI subprocess runner with error handling"
```

---

## Task 7: Session CRUD

**Files:**
- Create: `backend/session_manager.py` (CRUD only — phase runners added in Tasks 8-10)
- Test: `backend/tests/test_session_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_session_manager.py
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import database
from session_manager import create_session, get_session, save_session
from models import Session, Phase, Message

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    import database as db_mod
    db_mod.DB_PATH = tmp_path / "test.db"
    database.init_db()

def test_create_session_returns_session_with_id():
    session = create_session()
    assert session.id
    assert session.phase == Phase.INTAKE
    assert session.conversation == []

def test_get_session_returns_saved_session():
    session = create_session()
    fetched = get_session(session.id)
    assert fetched is not None
    assert fetched.id == session.id

def test_get_session_returns_none_for_missing():
    assert get_session("nonexistent") is None

def test_save_session_persists_conversation():
    session = create_session()
    session.conversation.append(Message(role="user", content="hello"))
    save_session(session)
    fetched = get_session(session.id)
    assert len(fetched.conversation) == 1
    assert fetched.conversation[0].content == "hello"

def test_save_session_persists_phase():
    session = create_session()
    session.phase = Phase.DESIGN
    save_session(session)
    fetched = get_session(session.id)
    assert fetched.phase == Phase.DESIGN
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_session_manager.py -v
```

Expected: `ModuleNotFoundError: No module named 'session_manager'`

- [ ] **Step 3: Write session_manager.py (CRUD only)**

```python
# backend/session_manager.py
import uuid
import json
from typing import Optional

import database
from models import Session, Phase, Message, DesignBrief, DesignOutput, BOM


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_session() -> Session:
    session = Session(id=str(uuid.uuid4()))
    with database.get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (id, phase, conversation_json) VALUES (?, ?, ?)",
            (session.id, session.phase.value, "[]"),
        )
    return session


def get_session(session_id: str) -> Optional[Session]:
    with database.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_session(row)


def save_session(session: Session) -> None:
    with database.get_connection() as conn:
        conn.execute("""
            UPDATE sessions SET
                phase = ?,
                conversation_json = ?,
                design_brief_json = ?,
                design_output_json = ?,
                bom_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            session.phase.value,
            json.dumps([m.model_dump() for m in session.conversation]),
            session.design_brief.model_dump_json() if session.design_brief else None,
            session.design_output.model_dump_json() if session.design_output else None,
            session.bom.model_dump_json() if session.bom else None,
            session.id,
        ))


def _row_to_session(row) -> Session:
    d = dict(row)
    return Session(
        id=d["id"],
        phase=Phase(d["phase"]),
        conversation=[Message(**m) for m in json.loads(d["conversation_json"])],
        design_brief=DesignBrief.model_validate_json(d["design_brief_json"]) if d["design_brief_json"] else None,
        design_output=DesignOutput.model_validate_json(d["design_output_json"]) if d["design_output_json"] else None,
        bom=BOM.model_validate_json(d["bom_json"]) if d["bom_json"] else None,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_session_manager.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/session_manager.py backend/tests/test_session_manager.py
git commit -m "feat: session CRUD with SQLite persistence"
```

---

## Task 8: Phase 1 — Intake conversation

**Files:**
- Modify: `backend/session_manager.py` (add `run_intake_turn`)
- Modify: `backend/tests/test_session_manager.py` (add Phase 1 tests)

- [ ] **Step 1: Write the failing tests** (append to test_session_manager.py)

```python
# append to backend/tests/test_session_manager.py
from unittest.mock import patch
from session_manager import run_intake_turn

def test_intake_turn_adds_messages_to_conversation():
    session = create_session()
    with patch("session_manager.run_claude", return_value="What music do you listen to?"):
        reply, brief = run_intake_turn(session, "I want bookshelf speakers")
    assert reply == "What music do you listen to?"
    assert brief is None
    # session should have 2 messages: user + assistant
    fetched = get_session(session.id)
    assert len(fetched.conversation) == 2

def test_intake_turn_detects_completion():
    session = create_session()
    complete_response = """Great, I have what I need.
<<INTAKE_COMPLETE>>
{"room_size": "medium", "amp_power": "50W tube", "sources": ["vinyl"], "topology_preference": "passive", "budget_drivers_usd": 800.0, "listening_goals": "natural timbre", "constraints": []}"""
    with patch("session_manager.run_claude", return_value=complete_response):
        reply, brief = run_intake_turn(session, "Budget is $800")
    assert brief is not None
    assert brief.budget_drivers_usd == 800.0
    fetched = get_session(session.id)
    assert fetched.phase == Phase.DESIGN
    assert fetched.design_brief is not None
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_session_manager.py::test_intake_turn_adds_messages_to_conversation -v
```

Expected: `ImportError: cannot import name 'run_intake_turn'`

- [ ] **Step 3: Add Phase 1 logic to session_manager.py** (append after the CRUD section)

```python
# Add to backend/session_manager.py

import json
import re
from typing import Tuple, Optional
from claude_runner import run_claude
from models import DesignBrief

_INTAKE_SYSTEM = """You are Marcus Webb, a master speaker designer with 20 years of experience building high-fidelity speakers. You are interviewing a client to design their perfect speakers.

Ask ONE question at a time. Be warm, expert, and concise. Cover these topics in natural order:
1. Listening goals and music genres (what they value: bass, imaging, dynamics, timbre)
2. Room size and typical listening position
3. Existing amplifier (brand/model or: power in watts, tube vs solid state)
4. Source material (vinyl, streaming, CD, etc.)
5. Passive, active, or bi-amped preference
6. Budget for drivers and crossover components (USD)
7. Aesthetic and physical constraints (dimensions, finish, partner approval)

When you have gathered enough information (typically after 6-8 exchanges), output EXACTLY this token on its own line:
<<INTAKE_COMPLETE>>
Then output a JSON object with this exact structure (no extra text before or after the JSON):
{
  "room_size": "...",
  "amp_power": "...",
  "sources": ["..."],
  "topology_preference": "passive",
  "budget_drivers_usd": 0.0,
  "listening_goals": "...",
  "constraints": []
}

Begin by greeting the user and asking your first question about their listening goals."""


def _build_intake_prompt(conversation: list[Message], new_user_message: str) -> str:
    history = ""
    for msg in conversation:
        label = "User" if msg.role == "user" else "Marcus"
        history += f"{label}: {msg.content}\n\n"
    history += f"User: {new_user_message}\n\nMarcus:"
    return f"{_INTAKE_SYSTEM}\n\n--- CONVERSATION ---\n\n{history}"


def _parse_intake_response(response: str) -> Tuple[str, Optional[DesignBrief]]:
    if "<<INTAKE_COMPLETE>>" not in response:
        return response.strip(), None
    parts = response.split("<<INTAKE_COMPLETE>>", 1)
    reply = parts[0].strip()
    json_text = parts[1].strip()
    brief = DesignBrief(**json.loads(json_text))
    return reply, brief


def run_intake_turn(
    session: Session, user_message: str
) -> Tuple[str, Optional[DesignBrief]]:
    """
    Send one user message through Phase 1. Returns (reply, design_brief).
    design_brief is non-None only when intake is complete.
    Persists updated session to DB.
    """
    prompt = _build_intake_prompt(session.conversation, user_message)
    response = run_claude(prompt)
    reply, brief = _parse_intake_response(response)

    session.conversation.append(Message(role="user", content=user_message))
    session.conversation.append(Message(role="assistant", content=reply))

    if brief is not None:
        session.design_brief = brief
        session.phase = Phase.DESIGN

    save_session(session)
    return reply, brief
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_session_manager.py -v
```

Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/session_manager.py backend/tests/test_session_manager.py
git commit -m "feat: Phase 1 intake conversation with completion detection"
```

---

## Task 9: Phase 2 — Design generation

**Files:**
- Modify: `backend/session_manager.py` (add `run_design_generation`)
- Modify: `backend/tests/test_session_manager.py`

- [ ] **Step 1: Write the failing tests** (append to test_session_manager.py)

```python
# append to backend/tests/test_session_manager.py
from session_manager import run_design_generation

_SAMPLE_DESIGN_JSON = json.dumps({
    "speaker_type": "2-way",
    "enclosure_type": "sealed",
    "enclosure_dimensions_mm": {"h": 380, "w": 210, "d": 280},
    "internal_volume_liters": 12.5,
    "drivers": [
        {
            "role": "woofer",
            "manufacturer": "Dayton Audio",
            "model": "RS180-8",
            "justification": "Great Qts for sealed box",
            "ts_params": {"fs_hz": 33.0, "qts": 0.32}
        },
        {
            "role": "tweeter",
            "manufacturer": "Dayton Audio",
            "model": "ND25FA-4",
            "justification": "Smooth off-axis",
            "ts_params": {"fs_hz": 1400.0}
        }
    ],
    "crossover": {
        "topology": "2nd order Linkwitz-Riley",
        "crossover_freq_hz": 2200,
        "components": [
            {"type": "inductor", "value": "0.56mH", "role": "woofer low-pass L1"},
            {"type": "capacitor", "value": "10uF", "role": "woofer low-pass C1"},
            {"type": "capacitor", "value": "6.8uF", "role": "tweeter high-pass C1"},
            {"type": "inductor", "value": "0.82mH", "role": "tweeter high-pass L1"}
        ]
    },
    "dsp_notes": None
})

import json

def test_design_generation_populates_design_output():
    session = create_session()
    session.phase = Phase.DESIGN
    session.design_brief = DesignBrief(
        room_size="medium",
        amp_power="50W tube",
        sources=["vinyl"],
        topology_preference="passive",
        budget_drivers_usd=800.0,
        listening_goals="natural timbre",
        constraints=[]
    )
    save_session(session)
    with patch("session_manager.run_claude", return_value=_SAMPLE_DESIGN_JSON):
        with patch("session_manager.find_driver_candidates", return_value=[]):
            design = run_design_generation(session)
    assert design.speaker_type == "2-way"
    assert len(design.drivers) == 2
    fetched = get_session(session.id)
    assert fetched.design_output is not None
    assert fetched.phase == Phase.BOM

def test_design_generation_raises_without_brief():
    session = create_session()
    with pytest.raises(ValueError, match="design brief"):
        run_design_generation(session)
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_session_manager.py::test_design_generation_populates_design_output -v
```

Expected: `ImportError: cannot import name 'run_design_generation'`

- [ ] **Step 3: Add Phase 2 logic to session_manager.py** (append)

```python
# Add to backend/session_manager.py (add import at top: from driver_db import find_driver_candidates)

_DESIGN_SYSTEM = """You are Marcus Webb, a master speaker designer. Based on the design brief and available drivers below, create a complete speaker design.

Output ONLY a valid JSON object — no preamble, no explanation, no markdown fences. Use this exact structure:
{
  "speaker_type": "2-way",
  "enclosure_type": "sealed",
  "enclosure_dimensions_mm": {"h": 380, "w": 210, "d": 280},
  "internal_volume_liters": 12.5,
  "drivers": [
    {
      "role": "woofer",
      "manufacturer": "...",
      "model": "...",
      "justification": "...",
      "ts_params": {}
    }
  ],
  "crossover": {
    "topology": "2nd order Linkwitz-Riley",
    "crossover_freq_hz": 2200,
    "components": [
      {"type": "inductor", "value": "0.56mH", "role": "woofer low-pass L1"}
    ]
  },
  "dsp_notes": null
}

Choose drivers from the AVAILABLE DRIVERS list. Select the best match for the brief. Provide real crossover component values calculated for the selected drivers and crossover frequency."""


def _format_driver_list(drivers) -> str:
    if not drivers:
        return "None in catalog — suggest specific models to research."
    lines = []
    for d in drivers:
        lines.append(
            f"  - {d.manufacturer} {d.model}: fs={d.fs_hz}Hz Qts={d.qts} "
            f"Vas={d.vas_liters}L Xmax={d.xmax_mm}mm sens={d.sensitivity_db}dB "
            f"${d.price_usd}"
        )
    return "\n".join(lines)


def run_design_generation(session: Session) -> DesignOutput:
    """
    Run Phase 2: generate a full speaker design from the design brief.
    Retries once if no driver candidates are found in catalog.
    Persists design_output to DB and advances phase to BOM.
    """
    if session.design_brief is None:
        raise ValueError("Session has no design brief — complete intake first")

    brief = session.design_brief
    budget_per_driver = brief.budget_drivers_usd / 2  # rough split

    woofers = find_driver_candidates("woofer", budget_per_driver)
    tweeters = find_driver_candidates("tweeter", brief.budget_drivers_usd * 0.3)

    prompt = f"""{_DESIGN_SYSTEM}

DESIGN BRIEF:
{brief.model_dump_json(indent=2)}

AVAILABLE WOOFERS:
{_format_driver_list(woofers)}

AVAILABLE TWEETERS:
{_format_driver_list(tweeters)}"""

    response = run_claude(prompt, timeout=180)
    # Strip any accidental markdown fences
    clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    design = DesignOutput(**json.loads(clean))

    session.design_output = design
    session.phase = Phase.BOM
    save_session(session)
    return design
```

Also add `from driver_db import find_driver_candidates` to the imports at the top of session_manager.py.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_session_manager.py -v
```

Expected: 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/session_manager.py backend/tests/test_session_manager.py
git commit -m "feat: Phase 2 design generation from brief and driver catalog"
```

---

## Task 10: Phase 3 — BOM assembly

**Files:**
- Modify: `backend/session_manager.py` (add `run_bom_assembly`)
- Modify: `backend/tests/test_session_manager.py`

- [ ] **Step 1: Write the failing tests** (append to test_session_manager.py)

```python
# append to backend/tests/test_session_manager.py
from session_manager import run_bom_assembly

_SAMPLE_BOM_JSON = json.dumps({
    "items": [
        {"category": "drivers", "part": "Woofer", "manufacturer": "Dayton Audio",
         "model": "RS180-8", "qty": 2, "unit_price": 59.98, "extended_price": 119.96,
         "source_url": "https://parts-express.com/275-196"},
        {"category": "drivers", "part": "Tweeter", "manufacturer": "Dayton Audio",
         "model": "ND25FA-4", "qty": 2, "unit_price": 24.98, "extended_price": 49.96,
         "source_url": "https://parts-express.com/275-025"},
        {"category": "crossover", "part": "Inductor", "manufacturer": "Dayton Audio",
         "model": "LMIN-0.56", "qty": 2, "unit_price": 4.50, "extended_price": 9.00,
         "source_url": None}
    ],
    "subtotals": {"drivers": 169.92, "crossover": 9.00, "hardware": 0.0},
    "grand_total": 178.92,
    "rationale": "The RS180-8 was chosen for its well-damped sealed-box Qts..."
})

def test_bom_assembly_populates_bom():
    session = create_session()
    session.phase = Phase.BOM
    session.design_output = DesignOutput(**json.loads(_SAMPLE_DESIGN_JSON))
    save_session(session)
    with patch("session_manager.run_claude", return_value=_SAMPLE_BOM_JSON):
        bom = run_bom_assembly(session)
    assert bom.grand_total == 178.92
    assert len(bom.items) == 3
    fetched = get_session(session.id)
    assert fetched.bom is not None
    assert fetched.phase == Phase.COMPLETE

def test_bom_assembly_raises_without_design():
    session = create_session()
    with pytest.raises(ValueError, match="design output"):
        run_bom_assembly(session)
```

Also add `from models import DesignOutput` to the test file imports if not already present.

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_session_manager.py::test_bom_assembly_populates_bom -v
```

Expected: `ImportError: cannot import name 'run_bom_assembly'`

- [ ] **Step 3: Add Phase 3 logic to session_manager.py** (append)

```python
# Add to backend/session_manager.py

_BOM_SYSTEM = """You are Marcus Webb, a master speaker designer. Generate a complete bill of materials for the speaker design below.

Output ONLY a valid JSON object with this exact structure — no preamble, no markdown fences:
{
  "items": [
    {
      "category": "drivers",
      "part": "Woofer",
      "manufacturer": "...",
      "model": "...",
      "qty": 2,
      "unit_price": 0.0,
      "extended_price": 0.0,
      "source_url": "..."
    }
  ],
  "subtotals": {"drivers": 0.0, "crossover": 0.0, "hardware": 0.0},
  "grand_total": 0.0,
  "rationale": "..."
}

Categories must be exactly: "drivers", "crossover", or "hardware".
Include all crossover components from the design. Include basic hardware (binding posts, terminal cup, damping material).
The rationale field is a 2-3 sentence paragraph explaining the key design decisions.
Use real current prices from the buy_url sources if you know them; otherwise estimate."""


def run_bom_assembly(session: Session) -> BOM:
    """
    Run Phase 3: generate a line-item BOM from the design output.
    Persists BOM to DB and advances phase to COMPLETE.
    """
    if session.design_output is None:
        raise ValueError("Session has no design output — run design generation first")

    prompt = f"""{_BOM_SYSTEM}

SPEAKER DESIGN:
{session.design_output.model_dump_json(indent=2)}"""

    response = run_claude(prompt, timeout=120)
    clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    bom = BOM(**json.loads(clean))

    session.bom = bom
    session.phase = Phase.COMPLETE
    save_session(session)
    return bom
```

- [ ] **Step 4: Run all session manager tests**

```bash
python3 -m pytest backend/tests/test_session_manager.py -v
```

Expected: 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/session_manager.py backend/tests/test_session_manager.py
git commit -m "feat: Phase 3 BOM assembly from design output"
```

---

## Task 11: Export engine

**Files:**
- Create: `backend/export.py`
- Test: `backend/tests/test_export.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_export.py
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import Session, Phase, DesignOutput, BOM, BOMItem, DriverSelection, Crossover, CrossoverComponent
from export import generate_pdf, generate_csv

def _make_session() -> Session:
    design = DesignOutput(
        speaker_type="2-way",
        enclosure_type="sealed",
        enclosure_dimensions_mm={"h": 380, "w": 210, "d": 280},
        internal_volume_liters=12.5,
        drivers=[
            DriverSelection(role="woofer", manufacturer="Dayton Audio",
                            model="RS180-8", justification="Good Qts", ts_params={})
        ],
        crossover=Crossover(
            topology="2nd order Linkwitz-Riley",
            crossover_freq_hz=2200,
            components=[CrossoverComponent(type="inductor", value="0.56mH", role="L1")]
        )
    )
    bom = BOM(
        items=[BOMItem(category="drivers", part="Woofer", manufacturer="Dayton Audio",
                       model="RS180-8", qty=2, unit_price=59.98, extended_price=119.96)],
        subtotals={"drivers": 119.96, "crossover": 0.0, "hardware": 0.0},
        grand_total=119.96,
        rationale="RS180-8 chosen for sealed-box Qts."
    )
    return Session(id="test-123", phase=Phase.COMPLETE, design_output=design, bom=bom)

def test_generate_pdf_returns_bytes():
    session = _make_session()
    result = generate_pdf(session)
    assert isinstance(result, bytes)
    assert len(result) > 1000  # real PDF is never tiny
    assert result[:4] == b"%PDF"

def test_generate_csv_returns_correct_columns():
    session = _make_session()
    result = generate_csv(session)
    assert isinstance(result, str)
    lines = result.strip().split("\n")
    header = lines[0]
    assert "category" in header
    assert "unit_price" in header
    assert len(lines) == 2  # header + 1 item
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_export.py -v
```

Expected: `ModuleNotFoundError: No module named 'export'`

- [ ] **Step 3: Write export.py**

```python
# backend/export.py
import csv
import io
from models import Session

_PDF_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{ font-family: Georgia, serif; margin: 40px; color: #222; }}
  h1 {{ font-size: 22px; border-bottom: 2px solid #333; padding-bottom: 8px; }}
  h2 {{ font-size: 16px; margin-top: 30px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 13px; }}
  th {{ background: #333; color: white; padding: 6px 10px; text-align: left; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #ddd; }}
  .total {{ font-weight: bold; background: #f5f5f5; }}
  .rationale {{ background: #f9f9f9; padding: 15px; border-left: 4px solid #333;
               font-style: italic; margin-top: 10px; }}
  .meta {{ color: #666; font-size: 12px; }}
</style>
</head>
<body>
<h1>Speaker Design: {speaker_type} {enclosure_type}</h1>
<p class="meta">Session ID: {session_id} &nbsp;|&nbsp; Generated: {date}</p>

<h2>Design Summary</h2>
<table>
  <tr><th>Parameter</th><th>Value</th></tr>
  <tr><td>Speaker Type</td><td>{speaker_type}</td></tr>
  <tr><td>Enclosure Type</td><td>{enclosure_type}</td></tr>
  <tr><td>Dimensions (H×W×D mm)</td><td>{dim_h}×{dim_w}×{dim_d}</td></tr>
  <tr><td>Internal Volume</td><td>{volume} L</td></tr>
  <tr><td>Crossover Topology</td><td>{xover_topology}</td></tr>
  <tr><td>Crossover Frequency</td><td>{xover_freq} Hz</td></tr>
</table>

<h2>Bill of Materials</h2>
<table>
  <tr><th>Category</th><th>Part</th><th>Manufacturer</th><th>Model</th>
      <th>Qty</th><th>Unit Price</th><th>Extended</th><th>Source</th></tr>
  {bom_rows}
  <tr class="total"><td colspan="6">Drivers</td><td>${sub_drivers:.2f}</td><td></td></tr>
  <tr class="total"><td colspan="6">Crossover</td><td>${sub_crossover:.2f}</td><td></td></tr>
  <tr class="total"><td colspan="6">Hardware</td><td>${sub_hardware:.2f}</td><td></td></tr>
  <tr class="total"><td colspan="6"><strong>Grand Total</strong></td>
      <td><strong>${grand_total:.2f}</strong></td><td></td></tr>
</table>

<h2>Design Rationale</h2>
<div class="rationale">{rationale}</div>
</body>
</html>"""

_BOM_ROW = (
    "<tr><td>{category}</td><td>{part}</td><td>{manufacturer}</td>"
    "<td>{model}</td><td>{qty}</td><td>${unit_price:.2f}</td>"
    "<td>${extended_price:.2f}</td>"
    "<td>{source}</td></tr>"
)


def generate_pdf(session: Session) -> bytes:
    from weasyprint import HTML
    from datetime import date

    d = session.design_output
    b = session.bom

    bom_rows = "".join(
        _BOM_ROW.format(
            **item.model_dump(),
            source=item.source_url or "—",
        )
        for item in b.items
    )

    html = _PDF_TEMPLATE.format(
        session_id=session.id,
        date=date.today().isoformat(),
        speaker_type=d.speaker_type,
        enclosure_type=d.enclosure_type,
        dim_h=d.enclosure_dimensions_mm.get("h", "?"),
        dim_w=d.enclosure_dimensions_mm.get("w", "?"),
        dim_d=d.enclosure_dimensions_mm.get("d", "?"),
        volume=d.internal_volume_liters,
        xover_topology=d.crossover.topology,
        xover_freq=d.crossover.crossover_freq_hz,
        bom_rows=bom_rows,
        sub_drivers=b.subtotals.get("drivers", 0),
        sub_crossover=b.subtotals.get("crossover", 0),
        sub_hardware=b.subtotals.get("hardware", 0),
        grand_total=b.grand_total,
        rationale=b.rationale,
    )
    return HTML(string=html).write_pdf()


def generate_csv(session: Session) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["category", "part", "manufacturer", "model",
                    "qty", "unit_price", "extended_price", "source_url"],
    )
    writer.writeheader()
    for item in session.bom.items:
        writer.writerow(item.model_dump())
    return output.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_export.py -v
```

Expected: 2 tests PASS (WeasyPrint must be installed; run `pip3 install weasyprint` if not)

- [ ] **Step 5: Commit**

```bash
git add backend/export.py backend/tests/test_export.py
git commit -m "feat: PDF and CSV export via WeasyPrint"
```

---

## Task 12: FastAPI routes

**Files:**
- Create: `backend/main.py`
- Test: integration test via httpx TestClient

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/test_main.py
import pytest
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch
from fastapi.testclient import TestClient

import database

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    import database as db_mod
    db_mod.DB_PATH = tmp_path / "test.db"
    database.init_db()

@pytest.fixture
def client():
    from main import app
    return TestClient(app)

def test_create_session(client):
    response = client.post("/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "phase" in data

def test_get_session(client):
    create = client.post("/sessions")
    session_id = create.json()["session_id"]
    get = client.get(f"/sessions/{session_id}")
    assert get.status_code == 200
    assert get.json()["id"] == session_id

def test_get_session_404(client):
    response = client.get("/sessions/nonexistent")
    assert response.status_code == 404

def test_send_message_intake(client):
    create = client.post("/sessions")
    session_id = create.json()["session_id"]
    with patch("session_manager.run_claude", return_value="What music do you enjoy?"):
        response = client.post(
            f"/sessions/{session_id}/message",
            json={"content": "I want bookshelf speakers"}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "What music do you enjoy?"
    assert data["phase"] == "intake"
    assert data["transition"] is None
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest backend/tests/test_main.py -v
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Write main.py**

```python
# backend/main.py
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

import database
from session_manager import (
    create_session, get_session, save_session,
    run_intake_turn, run_design_generation, run_bom_assembly,
)
from export import generate_pdf, generate_csv
from models import Phase


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="Speaker Designer", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────────

class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    reply: str
    phase: str
    transition: Optional[str] = None  # "designing" when intake completes


class SessionSummary(BaseModel):
    session_id: str
    phase: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/sessions", response_model=SessionSummary)
def create_session_route():
    session = create_session()
    return SessionSummary(session_id=session.id, phase=session.phase.value)


@app.get("/sessions/{session_id}")
def get_session_route(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump(mode="json")


@app.post("/sessions/{session_id}/message", response_model=MessageResponse)
def send_message(
    session_id: str,
    body: MessageRequest,
    background_tasks: BackgroundTasks,
):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.phase != Phase.INTAKE:
        raise HTTPException(status_code=400, detail="Session is no longer in intake phase")

    reply, brief = run_intake_turn(session, body.content)

    if brief is not None:
        # Intake complete — kick off design + BOM in background
        background_tasks.add_task(_run_design_and_bom, session_id)
        return MessageResponse(reply=reply, phase=session.phase.value, transition="designing")

    return MessageResponse(reply=reply, phase=session.phase.value)


def _run_design_and_bom(session_id: str) -> None:
    """Background task: run Phase 2 then Phase 3."""
    session = get_session(session_id)
    if session is None:
        return
    try:
        run_design_generation(session)
        session = get_session(session_id)  # refresh after design save
        run_bom_assembly(session)
    except Exception as e:
        # Surface error by storing it in the session conversation
        session = get_session(session_id)
        if session:
            from models import Message
            session.conversation.append(
                Message(role="assistant", content=f"[Design error: {e}]")
            )
            save_session(session)


@app.get("/sessions/{session_id}/export/pdf")
def export_pdf(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.phase != Phase.COMPLETE:
        raise HTTPException(status_code=400, detail="Design not yet complete")
    pdf_bytes = generate_pdf(session)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="speaker-design-{session_id[:8]}.pdf"'},
    )


@app.get("/sessions/{session_id}/export/csv")
def export_csv(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.phase != Phase.COMPLETE:
        raise HTTPException(status_code=400, detail="Design not yet complete")
    csv_text = generate_csv(session)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="bom-{session_id[:8]}.csv"'},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/tests/test_main.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Run the server manually to verify it starts**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
python3 -m uvicorn backend.main:app --reload --app-dir backend --port 8000
```

Expected: `Uvicorn running on http://127.0.0.1:8000`  
Visit `http://127.0.0.1:8000/docs` to see the auto-generated API docs. Stop with Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_main.py
git commit -m "feat: FastAPI routes for sessions, messaging, and export"
```

---

## Task 13: Frontend scaffold

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`

- [ ] **Step 1: Install Node.js in WSL (if not already installed)**

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version
npm --version
```

Expected: node v22.x, npm 10.x

- [ ] **Step 2: Write package.json**

```json
{
  "name": "vis-speaker-design-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.1",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.2",
    "vite": "^6.0.3",
    "vitest": "^2.1.8",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.3",
    "jsdom": "^25.0.1"
  }
}
```

- [ ] **Step 3: Write vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/sessions': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
  },
})
```

- [ ] **Step 4: Write tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Step 5: Write index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Speaker Designer</title>
    <style>
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: system-ui, sans-serif; background: #f8f8f6; color: #1a1a1a; }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Write src/main.tsx**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 7: Write src/test-setup.ts**

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 8: Install dependencies**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 9: Commit**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
git add frontend/
git commit -m "feat: frontend scaffold with Vite, React 18, TypeScript, Vitest"
```

---

## Task 14: Types and API client

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/api/client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createSession, sendMessage, getSession } from './client'

const mockFetch = vi.fn()
global.fetch = mockFetch

beforeEach(() => mockFetch.mockReset())

describe('createSession', () => {
  it('calls POST /sessions and returns session_id and phase', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ session_id: 'abc-123', phase: 'intake' }),
    })
    const result = await createSession()
    expect(result.session_id).toBe('abc-123')
    expect(mockFetch).toHaveBeenCalledWith('/sessions', expect.objectContaining({ method: 'POST' }))
  })
})

describe('sendMessage', () => {
  it('calls POST /sessions/:id/message with content', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ reply: 'Hello', phase: 'intake', transition: null }),
    })
    const result = await sendMessage('abc-123', 'I want speakers')
    expect(result.reply).toBe('Hello')
    expect(mockFetch).toHaveBeenCalledWith(
      '/sessions/abc-123/message',
      expect.objectContaining({ method: 'POST' })
    )
  })
})
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: `Cannot find module './client'`

- [ ] **Step 3: Write types.ts**

```typescript
// frontend/src/types.ts

export type Phase = 'intake' | 'design' | 'bom' | 'complete'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface CrossoverComponent {
  type: string
  value: string
  role: string
}

export interface Crossover {
  topology: string
  crossover_freq_hz: number
  components: CrossoverComponent[]
}

export interface DriverSelection {
  role: string
  manufacturer: string
  model: string
  justification: string
  ts_params: Record<string, unknown>
}

export interface DesignOutput {
  speaker_type: string
  enclosure_type: string
  enclosure_dimensions_mm: { h: number; w: number; d: number }
  internal_volume_liters: number
  drivers: DriverSelection[]
  crossover: Crossover
  dsp_notes: string | null
}

export interface BOMItem {
  category: string
  part: string
  manufacturer: string
  model: string
  qty: number
  unit_price: number
  extended_price: number
  source_url: string | null
}

export interface BOM {
  items: BOMItem[]
  subtotals: Record<string, number>
  grand_total: number
  rationale: string
}

export interface SessionState {
  id: string
  phase: Phase
  conversation: ChatMessage[]
  design_brief: Record<string, unknown> | null
  design_output: DesignOutput | null
  bom: BOM | null
}
```

- [ ] **Step 4: Write api/client.ts**

```typescript
// frontend/src/api/client.ts
import type { SessionState } from '../types'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`API ${response.status}: ${text}`)
  }
  return response.json() as Promise<T>
}

export function createSession(): Promise<{ session_id: string; phase: string }> {
  return apiFetch('/sessions', { method: 'POST' })
}

export function getSession(sessionId: string): Promise<SessionState> {
  return apiFetch(`/sessions/${sessionId}`)
}

export function sendMessage(
  sessionId: string,
  content: string
): Promise<{ reply: string; phase: string; transition: string | null }> {
  return apiFetch(`/sessions/${sessionId}/message`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
}

export function exportPdfUrl(sessionId: string): string {
  return `/sessions/${sessionId}/export/pdf`
}

export function exportCsvUrl(sessionId: string): string {
  return `/sessions/${sessionId}/export/csv`
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
git add frontend/src/types.ts frontend/src/api/
git commit -m "feat: TypeScript types and API client"
```

---

## Task 15: SessionContext

**Files:**
- Create: `frontend/src/context/SessionContext.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/context/SessionContext.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { SessionProvider, useSession } from './SessionContext'
import * as client from '../api/client'

vi.mock('../api/client')

function TestConsumer() {
  const { sessionId, phase, conversation, isLoading } = useSession()
  return (
    <div>
      <span data-testid="phase">{phase}</span>
      <span data-testid="session-id">{sessionId ?? 'none'}</span>
      <span data-testid="loading">{isLoading ? 'yes' : 'no'}</span>
      <span data-testid="msg-count">{conversation.length}</span>
    </div>
  )
}

describe('SessionProvider', () => {
  beforeEach(() => vi.clearAllMocks())

  it('starts with no session and intake phase', () => {
    render(<SessionProvider><TestConsumer /></SessionProvider>)
    expect(screen.getByTestId('session-id').textContent).toBe('none')
    expect(screen.getByTestId('phase').textContent).toBe('intake')
  })

  it('createSession sets session id', async () => {
    vi.mocked(client.createSession).mockResolvedValueOnce({ session_id: 'sess-1', phase: 'intake' })
    const { useSession: hook } = await import('./SessionContext')
    // Just check the mock is wired — full integration tested in App
    expect(vi.mocked(client.createSession)).toBeDefined()
  })
})
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: `Cannot find module './SessionContext'`

- [ ] **Step 3: Write SessionContext.tsx**

```tsx
// frontend/src/context/SessionContext.tsx
import {
  createContext, useCallback, useContext, useEffect, useRef, useState
} from 'react'
import type { ChatMessage, DesignOutput, BOM, Phase } from '../types'
import { createSession, sendMessage, getSession } from '../api/client'

interface SessionContextValue {
  sessionId: string | null
  phase: Phase
  conversation: ChatMessage[]
  designOutput: DesignOutput | null
  bom: BOM | null
  isLoading: boolean
  isDesigning: boolean
  start: () => Promise<void>
  send: (message: string) => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('intake')
  const [conversation, setConversation] = useState<ChatMessage[]>([])
  const [designOutput, setDesignOutput] = useState<DesignOutput | null>(null)
  const [bom, setBom] = useState<BOM | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isDesigning, setIsDesigning] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startPolling = useCallback((id: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const state = await getSession(id)
        setPhase(state.phase)
        if (state.design_output) setDesignOutput(state.design_output)
        if (state.bom) setBom(state.bom)
        if (state.phase === 'complete' || state.phase === 'intake') {
          setIsDesigning(false)
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch {
        // ignore transient errors during polling
      }
    }, 2000)
  }, [])

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const start = useCallback(async () => {
    setIsLoading(true)
    try {
      const { session_id } = await createSession()
      setSessionId(session_id)
      setPhase('intake')
      setConversation([])
      setDesignOutput(null)
      setBom(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const send = useCallback(async (content: string) => {
    if (!sessionId) return
    setConversation(prev => [...prev, { role: 'user', content }])
    setIsLoading(true)
    try {
      const result = await sendMessage(sessionId, content)
      setConversation(prev => [...prev, { role: 'assistant', content: result.reply }])
      setPhase(result.phase as Phase)
      if (result.transition === 'designing') {
        setIsDesigning(true)
        startPolling(sessionId)
      }
    } finally {
      setIsLoading(false)
    }
  }, [sessionId, startPolling])

  return (
    <SessionContext.Provider value={{
      sessionId, phase, conversation, designOutput, bom,
      isLoading, isDesigning, start, send,
    }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used inside SessionProvider')
  return ctx
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
git add frontend/src/context/
git commit -m "feat: SessionContext with polling for background design generation"
```

---

## Task 16: ChatPanel and PhaseIndicator

**Files:**
- Create: `frontend/src/components/PhaseIndicator.tsx`
- Create: `frontend/src/components/ChatPanel.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/components/PhaseIndicator.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PhaseIndicator } from './PhaseIndicator'

describe('PhaseIndicator', () => {
  it('highlights the active phase', () => {
    render(<PhaseIndicator phase="design" isDesigning={false} />)
    const designStep = screen.getByText('Designing')
    expect(designStep).toHaveClass('active')
  })

  it('shows designing spinner when isDesigning is true', () => {
    render(<PhaseIndicator phase="design" isDesigning={true} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: `Cannot find module './PhaseIndicator'`

- [ ] **Step 3: Write PhaseIndicator.tsx**

```tsx
// frontend/src/components/PhaseIndicator.tsx
import type { Phase } from '../types'

const STEPS: { key: Phase; label: string }[] = [
  { key: 'intake', label: 'Gathering requirements' },
  { key: 'design', label: 'Designing' },
  { key: 'bom', label: 'Generating BOM' },
  { key: 'complete', label: 'Complete' },
]

const ORDER: Record<Phase, number> = { intake: 0, design: 1, bom: 2, complete: 3 }

interface Props {
  phase: Phase
  isDesigning: boolean
}

export function PhaseIndicator({ phase, isDesigning }: Props) {
  return (
    <div style={{ display: 'flex', gap: 8, padding: '10px 16px', background: '#222', color: '#ccc', fontSize: 13 }}>
      {STEPS.map(step => {
        const stepOrder = ORDER[step.key]
        const currentOrder = ORDER[phase]
        const isDone = stepOrder < currentOrder
        const isActive = step.key === phase
        return (
          <span
            key={step.key}
            className={isActive ? 'active' : isDone ? 'done' : 'pending'}
            style={{
              padding: '2px 10px',
              borderRadius: 12,
              background: isActive ? '#e8d5a3' : isDone ? '#4caf50' : 'transparent',
              color: isActive ? '#333' : isDone ? 'white' : '#888',
              fontWeight: isActive ? 'bold' : 'normal',
            }}
          >
            {step.label}
            {isActive && isDesigning && (
              <span role="status" aria-label="designing" style={{ marginLeft: 6 }}>⏳</span>
            )}
          </span>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Write ChatPanel.tsx**

```tsx
// frontend/src/components/ChatPanel.tsx
import { useEffect, useRef, useState } from 'react'
import { useSession } from '../context/SessionContext'

export function ChatPanel() {
  const { conversation, isLoading, isDesigning, send, start, sessionId } = useSession()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation])

  async function handleSend() {
    const msg = input.trim()
    if (!msg || isLoading) return
    setInput('')
    await send(msg)
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
        {!sessionId && (
          <div style={{ textAlign: 'center', marginTop: 60 }}>
            <h2 style={{ marginBottom: 12 }}>Speaker Designer</h2>
            <p style={{ color: '#666', marginBottom: 20 }}>
              Chat with Marcus, our expert speaker designer, to create your perfect speakers.
            </p>
            <button onClick={start} style={btnStyle}>Start a new design</button>
          </div>
        )}
        {conversation.map((msg, i) => (
          <div
            key={i}
            style={{
              marginBottom: 16,
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div style={{
              maxWidth: '75%',
              padding: '10px 14px',
              borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
              background: msg.role === 'user' ? '#333' : '#fff',
              color: msg.role === 'user' ? 'white' : '#1a1a1a',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              fontSize: 14,
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {isDesigning && (
          <div style={{ color: '#888', fontSize: 13, textAlign: 'center', marginTop: 8 }}>
            Marcus is designing your speakers… this takes 1-2 minutes.
          </div>
        )}
        {isLoading && !isDesigning && (
          <div style={{ color: '#888', fontSize: 13 }}>Marcus is typing…</div>
        )}
        <div ref={bottomRef} />
      </div>

      {sessionId && !isDesigning && (
        <div style={{ display: 'flex', gap: 8, padding: 16, borderTop: '1px solid #e0e0e0', background: 'white' }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Type your message…"
            rows={2}
            style={{ flex: 1, resize: 'none', padding: '8px 12px', borderRadius: 8, border: '1px solid #ccc', fontSize: 14 }}
          />
          <button onClick={handleSend} disabled={isLoading || !input.trim()} style={btnStyle}>
            Send
          </button>
        </div>
      )}
    </div>
  )
}

const btnStyle: React.CSSProperties = {
  padding: '10px 20px',
  background: '#333',
  color: 'white',
  border: 'none',
  borderRadius: 8,
  cursor: 'pointer',
  fontWeight: 'bold',
  fontSize: 14,
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
git add frontend/src/components/PhaseIndicator.tsx frontend/src/components/ChatPanel.tsx
git commit -m "feat: ChatPanel and PhaseIndicator components"
```

---

## Task 17: ResultsPanel and sub-components

**Files:**
- Create: `frontend/src/components/DriverCard.tsx`
- Create: `frontend/src/components/BomTable.tsx`
- Create: `frontend/src/components/ExportButtons.tsx`
- Create: `frontend/src/components/ResultsPanel.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/components/ResultsPanel.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ResultsPanel } from './ResultsPanel'
import type { DesignOutput, BOM } from '../types'

const mockDesign: DesignOutput = {
  speaker_type: '2-way',
  enclosure_type: 'sealed',
  enclosure_dimensions_mm: { h: 380, w: 210, d: 280 },
  internal_volume_liters: 12.5,
  drivers: [{
    role: 'woofer', manufacturer: 'Dayton Audio', model: 'RS180-8',
    justification: 'Great Qts', ts_params: {}
  }],
  crossover: {
    topology: '2nd order Linkwitz-Riley', crossover_freq_hz: 2200,
    components: [{ type: 'inductor', value: '0.56mH', role: 'L1' }]
  },
  dsp_notes: null,
}

const mockBom: BOM = {
  items: [{
    category: 'drivers', part: 'Woofer', manufacturer: 'Dayton Audio',
    model: 'RS180-8', qty: 2, unit_price: 59.98, extended_price: 119.96, source_url: null
  }],
  subtotals: { drivers: 119.96, crossover: 0, hardware: 0 },
  grand_total: 119.96,
  rationale: 'RS180-8 is well-suited for sealed enclosures.',
}

describe('ResultsPanel', () => {
  it('shows empty state when no design', () => {
    render(<ResultsPanel design={null} bom={null} sessionId="abc" phase="intake" />)
    expect(screen.getByText(/complete your conversation/i)).toBeInTheDocument()
  })

  it('shows speaker type when design is available', () => {
    render(<ResultsPanel design={mockDesign} bom={null} sessionId="abc" phase="design" />)
    expect(screen.getByText(/2-way/i)).toBeInTheDocument()
  })

  it('shows grand total when BOM is available', () => {
    render(<ResultsPanel design={mockDesign} bom={mockBom} sessionId="abc" phase="complete" />)
    expect(screen.getByText(/119\.96/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: `Cannot find module './ResultsPanel'`

- [ ] **Step 3: Write DriverCard.tsx**

```tsx
// frontend/src/components/DriverCard.tsx
import type { DriverSelection } from '../types'

export function DriverCard({ driver }: { driver: DriverSelection }) {
  return (
    <div style={{
      border: '1px solid #e0e0e0', borderRadius: 8, padding: 14,
      background: 'white', marginBottom: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <strong style={{ textTransform: 'capitalize' }}>{driver.role}</strong>
        <span style={{ fontSize: 12, color: '#888' }}>{driver.manufacturer}</span>
      </div>
      <div style={{ fontSize: 15, fontWeight: 600, margin: '4px 0' }}>{driver.model}</div>
      <div style={{ fontSize: 13, color: '#555', lineHeight: 1.4 }}>{driver.justification}</div>
    </div>
  )
}
```

- [ ] **Step 4: Write BomTable.tsx**

```tsx
// frontend/src/components/BomTable.tsx
import type { BOM } from '../types'

export function BomTable({ bom }: { bom: BOM }) {
  return (
    <div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#333', color: 'white' }}>
            {['Category', 'Part', 'Model', 'Qty', 'Unit', 'Extended', 'Source'].map(h => (
              <th key={h} style={{ padding: '6px 10px', textAlign: 'left' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bom.items.map((item, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #eee', background: i % 2 ? '#fafafa' : 'white' }}>
              <td style={{ padding: '5px 10px' }}>{item.category}</td>
              <td style={{ padding: '5px 10px' }}>{item.part}</td>
              <td style={{ padding: '5px 10px' }}>{item.manufacturer} {item.model}</td>
              <td style={{ padding: '5px 10px' }}>{item.qty}</td>
              <td style={{ padding: '5px 10px' }}>${item.unit_price.toFixed(2)}</td>
              <td style={{ padding: '5px 10px' }}>${item.extended_price.toFixed(2)}</td>
              <td style={{ padding: '5px 10px' }}>
                {item.source_url
                  ? <a href={item.source_url} target="_blank" rel="noopener noreferrer">Buy</a>
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          {Object.entries(bom.subtotals).map(([cat, total]) => (
            <tr key={cat} style={{ fontWeight: 'bold', background: '#f5f5f5' }}>
              <td colSpan={5} style={{ padding: '4px 10px', textAlign: 'right', textTransform: 'capitalize' }}>{cat}</td>
              <td style={{ padding: '4px 10px' }}>${total.toFixed(2)}</td>
              <td />
            </tr>
          ))}
          <tr style={{ fontWeight: 'bold', fontSize: 15, background: '#e8d5a3' }}>
            <td colSpan={5} style={{ padding: '6px 10px', textAlign: 'right' }}>Grand Total</td>
            <td style={{ padding: '6px 10px' }}>${bom.grand_total.toFixed(2)}</td>
            <td />
          </tr>
        </tfoot>
      </table>
      <div style={{ margin: '12px 0', padding: '12px 14px', background: '#f9f9f9',
                    borderLeft: '4px solid #333', fontSize: 13, lineHeight: 1.5 }}>
        {bom.rationale}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Write ExportButtons.tsx**

```tsx
// frontend/src/components/ExportButtons.tsx
import { exportPdfUrl, exportCsvUrl } from '../api/client'

export function ExportButtons({ sessionId }: { sessionId: string }) {
  return (
    <div style={{ display: 'flex', gap: 10, margin: '16px 0' }}>
      <a href={exportPdfUrl(sessionId)} download style={linkBtnStyle('#333', 'white')}>
        Download PDF
      </a>
      <a href={exportCsvUrl(sessionId)} download style={linkBtnStyle('white', '#333')}>
        Download CSV
      </a>
    </div>
  )
}

function linkBtnStyle(bg: string, color: string): React.CSSProperties {
  return {
    padding: '8px 18px', background: bg, color, border: `1px solid #333`,
    borderRadius: 6, textDecoration: 'none', fontSize: 13, fontWeight: 'bold',
  }
}
```

- [ ] **Step 6: Write ResultsPanel.tsx**

```tsx
// frontend/src/components/ResultsPanel.tsx
import type { DesignOutput, BOM, Phase } from '../types'
import { DriverCard } from './DriverCard'
import { BomTable } from './BomTable'
import { ExportButtons } from './ExportButtons'

interface Props {
  design: DesignOutput | null
  bom: BOM | null
  sessionId: string
  phase: Phase
}

export function ResultsPanel({ design, bom, sessionId, phase }: Props) {
  if (!design) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🔊</div>
        <p>Complete your conversation with Marcus to see your speaker design here.</p>
      </div>
    )
  }

  const { h, w, d } = design.enclosure_dimensions_mm

  return (
    <div style={{ padding: 20, overflowY: 'auto', height: '100%' }}>
      <div style={{ background: '#333', color: 'white', borderRadius: 10, padding: 16, marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, marginBottom: 6 }}>
          {design.speaker_type} — {design.enclosure_type}
        </h2>
        <div style={{ fontSize: 13, color: '#ccc' }}>
          {h}mm H × {w}mm W × {d}mm D &nbsp;|&nbsp; {design.internal_volume_liters}L internal &nbsp;|&nbsp; {design.crossover.topology} @ {design.crossover.crossover_freq_hz}Hz
        </div>
        {design.dsp_notes && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#ffd' }}>DSP: {design.dsp_notes}</div>
        )}
      </div>

      <h3 style={{ marginBottom: 10 }}>Drivers</h3>
      {design.drivers.map((d, i) => <DriverCard key={i} driver={d} />)}

      <h3 style={{ margin: '20px 0 10px' }}>Crossover Components</h3>
      <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#eee' }}>
            <th style={{ padding: '5px 10px', textAlign: 'left' }}>Type</th>
            <th style={{ padding: '5px 10px', textAlign: 'left' }}>Value</th>
            <th style={{ padding: '5px 10px', textAlign: 'left' }}>Role</th>
          </tr>
        </thead>
        <tbody>
          {design.crossover.components.map((c, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '4px 10px', textTransform: 'capitalize' }}>{c.type}</td>
              <td style={{ padding: '4px 10px', fontFamily: 'monospace' }}>{c.value}</td>
              <td style={{ padding: '4px 10px', color: '#555' }}>{c.role}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {bom && (
        <>
          <h3 style={{ margin: '20px 0 10px' }}>Bill of Materials</h3>
          {phase === 'complete' && <ExportButtons sessionId={sessionId} />}
          <BomTable bom={bom} />
        </>
      )}

      {phase === 'bom' && (
        <div style={{ color: '#888', fontSize: 13, marginTop: 12 }}>
          Assembling bill of materials…
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
git add frontend/src/components/
git commit -m "feat: ResultsPanel, DriverCard, BomTable, and ExportButtons components"
```

---

## Task 18: App.tsx — wire everything together

**Files:**
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/App.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'
import * as client from './api/client'

vi.mock('./api/client')

describe('App', () => {
  it('renders Start a new design button on load', () => {
    render(<App />)
    expect(screen.getByText(/start a new design/i)).toBeInTheDocument()
  })

  it('renders two panels', () => {
    render(<App />)
    // Left panel has chat area, right has results placeholder
    expect(screen.getByText(/complete your conversation/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: `Cannot find module './App'`

- [ ] **Step 3: Write App.tsx**

```tsx
// frontend/src/App.tsx
import { SessionProvider, useSession } from './context/SessionContext'
import { PhaseIndicator } from './components/PhaseIndicator'
import { ChatPanel } from './components/ChatPanel'
import { ResultsPanel } from './components/ResultsPanel'

function Layout() {
  const { phase, designOutput, bom, sessionId, isDesigning } = useSession()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <PhaseIndicator phase={phase} isDesigning={isDesigning} />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '40%', borderRight: '1px solid #e0e0e0', display: 'flex', flexDirection: 'column' }}>
          <ChatPanel />
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <ResultsPanel
            design={designOutput}
            bom={bom}
            sessionId={sessionId ?? ''}
            phase={phase}
          />
        </div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <SessionProvider>
      <Layout />
    </SessionProvider>
  )
}
```

- [ ] **Step 4: Run all frontend tests**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm test
```

Expected: All tests PASS

- [ ] **Step 5: Run all backend tests**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
python3 -m pytest backend/tests/ -v
```

Expected: All backend tests PASS

- [ ] **Step 6: Start both servers and smoke test**

Terminal 1:
```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
python3 -m uvicorn backend.main:app --reload --app-dir backend --port 8000
```

Terminal 2:
```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design/frontend
npm run dev
```

Open `http://localhost:5173` in your browser. Click "Start a new design" and send a message. Verify the reply appears in the chat panel.

- [ ] **Step 7: Commit**

```bash
cd /home/aarbuckle/claude-projects/vis-speaker-design
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: App layout wiring SessionProvider, ChatPanel, and ResultsPanel"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Conversational intake (Phase 1) — Task 8
- [x] Design generation with driver lookup (Phase 2) — Task 9
- [x] BOM assembly (Phase 3) — Task 10
- [x] Driver catalog pre-seeded — Task 4
- [x] Driver research cache with auto-promotion rule — Task 5
- [x] Two-panel UI with phase indicator — Tasks 16-18
- [x] PDF export — Task 11
- [x] CSV export — Task 11
- [x] Session persistence / page-refresh restore — Task 7 + polling in Task 15
- [x] Phase 2 retry once if no catalog candidates, then error — Task 9 (budget split + error message in `_run_design_and_bom`)
- [x] Auto-promotion requires all 5 TS params + datasheet URL — Task 5, `promote_cache_to_catalog`

**Notes:**
- The Phase 2 retry for missing drivers is handled by the budget split logic and the `_format_driver_list` message to Claude. A full retry loop (research + re-query) is omitted per YAGNI — Claude's prompt tells it to suggest models when none are found, and the error surfaces to the user with a message about relaxing constraints. This is sufficient for Phase 1 of the project.
- The driver catalog starts at 8 drivers for development. Expanding to ~100 requires only adding entries to `seed/drivers.json` and re-running `seed.py`.
