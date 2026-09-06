import csv
from pathlib import Path
from typing import Dict
from sqlmodel import Session, select
from app.models.sim_models import SimTeam
from app.models.player import Player
from app.models.depth_chart import DepthChart
from app.models.coach_models import Coach
from app.models.contract_models import PlayerContract, CapSummary

DATA_DIR = Path("app/data")

def _team_id_by_abbr(session: Session) -> Dict[str,int]:
    return {t.abbr: t.id for t in session.query(SimTeam).all()}

def import_players(session: Session, filename: str = "players.csv") -> int:
    path = DATA_DIR/filename
    mp = _team_id_by_abbr(session)
    count = 0
    with path.open(newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            abbr = row.get("team_abbr","").strip()
            if abbr not in mp: continue
            team_id = mp[abbr]
            pos = row.get("pos","QB").strip().upper()
            
            # Map CSV fields to existing Player model fields
            first_name = row.get("first","").strip() or "First"
            last_name = row.get("last","").strip() or "Last"
            ovr = int(row.get("ovr", "60"))
            age = int(row.get("age","24") or 24)
            potential = int(row.get("potential","50") or 50)
            
            # Create Player with existing model structure
            p = Player(
                team_id=team_id,
                first_name=first_name,
                last_name=last_name,
                position=pos,
                jersey_number=count + 1,  # Simple jersey assignment
                speed=ovr,  # Use OVR as base for speed
                strength=ovr - 5,  # Slightly lower strength
                agility=ovr + 2,  # Slightly higher agility
                throw_power=ovr if pos == "QB" else 50,
                throw_accuracy=ovr if pos == "QB" else 50,
                catching=ovr if pos in ["WR", "TE"] else 50,
                tackling=ovr if pos in ["DL", "LB", "CB", "S"] else 50,
                awareness=ovr,
                potential=potential,
                age=age,
                stamina=ovr,
                injury_proneness=50,
                morale=50
            )
            session.add(p); session.flush()
            # naive contract: 3yr, aav scaled by ovr
            aav = int(400_000 + ovr * 25_000)
            session.add(PlayerContract(player_id=p.id, team_id=team_id, years=3, aav=aav))
            count += 1
    session.commit()
    # rebuild depth chart: best-to-worst per pos
    rebuild_depth_charts(session)
    # cap summary
    rebuild_caps(session)
    return count

def rebuild_depth_charts(session: Session):
    team_ids = [t.id for t in session.query(SimTeam).all()]
    for tid in team_ids:
        session.query(DepthChart).filter(DepthChart.team_id==tid).delete()
        players = session.query(Player).filter(Player.team_id==tid).all()
        by_pos: Dict[str,list[Player]] = {}
        for p in players:
            by_pos.setdefault(p.position, []).append(p)
        for pos, arr in by_pos.items():
            # Sort by awareness (closest to OVR in existing model)
            arr.sort(key=lambda x: x.awareness, reverse=True)
            # Create depth chart entry with starter and backup
            starter = arr[0] if len(arr) > 0 else None
            backup = arr[1] if len(arr) > 1 else None
            session.add(DepthChart(
                team_id=tid, 
                position=pos, 
                starter_player_id=starter.id if starter else None,
                backup_player_id=backup.id if backup else None
            ))
    session.commit()

def rebuild_caps(session: Session):
    session.query(CapSummary).delete()
    teams = {t.id:t for t in session.query(SimTeam).all()}
    for tid in teams:
        deals = session.query(PlayerContract).filter(PlayerContract.team_id==tid, PlayerContract.is_active==True).all()
        committed = sum(c.aav for c in deals)
        session.add(CapSummary(team_id=tid, committed=committed))
    session.commit()

def import_coaches(session: Session, filename: str = "coaches.csv") -> int:
    path = DATA_DIR/filename
    mp = _team_id_by_abbr(session)
    count = 0
    with path.open(newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            abbr = row.get("team_abbr","").strip()
            if abbr not in mp: continue
            team_id = mp[abbr]
            name = row.get("head_coach","Coach").strip() or "Coach"
            rb = float(row.get("run_bias", "0.5"))
            ag = float(row.get("aggression", "0.5"))
            pace = float(row.get("pace", "0.5"))
            # upsert
            existing = session.query(Coach).filter(Coach.team_id==team_id).first()
            if existing:
                existing.name=name; existing.run_bias=rb; existing.aggression=ag; existing.pace=pace
                session.add(existing)
            else:
                session.add(Coach(team_id=team_id, name=name, run_bias=rb, aggression=ag, pace=pace))
            count += 1
    session.commit()
    return count
