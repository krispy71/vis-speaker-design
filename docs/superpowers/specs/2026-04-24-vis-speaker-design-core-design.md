# vis-speaker-design: Core Design Spec
**Date:** 2026-04-24
**Scope:** Phase 1 — User intake through BOM output (excludes photo-realistic rendering and aesthetic design tool)

---

## Overview

A web-based speaker design application that guides users from a natural conversation about their listening goals to a complete speaker design with bill of materials. Claude (via CLI subprocess) acts as an experienced speaker designer, handling the full intake interview, making all technical design decisions, and generating the BOM. Python/FastAPI orchestrates the session and handles storage; React provides the UI.

---

## Architecture

```
React Frontend
     │  HTTP (REST)
     ▼
FastAPI Backend
     ├── Session Manager  (conversation history, phase state)
     ├── Claude Runner    (subprocess: claude -p)
     ├── Driver DB        (SQLite + pre-seeded catalog)
     └── Export Engine    (PDF via WeasyPrint, CSV)
```

- **React** — single-page app with a chat panel and a results panel
- **FastAPI** — thin orchestrator; routes messages to Claude, manages phase transitions, reads/writes driver DB
- **Claude CLI** — invoked as a subprocess (`claude -p`) per phase with a tailored system prompt; no API key required (uses Pro subscription auth)
- **SQLite** — stores driver catalog (TS params, pricing), design sessions, and generated BOMs
- **WeasyPrint** — server-side PDF generation from HTML/CSS templates

---

## Phase-Based Conversation Flow

The session is divided into three phases. Each phase is a distinct Claude subprocess call pattern. Phase outputs are stored in SQLite, making each phase independently retryable without restarting the session.

### Phase 1 — Intake (multi-turn)

Claude plays the role of an experienced speaker designer interviewing the user. The system prompt establishes the persona and instructs Claude to ask one question at a time, covering:

- Listening goals and music preferences
- Room size and listening position
- Existing amplifier specs (power, topology)
- Source material (vinyl, streaming, CD)
- Passive / active / bi-amped preference
- Budget (drivers + crossover components)
- Aesthetic constraints (size, finish, WAF)

When Claude has sufficient information, it signals completion with `<<INTAKE_COMPLETE>>` followed by a structured JSON design brief:

```json
{
  "room_size": "medium (15x20ft)",
  "amp_power": "50W/ch tube",
  "sources": ["vinyl", "streaming"],
  "topology_preference": "passive",
  "budget_drivers_usd": 800,
  "listening_goals": "natural timbre, jazz and acoustic",
  "constraints": ["slim profile preferred"]
}
```

FastAPI detects the completion token, extracts the JSON, and transitions to Phase 2.

### Phase 2 — Design Generation (single-turn)

FastAPI queries the driver database for candidates matching the design brief (by driver type, diameter range, sensitivity, and price). Up to 5 candidates per driver role are passed to Claude as context alongside the design brief. Claude outputs a full design as structured JSON:

```json
{
  "speaker_type": "2-way",
  "enclosure_type": "sealed",
  "enclosure_dimensions_mm": {"h": 380, "w": 210, "d": 280},
  "internal_volume_liters": 12.5,
  "drivers": [
    {
      "role": "woofer",
      "model": "Dayton Audio RS180-8",
      "justification": "...",
      "ts_params": {...}
    },
    {
      "role": "tweeter",
      "model": "ScanSpeak D2608/913000",
      "justification": "...",
      "ts_params": {...}
    }
  ],
  "crossover": {
    "topology": "2nd order Linkwitz-Riley",
    "crossover_freq_hz": 2200,
    "components": [...]
  },
  "dsp_notes": null
}
```

If no suitable driver candidates exist in the catalog, Claude is prompted to suggest specific models to research. FastAPI fetches those via a secondary Claude web-research call, caches results in `driver_search_cache`, and retries Phase 2 once. If the retry also yields no usable candidates, FastAPI returns an error to the frontend prompting the user to relax their budget or size constraints.

### Phase 3 — BOM Assembly (single-turn)

Claude receives the design JSON and generates a line-item BOM covering drivers, crossover components, hardware, and enclosure materials. Output includes part numbers, quantities, unit prices, and sourcing links where known.

---

## Driver Database

SQLite with two tables:

### `drivers` — pre-seeded catalog

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| manufacturer | TEXT | Dayton, ScanSpeak, SEAS, etc. |
| model | TEXT | |
| type | TEXT | woofer / mid / tweeter / fullrange |
| fs_hz | REAL | |
| qts | REAL | |
| vas_liters | REAL | |
| xmax_mm | REAL | |
| sensitivity_db | REAL | |
| power_rms_w | INTEGER | |
| diameter_mm | INTEGER | |
| price_usd | REAL | |
| price_updated_date | DATE | |
| datasheet_url | TEXT | |
| buy_url | TEXT | |

Pre-seeded with ~100 well-known drivers from Dayton Audio, ScanSpeak, SEAS, Peerless, Tang Band, and Fountek. The seed data is a versioned JSON file checked into the repo. Updating prices is a manual developer task run once per year by re-running the seed script.

### `driver_search_cache` — Claude web research results

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| query | TEXT | |
| driver_model | TEXT | |
| source_url | TEXT | |
| ts_params_json | TEXT | |
| price_usd | REAL | |
| fetched_at | DATETIME | |

Research results are cached here. A result is auto-promoted to `drivers` when all required TS params (fs, Qts, Vas, Xmax, sensitivity) are present and a datasheet URL is found. Results missing any required param are held for manual developer review.

---

## Frontend UI

Two-panel layout:

**Left panel — Chat**
- Conversation thread with user and Claude messages styled distinctly
- Text input + send button at the bottom
- Phase indicator at the top: `Gathering requirements → Designing → Generating BOM`
- Phase transitions are seamless — conversation continues naturally while the backend shifts phases

**Right panel — Design Results**
- Empty during Phase 1
- Populates progressively as Phases 2 and 3 complete:
  - Speaker summary card (type, enclosure, topology)
  - Driver cards (model, key specs, justification)
  - Crossover summary (topology, crossover frequency, component list)
  - BOM table (line items, quantities, unit prices, subtotals)
- Export buttons at the bottom of the BOM: **Download PDF** and **Download CSV**

**State management:** React context holds session ID, phase, conversation history, and design result. All state is persisted to FastAPI on each turn — a page refresh restores the session from SQLite.

---

## BOM Export

### PDF (WeasyPrint)
Server-side HTML template rendered to PDF containing:
- Header: design name, date, session ID
- Design summary: speaker type, enclosure, topology, key specs, enclosure dimensions
- BOM table: part, manufacturer, model, qty, unit price, extended price, source URL
- Subtotals by category (drivers, crossover, hardware) and grand total
- Design rationale: Claude-generated paragraph per driver choice and crossover decision

### CSV
Flat export of the BOM table only, suitable for spreadsheet use or supplier quoting. Columns: `category, part, manufacturer, model, qty, unit_price, extended_price, source_url`

Both exports are generated on demand (not pre-generated). FastAPI pulls stored design JSON from SQLite and renders fresh on each export request.

---

## Out of Scope (Future Phases)

- Photo-realistic product rendering
- Aesthetic design tool (drawing overlay, shape morphing)
- Crossover schematic diagram (visual)
- Automated annual pricing refresh
