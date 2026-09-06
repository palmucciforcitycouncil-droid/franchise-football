# app/services/save_load.py
from __future__ import annotations
from typing import Dict, Any, List, Optional, Iterable
from pathlib import Path
import json, hashlib, time, gzip

from sqlmodel import Session, select, SQLModel

from app.models.core_min import Player
from app.models.season_stats import TeamSeasonStats, PlayerSeasonStats
from app.models.awards import AwardResult
from app.models.progression import PlayerProgression
from app.models.rollover import RolloverAudit
from app.models.savegame import SaveGameAudit

SCHEMA_VERSION = "FF-SAVE-v1"

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _rows(session: Session, model: type[SQLModel]) -> List[SQLModel]:
    # deterministic ordering: try id/primary key, fall back to all()
    stmt = select(model)
    try:
        # prefer id or primary key field if exists
        if hasattr(model, "id"):
            stmt = stmt.order_by(model.id)  # type: ignore[attr-defined]
    except Exception:
        pass
    return list(session.exec(stmt).all())

def _serialize(obj: Any) -> Any:
    # SQLModel -> dict (drop private attrs)
    if isinstance(obj, SQLModel):
        d = obj.model_dump()
        # normalize optional Nones explicitly to None for stable JSON
        return {k: (None if v is None else v) for k, v in sorted(d.items(), key=lambda kv: kv[0])}
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in sorted(obj.items(), key=lambda kv: kv[0])}
    return obj

def _write_bytes(path: Path, data: bytes, compress: bool) -> Path:
    if compress:
        path = path.with_suffix(".json.gz") if path.suffix != ".gz" else path
        with gzip.open(path, "wb") as f:
            f.write(data)
    else:
        path = path.with_suffix(".json")
        path.write_bytes(data)
    return path

def _read_bytes_auto(path: Path) -> bytes:
    if str(path).endswith(".gz"):
        with gzip.open(path, "rb") as f:
            return f.read()
    return Path(path).read_bytes()

def export_league_to_json(session: Session, save_name: str, *, season: Optional[int] = None, out_dir: Path = Path("data/saves"), compress: bool = False) -> Dict[str, Any]:
    """
    Deterministic export of league state to a single JSON file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    # Gather
    payload = {
        "schema_version": SCHEMA_VERSION,
        "season": season,
        "generated_at": int(time.time()),
        "players": _serialize(_rows(session, Player)),
        "team_season_stats": _serialize(_rows(session, TeamSeasonStats)),
        "player_season_stats": _serialize(_rows(session, PlayerSeasonStats)),
        "awards": _serialize(_rows(session, AwardResult)),
        "player_progression": _serialize(_rows(session, PlayerProgression)),
        "rollover_audit": _serialize(_rows(session, RolloverAudit)),
    }
    b = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    h = _sha256_bytes(b)
    base = out_dir / save_name
    path = _write_bytes(base, b, compress=compress)

    # Audit row (upsert by save_name)
    existing = session.exec(select(SaveGameAudit).where(SaveGameAudit.save_name == save_name)).first()
    if existing:
        session.delete(existing)
        session.flush()
    audit = SaveGameAudit(
        save_name=save_name,
        schema_version=SCHEMA_VERSION,
        season=season or 0,
        sha256=h,
        bytes_size=len(b),
        objects_count=sum(len(payload[k]) for k in ["players","team_season_stats","player_season_stats","awards","player_progression","rollover_audit"]),
        notes=f"export compress={compress}"
    )
    session.add(audit)
    session.commit()
    return {"path": str(path), "sha256": h, "bytes": len(b), "objects": audit.objects_count, "compressed": compress}

def _truncate_tables(session: Session, models: Iterable[type[SQLModel]]) -> None:
    # fast replace strategy: delete-all
    for m in models:
        session.exec(m.__table__.delete())  # type: ignore[attr-defined]
    session.commit()

def import_league_from_json(session: Session, save_path: Path, *, strategy: str = "replace") -> Dict[str, Any]:
    """
    Import league state from a JSON save.
    strategy: "replace" (truncate then insert) | "upsert" (simple insert ignoring conflicts where possible)
    """
    raw = _read_bytes_auto(save_path)
    data = json.loads(raw.decode("utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Schema mismatch: {data.get('schema_version')} != {SCHEMA_VERSION}")

    # verify checksum (optional but nice)
    sha = _sha256_bytes(json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8"))

    models: List[type[SQLModel]] = [AwardResult, PlayerProgression, PlayerSeasonStats, TeamSeasonStats, RolloverAudit, Player]
    if strategy == "replace":
        _truncate_tables(session, models)

    # Insert in dependency-friendly order: Players first is fine here
    def _load_list(model: type[SQLModel], key: str) -> int:
        items = data.get(key, [])
        count = 0
        for d in items:
            obj = model.model_validate(d)  # type: ignore
            session.add(obj)
            count += 1
        session.commit()
        return count

    counts = {
        "players": _load_list(Player, "players"),
        "team_season": _load_list(TeamSeasonStats, "team_season_stats"),
        "player_season": _load_list(PlayerSeasonStats, "player_season_stats"),
        "awards": _load_list(AwardResult, "awards"),
        "progression": _load_list(PlayerProgression, "player_progression"),
        "rollover": _load_list(RolloverAudit, "rollover_audit"),
    }

    # write audit
    save_name = save_path.stem.replace(".json","").replace(".json.gz","")
    existing = session.exec(select(SaveGameAudit).where(SaveGameAudit.save_name == save_name)).first()
    if existing:
        session.delete(existing); session.flush()
    audit = SaveGameAudit(
        save_name=save_name,
        schema_version=SCHEMA_VERSION,
        season=data.get("season") or 0,
        sha256=sha,
        bytes_size=len(raw),
        objects_count=sum(counts.values()),
        notes="import"
    )
    session.add(audit); session.commit()

    return {"sha256": sha, "counts": counts}

# ---- Save-slot helpers
def list_saves(out_dir: Path = Path("data/saves")) -> List[Dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(out_dir.glob("*.json")) + sorted(out_dir.glob("*.json.gz")):
        items.append({"name": p.stem.replace(".json",""), "path": str(p), "compressed": p.suffix == ".gz", "bytes": p.stat().st_size})
    return items

def rename_save(session: Session, old: str, new: str, out_dir: Path = Path("data/saves")) -> Dict[str, Any]:
    src_json = out_dir / f"{old}.json"
    src_gz = out_dir / f"{old}.json.gz"
    if src_json.exists():
        dst = out_dir / f"{new}.json"; src_json.rename(dst)
    elif src_gz.exists():
        dst = out_dir / f"{new}.json.gz"; src_gz.rename(dst)
    else:
        raise FileNotFoundError(f"No save named {old}")
    aud = session.exec(select(SaveGameAudit).where(SaveGameAudit.save_name == old)).first()
    if aud:
        aud.save_name = new; session.add(aud); session.commit()
    return {"old": old, "new": new, "path": str(dst)}

def delete_save(session: Session, name: str, out_dir: Path = Path("data/saves")) -> Dict[str, Any]:
    targ = out_dir / f"{name}.json"
    targ_gz = out_dir / f"{name}.json.gz"
    removed = None
    if targ.exists(): targ.unlink(); removed = str(targ)
    elif targ_gz.exists(): targ_gz.unlink(); removed = str(targ_gz)
    else: raise FileNotFoundError(f"No save named {name}")
    aud = session.exec(select(SaveGameAudit).where(SaveGameAudit.save_name == name)).first()
    if aud: session.delete(aud); session.commit()
    return {"deleted": name, "path": removed}
