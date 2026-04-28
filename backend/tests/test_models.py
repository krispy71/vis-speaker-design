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
