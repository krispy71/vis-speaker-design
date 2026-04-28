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
