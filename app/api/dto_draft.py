from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel

class ProspectDTO(BaseModel):
    id: int
    name: str
    pos: str
    college: str
    ovr: int
    grade: float

class PickRowDTO(BaseModel):
    overall: int
    round: int
    pick_in_round: int
    team_name: str
    prospect_name_or_dash: str
    ovr_or_dash: str
    pos_or_dash: str
    college_or_dash: str
    status: str

class DraftBoardDTO(BaseModel):
    prospects: List[ProspectDTO]

class DraftResultsDTO(BaseModel):
    season_year: int
    current_overall: int
    user_on_clock: bool
    round: int
    rows: List[PickRowDTO]

class ActionResult(BaseModel):
    ok: bool
    message: str
