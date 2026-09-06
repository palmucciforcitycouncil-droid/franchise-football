from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict

Position = Literal["QB","RB","WR","TE","LT","LG","C","RG","RT","EDGE","IDL","LB","CB","S","K","P","FB"]

class TradeSide(BaseModel):
    team_id: int
    player_ids: List[int] = []
    picks: List[Dict[str,int]] = []  # e.g., {"season": 2026, "round": 3}
    cash: int = 0

class TradeOffer(BaseModel):
    from_side: TradeSide
    to_side: TradeSide

class AssetValue(BaseModel):
    asset_type: Literal["PLAYER","PICK"]
    asset_id: Optional[int] = None
    pick: Optional[Dict[str,int]] = None
    base_value: float
    age_penalty: float = 0.0
    contract_penalty: float = 0.0
    injury_penalty: float = 0.0
    fit_bonus: float = 0.0
    net_value: float

class TeamNeeds(BaseModel):
    team_id: int
    need_by_pos: Dict[Position, float]

class EvaluationInputs(BaseModel):
    season_year: int
    salary_cap: int
    fairness_floor_cpu: float = 0.92
    max_negative_surplus: float = -15.0
    min_need_improvement: float = 6.0
    soft_minimums: Dict[str,int] = Field(default={"QB":2, "OL":8, "CB":4, "S":3, "LB":4, "IDL":3, "EDGE":3, "K":1, "P":1})
    w_player_ovr: float = 1.0
    w_potential: float = 0.35
    w_age_decay: float = 0.04
    w_contract_years: float = 0.6
    w_contract_cost: float = 0.002
    w_need_fit: float = 12.0
    w_pick_round_base: float = 14.0
    w_pick_year_discount: float = 0.12

class EvaluationResult(BaseModel):
    fairness: float
    cpu_surplus: float
    human_surplus: float
    cpu_accepts: bool
    hard_veto: Optional[str] = None
    need_gain: Dict[str, float] = {}
    explanation: List[str] = []
    counter_suggestion: Optional[Dict[str, List[int]]] = None
