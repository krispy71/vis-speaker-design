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
from models import Phase, Message


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
