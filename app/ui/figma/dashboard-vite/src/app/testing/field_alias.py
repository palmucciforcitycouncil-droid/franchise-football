# app/testing/field_alias.py
ALIASES = {
    "points": ["points","pts_total","score"],
    "punts": ["punts","punt_att","punts_total"],
    "fga":   ["fga","field_goals_attempted","fg_att"],
    "fgm":   ["fgm","field_goals_made","fg_made"],
    "sacks": ["sacks_def","sacks","def_sacks","team_sacks"],
    "yards_total": ["yards_total","total_yards","yds_total","yards"],
}

def getf(obj, key, default=0):
    """Get field value using aliases."""
    for k in ALIASES.get(key, [key]):
        try:
            v = getattr(obj, k)
            if v is not None:
                return v
        except Exception:
            pass
        try:
            v = obj[k]  # dict-like
            if v is not None:
                return v
        except Exception:
            pass
    return default

def incf(obj, key, val):
    """Increment field value using aliases."""
    for k in ALIASES.get(key, [key]):
        try:
            cur = getattr(obj, k)
            setattr(obj, k, (cur or 0) + val)
            return True
        except Exception:
            continue
    # fallback: try canonical
    try:
        cur = getattr(obj, key, 0)
        setattr(obj, key, (cur or 0) + val)
        return True
    except Exception:
        return False
