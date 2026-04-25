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
