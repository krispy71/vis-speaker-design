import uuid
import json
import re
from typing import Optional, Tuple

import database
from models import Session, Phase, Message, DesignBrief, DesignOutput, BOM
from claude_runner import run_claude
from driver_db import find_driver_candidates


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


# ── Phase 1: Intake conversation ───────────────────────────────────────────────

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


def _build_intake_prompt(conversation: list, new_user_message: str) -> str:
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


# ── Phase 2: Design generation ─────────────────────────────────────────────────

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


# ── Phase 3: BOM assembly ──────────────────────────────────────────────────────

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
