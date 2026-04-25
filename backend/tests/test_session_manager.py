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

import json
from session_manager import run_design_generation
from models import DesignBrief

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
