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
