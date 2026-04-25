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
