"""
GDD Sec 12: Weekly Headlines. Built deterministic per ROADMAP.md Sec4e
(2026-09-12, Brian's explicit decision) -- a template bank instead of a
live Claude API call, since that would have been the only external-API,
non-reproducible-output dependency in a project whose whole design is
"given the same LEAGUE_SEED, results must be perfectly reproducible"
(GDD Sec 1.3). See docs/GDD_v3.2.md Sec 12.1's amendment note.

Two-stage pipeline, matching GDD Sec 12.2/12.3 exactly:
1. detect_events() -- pure functions over already-real per-week data,
   scored via Sec 12.3's magnitude formula.
2. select_events() -- the tier waterfall Sec 12.2.1/12.2.2/12.2.3's own
   text already specifies: Tier 1 first (capped at 3), Tier 2 fills to
   4, Tier 3 fills to 5.
3. render -- picks a phrasing variant deterministically and fills in
   real values.

Real event sources used: standings/records (season.records), the real
per-game box score (already-computed PassingLine/RushingLine/
ReceivingLine/DefensiveLine), the real archived League Record Book
(history_store.career_stats()/get_history()), and R1's real injuries
(app.engine.injuries.roll_injuries_*()'s own return value).

2026-09-14 rework (Brian's feedback):
- "Upset"/"shocks" only when a genuinely weaker team wins: a clearly
  worse record going in (after enough games to mean something) or, early
  on, a clearly lower PRE-game power rating. Never on a tie, never between
  equal records. (The old check compared POST-game ratings with no record
  context at all, and treated a tied score as a win for the away side --
  which is how "NE shocks NYJ 17-17" happened.)
- A tied score gets its own phrasing; never "falls to"/"defeats"/"upset".
- A team named as the subject/object of a result carries its record in
  parentheses -- "NE (1-14) upsets NYJ (14-1), 32-3" -- but not when the
  team is only there to describe a player ("Name (QB, NE)").
- Headlines change week to week: several phrasings per type, and the
  variant used last time for a type is avoided next time (tracked in
  headlines_history's per-season meta). Clinch stories fire only in the
  week the clinch actually happens (app/engine/clinch.py compares the
  standings before vs. after the week), never repeated.
- Preseason rounds and every playoff round get headlines too (results by
  round name plus standout performers from the real box scores), and any
  STARTER hurt badly enough to miss time gets an injury headline.
- The "NE falls to NO as the favorite, 17-" cut-off was not a template
  bug: the Dashboard's headline list was a fixed-height CSS multi-column
  box, which fragments a wrapped line into an overflow column that's
  clipped out of view. Fixed in base.html (a plain 2-column grid).

Disclosed scope cuts, not fabricated:
- 3b (close games) is final-margin-only. This engine has no clock/
  quarter model anywhere -- there is no score_by_quarter to test a
  halftime deficit against.
- Coaching changes (hires/fires), trades, and free-agent signings are
  NOT event sources this pass -- none of those systems keep a
  timestamped transaction log today.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.rng import stable_seed
from app.engine.season_stats import cached_current_season_aggregates
from app.data.teams import TEAMS_BY_ABBR
from app.services import history_store

REGULAR_SEASON_GAMES = 17  # every team plays exactly 17 (one bye) -- see app/engine/schedule.py

TIER_BASE = {1: 100.0, 2: 50.0, 3: 20.0}
USER_TEAM_BONUS = 10.0
MAX_TIER1 = 3
TARGET_TOTAL = 5
MIN_TOTAL = 4
# Starter-injury headlines ride alongside the tiered picks rather than
# competing with them for the 5 slots -- a starter going down for weeks is
# news regardless of how big the week's other stories were. Capped so a
# brutal injury week doesn't bury everything else; the user's own
# starters are always listed first.
MAX_INJURY_HEADLINES = 3

# Upset rule (see module docstring). A record gap only counts once both
# teams have a real sample; before that a wide PRE-game rating gap is the
# only honest "favorite" signal there is.
UPSET_MIN_GAMES = 4
UPSET_MIN_WIN_PCT_GAP = 0.25
UPSET_RATING_TOLERANCE = 25.0  # a record favorite who is also clearly the weaker-rated side isn't really "the favorite"
UPSET_EARLY_RATING_GAP = 80.0
PLAYOFF_UPSET_SEED_GAP = 3
DIVISION_LEAD_MIN_WEEK = 4  # before this, "first place" flips on coin-toss tiebreaks between 1-0/2-1 teams -- noise, not news

ROUND_LABELS = {"WC": "Wild Card", "DIV": "Divisional Round", "CONF": "Conference Championship", "SB": "Super Bowl"}


@dataclass
class HeadlineEvent:
    tier: int
    category: str
    magnitude: float
    is_user_team: bool
    template_key: str
    values: dict = field(default_factory=dict)
    event_key: str = ""  # unique-enough string for the render seed / tie-break

    @property
    def score(self) -> float:
        return TIER_BASE[self.tier] + min(self.magnitude, 20.0) + (USER_TEAM_BONUS if self.is_user_team else 0.0)


def _team_name(abbr: str) -> str:
    """Despite the name, returns the team's real ABBREVIATION (e.g. "KC"),
    not its location -- Brian's request, 2026-09-13: headlines read more
    like real ticker-style sports headlines that way."""
    return abbr


# ---------------------------------------------------------------------------
# Records next to team names
# ---------------------------------------------------------------------------

def _record_str(wins: int, losses: int, ties: int = 0) -> str:
    return f"{wins}-{losses}-{ties}" if ties else f"{wins}-{losses}"


def season_record_map(season) -> dict[str, tuple[int, int, int]]:
    """{abbr: (W, L, T)} straight from season.records -- the exact numbers
    the Standings boxes show, so a headline never disagrees with them."""
    return {abbr: (r.wins, r.losses, getattr(r, "ties", 0)) for abbr, r in season.records.items()}


def games_record_map(weeks: list[list]) -> dict[str, tuple[int, int, int]]:
    """{abbr: (W, L, T)} over a list of weeks of WeekGames by literal score
    -- used for preseason, which never touches season.records."""
    out: dict[str, list[int]] = {}
    for week in weeks:
        for g in week:
            if g.result is None:
                continue
            h, a = g.result.home_score, g.result.away_score
            for abbr, mine, theirs in ((g.home_abbr, h, a), (g.away_abbr, a, h)):
                rec = out.setdefault(abbr, [0, 0, 0])
                rec[0 if mine > theirs else (1 if mine < theirs else 2)] += 1
    return {abbr: tuple(v) for abbr, v in out.items()}


def _label(abbr: str, rec_map: dict | None) -> str:
    """"NE (8-6)" -- only for a team that's the subject/object of a result,
    never for the team in a player's "(POS, TEAM)" tag."""
    if rec_map and abbr in rec_map:
        return f"{_team_name(abbr)} ({_record_str(*rec_map[abbr])})"
    return _team_name(abbr)


def _positions_by_name(team_abbr: str) -> dict[str, str]:
    """{full_name: position} for every real rostered player on team_abbr
    (Brian's request, 2026-09-13: a named player shows their position)."""
    from app.core.db import get_session
    from app.models.player import Player
    from sqlmodel import select

    with get_session() as s:
        players = s.exec(select(Player).where(Player.team_abbr == team_abbr)).all()
        return {p.full_name: p.position.value for p in players}


# ---------------------------------------------------------------------------
# Upset detection (pre-game state)
# ---------------------------------------------------------------------------

def _pregame_ratings(post_home: float, post_away: float, home_score: int, away_score: int) -> tuple[float, float]:
    """Inverts power_rating.update_ratings() for one game. season.records
    only holds POST-game ratings by the time headlines run, but "was this
    an upset" is a question about who was favored BEFORE kickoff. The
    update is zero-sum (so the pair's sum is known) and the new home rating
    is strictly increasing in the old one, so a bisection recovers it
    exactly -- no extra pre-game snapshot needed."""
    from app.engine.power_rating import update_ratings

    total = post_home + post_away
    lo, hi = post_home - 400.0, post_home + 400.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if update_ratings(mid, total - mid, home_score, away_score)[0] < post_home:
            lo = mid
        else:
            hi = mid
    pre_home = (lo + hi) / 2
    return pre_home, total - pre_home


def _is_upset(winner_pre: tuple[int, int, float], loser_pre: tuple[int, int, float]) -> tuple[bool, float]:
    """(is_upset, magnitude). Each side is (wins, losses, rating) as of
    kickoff. Caller guarantees the game wasn't a tie.

    With a real sample, the record gap must be wide both going in AND in
    the records the headline itself prints (after the game) -- a 3-2 team
    beating a 4-1 team was 2-2 vs 4-0 at kickoff, but "BAL (3-2) shocks
    IND (4-1)" reads as nothing shocking at all, which is exactly Brian's
    complaint."""
    w_w, w_l, w_rating = winner_pre
    l_w, l_l, l_rating = loser_pre
    games = min(w_w + w_l, l_w + l_l)
    if games >= UPSET_MIN_GAMES:
        pre_gap = l_w / (l_w + l_l) - w_w / (w_w + w_l)
        post_gap = l_w / (l_w + l_l + 1) - (w_w + 1) / (w_w + w_l + 1)
        if (pre_gap >= UPSET_MIN_WIN_PCT_GAP and post_gap >= UPSET_MIN_WIN_PCT_GAP
                and l_rating >= w_rating - UPSET_RATING_TOLERANCE):
            return True, (pre_gap - UPSET_MIN_WIN_PCT_GAP) * 40.0 + max(l_rating - w_rating, 0.0) / 10.0
        return False, 0.0
    # Too few games for records to mean much: only a wide pre-game rating
    # gap counts, and never when the "favorite" already had the worse record.
    # The printed (post-game) records must still show the loser at least 2
    # wins better, or "CLE (1-2) knocks off BAL (2-1)" reads as a coin flip.
    rating_gap = l_rating - w_rating
    if rating_gap >= UPSET_EARLY_RATING_GAP and l_w - (w_w + 1) >= 2:
        return True, (rating_gap - UPSET_EARLY_RATING_GAP) / 4.0
    return False, 0.0


# ---------------------------------------------------------------------------
# 1a. Standings / Playoff implications
# ---------------------------------------------------------------------------

def _detect_standings_events(season, prior_standings: dict, user_team_abbr: str | None, week_num: int | None = None) -> list[HeadlineEvent]:
    """prior_standings: playoffs.final_division_standings(season) captured
    BEFORE this week's games. Clinches come from app/engine/clinch.py and
    fire only when the status is new THIS week."""
    from app.engine.playoffs import final_division_standings
    from app.engine import clinch

    events: list[HeadlineEvent] = []
    rec_map = season_record_map(season)
    new_standings = final_division_standings(season)

    if week_num is None or week_num >= DIVISION_LEAD_MIN_WEEK:
        for (conf, div), new_order in new_standings.items():
            old_order = prior_standings.get((conf, div), new_order)
            leader, old_leader = new_order[0], old_order[0]
            if leader != old_leader:
                is_user = user_team_abbr in (leader, old_leader)
                events.append(HeadlineEvent(
                    tier=1, category="division_lead_change", magnitude=5.0, is_user_team=is_user,
                    template_key="division_lead_change",
                    values={"team": _team_name(leader), "team_label": _label(leader, rec_map),
                            "division": f"{conf} {div}", "prev": _team_name(old_leader),
                            "prev_label": _label(old_leader, rec_map)},
                    event_key=f"lead|{conf}|{div}|{leader}",
                ))

    if week_num is not None:
        before = clinch.clinches_before_week(season, week_num)
        after = clinch.season_clinches(season)
        for abbr, status in after.items():
            prev = before.get(abbr, clinch.ClinchStatus())
            conf = TEAMS_BY_ABBR[abbr].conference
            values = {"team": _team_name(abbr), "team_label": _label(abbr, rec_map),
                      "division": clinch.division_label(abbr), "conference": conf}
            # One story per team per week -- the biggest new milestone.
            if status.bye and not prev.bye:
                key, mag = "clinch_bye", 18.0
            elif status.division and not prev.division:
                key, mag = "clinch_division", 15.0
            elif status.berth and not prev.berth:
                key, mag = "clinch_berth", 12.0
            else:
                continue
            events.append(HeadlineEvent(
                tier=1, category="clinch", magnitude=mag, is_user_team=(abbr == user_team_abbr),
                template_key=key, values=values, event_key=f"{key}|{abbr}",
            ))
    return events


# ---------------------------------------------------------------------------
# 1b. Single-season records
# ---------------------------------------------------------------------------

_RECORD_CATEGORIES = [
    ("passing", "yards", "passing yards"),
    ("rushing", "yards", "rushing yards"),
    ("receiving", "yards", "receiving yards"),
]


def _single_season_record_values(pool_name: str, stat: str) -> float:
    """The real all-time single-season record for one stat, from every
    archived season's own leader -- not a fabricated number."""
    best = 0.0
    for rec in history_store.get_history():
        leaders = getattr(rec, f"{pool_name}_leaders")
        if leaders:
            best = max(best, getattr(leaders[0], stat))
    return best


def _detect_record_events(season, week_num: int, week_games: list, user_team_abbr: str | None) -> list[HeadlineEvent]:
    """A player's CURRENT season total newly exceeding the real all-time
    single-season record, found via this week's own box-score contribution."""
    from app.engine.box_score import build_box_score

    events: list[HeadlineEvent] = []
    passing, rushing, receiving, _defense = cached_current_season_aggregates(season)
    pools = {"passing": passing, "rushing": rushing, "receiving": receiving}

    for pool_name, stat, label in _RECORD_CATEGORIES:
        record_value = _single_season_record_values(pool_name, stat)
        if record_value <= 0:
            continue
        pool = pools[pool_name]
        for game in week_games:
            if game.result is None:
                continue
            for abbr in (game.home_abbr, game.away_abbr):
                box = build_box_score(game.result.plays, abbr)
                this_week_lines = getattr(box, pool_name)
                if not this_week_lines:
                    continue
                positions = _positions_by_name(abbr)
                for line in this_week_lines:
                    season_total = getattr(pool.get((abbr, line.name)), stat, 0)
                    prior_total = season_total - getattr(line, stat, 0)
                    if prior_total <= record_value < season_total:
                        events.append(HeadlineEvent(
                            tier=1, category="record", magnitude=20.0, is_user_team=(abbr == user_team_abbr),
                            template_key="single_season_record",
                            values={"name": line.name, "pos": positions.get(line.name, ""),
                                    "team": _team_name(abbr), "stat": label, "value": season_total},
                            event_key=f"record|{abbr}|{line.name}|{stat}|{week_num}",
                        ))
    return events


# ---------------------------------------------------------------------------
# 1c. Blowouts, upsets & ties, 2a. milestones & your-team performance, 3b. close games
# ---------------------------------------------------------------------------

_MILESTONES = [
    ("passing", "yards", 300, "passing yards", "stat_milestone"),
    ("rushing", "yards", 150, "rushing yards", "stat_milestone"),
    ("receiving", "yards", 150, "receiving yards", "stat_milestone"),
    ("passing", "interceptions", 3, "interceptions", "int_milestone"),
]


def _detect_game_events(season, week_games: list, user_team_abbr: str | None,
                        rec_map: dict | None = None, allow_upsets: bool = True) -> list[HeadlineEvent]:
    from app.engine.box_score import build_box_score
    from app.engine.defensive_box_score import build_defensive_box_score

    if rec_map is None:
        rec_map = season_record_map(season)
    events: list[HeadlineEvent] = []
    for game in week_games:
        if game.result is None:
            continue
        home, away = game.home_abbr, game.away_abbr
        h_score, a_score = game.result.home_score, game.result.away_score
        is_user = user_team_abbr in (home, away)
        game_key = f"{home}|{away}"

        if h_score == a_score:
            # A tie is its own story -- never a win, loss, or upset.
            events.append(HeadlineEvent(
                tier=2, category="tie", magnitude=10.0, is_user_team=is_user, template_key="tie",
                values={"home": home, "away": away, "home_label": _label(home, rec_map),
                        "away_label": _label(away, rec_map), "score": h_score},
                event_key=f"tie|{game_key}",
            ))
        else:
            winner, loser = (home, away) if h_score > a_score else (away, home)
            w_score, l_score = max(h_score, a_score), min(h_score, a_score)
            margin = w_score - l_score
            result_values = {"winner": _team_name(winner), "loser": _team_name(loser),
                             "winner_label": _label(winner, rec_map), "loser_label": _label(loser, rec_map),
                             "w_score": w_score, "l_score": l_score}

            if margin >= 21:
                events.append(HeadlineEvent(
                    tier=1, category="blowout", magnitude=(margin - 21) / 2.0, is_user_team=is_user,
                    template_key="blowout", values=dict(result_values), event_key=f"blowout|{game_key}",
                ))

            upset = False
            if allow_upsets and winner in season.records and loser in season.records:
                w_rec, l_rec = season.records[winner], season.records[loser]
                pre_home, pre_away = _pregame_ratings(season.records[home].power_rating,
                                                      season.records[away].power_rating, h_score, a_score)
                pre = {home: pre_home, away: pre_away}
                # Records as of kickoff: undo this game's own W/L.
                winner_pre = (max(w_rec.wins - 1, 0), w_rec.losses, pre[winner])
                loser_pre = (l_rec.wins, max(l_rec.losses - 1, 0), pre[loser])
                upset, magnitude = _is_upset(winner_pre, loser_pre)
                if upset:
                    # One story per upset: the user's own team losing as the
                    # favorite gets its own phrasing instead of the generic one
                    # (both used to fire for the same game).
                    if loser != user_team_abbr:
                        events.append(HeadlineEvent(
                            tier=1, category="upset", magnitude=magnitude, is_user_team=is_user,
                            template_key="upset", values=dict(result_values), event_key=f"upset|{game_key}",
                        ))
                    else:
                        events.append(HeadlineEvent(
                            tier=1, category="team_upset", magnitude=magnitude, is_user_team=True,
                            template_key="your_team_upset_loss",
                            values={"team": _team_name(loser), "opp": _team_name(winner),
                                    "team_label": _label(loser, rec_map), "opp_label": _label(winner, rec_map),
                                    "score": l_score, "opp_score": w_score},
                            event_key=f"teamupset|{game_key}",
                        ))

            # 3b close games -- final margin only, see module docstring.
            if margin <= 3 and not upset:
                events.append(HeadlineEvent(
                    tier=3, category="close_game", magnitude=(3 - margin) * 6.0, is_user_team=is_user,
                    template_key="close_game", values=dict(result_values), event_key=f"close|{game_key}",
                ))

        # 2a your-team explosive offense / stingy defense.
        for abbr, points, allowed in ((home, h_score, a_score), (away, a_score, h_score)):
            if abbr != user_team_abbr:
                continue
            if points >= 35:
                events.append(HeadlineEvent(
                    tier=2, category="explosive", magnitude=points - 35, is_user_team=True,
                    template_key="explosive_offense",
                    values={"team": _team_name(abbr), "team_label": _label(abbr, rec_map), "points": points},
                    event_key=f"explosive|{game_key}|{abbr}",
                ))
            if allowed <= 10:
                events.append(HeadlineEvent(
                    tier=2, category="shutout_defense", magnitude=(10 - allowed) * 2.0, is_user_team=True,
                    template_key="shutout_defense",
                    values={"team": _team_name(abbr), "team_label": _label(abbr, rec_map), "allowed": allowed},
                    event_key=f"shutoutdef|{game_key}|{abbr}",
                ))

        # 2a statistical milestones (single-game).
        for abbr in (home, away):
            positions = _positions_by_name(abbr)
            box = build_box_score(game.result.plays, abbr)
            for pool_name, stat, threshold, label, template_key in _MILESTONES:
                for line in getattr(box, pool_name):
                    value = getattr(line, stat)
                    if value >= threshold:
                        events.append(HeadlineEvent(
                            tier=2, category="milestone", magnitude=(value - threshold) / threshold * 20.0,
                            is_user_team=(abbr == user_team_abbr), template_key=template_key,
                            values={"name": line.name, "pos": positions.get(line.name, ""),
                                    "team": _team_name(abbr), "value": value, "stat": label},
                            event_key=f"milestone|{abbr}|{line.name}|{stat}",
                        ))
            for line in build_defensive_box_score(game.result.plays, abbr):
                for value, threshold, per, label in ((line.sacks, 3, 4.0, "sacks"), (line.solo_tackles, 10, 2.0, "tackles")):
                    if value >= threshold:
                        events.append(HeadlineEvent(
                            tier=2, category="milestone", magnitude=(value - threshold) * per,
                            is_user_team=(abbr == user_team_abbr), template_key="stat_milestone",
                            values={"name": line.name, "pos": positions.get(line.name, ""),
                                    "team": _team_name(abbr), "value": value, "stat": label},
                            event_key=f"milestone|{abbr}|{line.name}|{label}",
                        ))
    return events


# ---------------------------------------------------------------------------
# 3a. Starter injuries
# ---------------------------------------------------------------------------

def starter_ids_for_games(games: list) -> set[str]:
    """player_ids of every depth-chart starter (offense incl. K/P, defense)
    for each team in `games`. Call it AFTER the games but BEFORE rolling
    injuries: the starters cache at that point is exactly the lineup that
    took the field (injury_store hasn't changed yet), whereas afterwards a
    newly-hurt starter is already filtered out of the lineup."""
    from app.services import depth_chart

    ids: set[str] = set()
    teams = {abbr for g in games if g.result is not None for abbr in (g.home_abbr, g.away_abbr)}
    for abbr in teams:
        try:
            off = depth_chart.get_offensive_starters(abbr)
            de = depth_chart.get_defensive_starters(abbr)
        except (IndexError, KeyError, ValueError):
            continue  # a roster too thin to field a lineup (synthetic test DBs) -- no starters to report
        players = [off.qb, off.hb, off.wr1, off.wr2, off.wr3, off.te, *off.offensive_line, off.k, off.p,
                   de.dt1, de.dt2, de.le, de.re, de.lolb, de.mlb, de.rolb, de.cb1, de.cb2, de.fs, de.ss]
        ids.update(p.player_id for p in players if p is not None)
    return ids


def _injury_phrase(injury_type_value: str) -> str:
    kind = injury_type_value.replace("_", " ").lower()
    if kind == "concussion":
        return "a concussion"
    if kind == "other":
        return "an undisclosed injury"
    return f"{'an' if kind[0] in 'aeiou' else 'a'} {kind} injury"


def _detect_injury_events(injuries_this_week: list, user_team_abbr: str | None,
                          starter_ids: set[str] | None = None) -> list[HeadlineEvent]:
    """Every STARTER who'll miss time (weeks_out >= 1). `starter_ids` None
    (a caller that couldn't capture the kickoff lineup) falls back to the
    old OVR-80 notability proxy rather than guessing at a lineup."""
    from app.core.db import get_session
    from app.models.player import Player

    events: list[HeadlineEvent] = []
    if not injuries_this_week:
        return events
    with get_session() as s:
        for injury in injuries_this_week:
            if injury.weeks_out < 1:
                continue
            player = s.get(Player, injury.player_id)
            if player is None:
                continue
            is_starter = (injury.player_id in starter_ids) if starter_ids is not None else player.overall_rating >= 80
            if not is_starter:
                continue
            weeks = injury.weeks_out
            events.append(HeadlineEvent(
                tier=3, category="injury", magnitude=min(weeks, 10) + max(player.overall_rating - 70, 0) / 5.0,
                is_user_team=(injury.team_abbr == user_team_abbr), template_key="notable_injury",
                values={"name": player.full_name, "pos": player.position.value, "team": _team_name(injury.team_abbr),
                        "injury": _injury_phrase(injury.injury_type.value),
                        "injury_type": injury.injury_type.value.replace("_", " ").lower(),
                        "weeks_out": weeks, "weeks_text": f"{weeks} week{'s' if weeks != 1 else ''}"},
                event_key=f"injury|{injury.injury_id}",
            ))
    return events


def _select_injuries(events: list[HeadlineEvent]) -> list[HeadlineEvent]:
    return sorted(events, key=lambda e: (not e.is_user_team, -e.magnitude, e.event_key))[:MAX_INJURY_HEADLINES]


# ---------------------------------------------------------------------------
# 3c. Win/loss streaks
# ---------------------------------------------------------------------------

def _team_result_sequence(season, abbr: str, through_week: int) -> list[bool]:
    """True=win, for every game abbr has played through `through_week`,
    in week order (the engine's own W/L convention, GameResult.winner)."""
    seq = []
    for week in season.schedule[:through_week]:
        for game in week:
            if abbr not in (game.home_abbr, game.away_abbr) or game.result is None:
                continue
            is_home = game.home_abbr == abbr
            seq.append((game.result.home_score > game.result.away_score) == is_home)
    return seq


def _detect_streak_events(season, week_num: int, user_team_abbr: str | None) -> list[HeadlineEvent]:
    events: list[HeadlineEvent] = []
    rec_map = season_record_map(season)
    for abbr in season.records:
        seq = _team_result_sequence(season, abbr, week_num)
        if not seq:
            continue
        last = seq[-1]
        length = 0
        for won in reversed(seq):
            if won != last:
                break
            length += 1
        if length in (5, 7, 10):
            events.append(HeadlineEvent(
                tier=3, category="streak", magnitude=(length - 5) * 4.0, is_user_team=(abbr == user_team_abbr),
                template_key="win_streak" if last else "losing_streak",
                values={"team": _team_name(abbr), "team_label": _label(abbr, rec_map), "length": length},
                event_key=f"streak|{abbr}|{week_num}",
            ))
    return events


# ---------------------------------------------------------------------------
# Standout performers (playoffs)
# ---------------------------------------------------------------------------

def _standouts_for_game(plays: list, abbr: str) -> list[tuple[float, str, str]]:
    """(game_score, name, stat_line) for every player on `abbr` with a real
    stat line this game -- a simple, disclosed fantasy-style weighting,
    only used to pick WHO to name, never shown as a number."""
    from app.engine.box_score import build_box_score
    from app.engine.defensive_box_score import build_defensive_box_score

    box = build_box_score(plays, abbr)
    by_name: dict[str, dict] = {}

    def slot(name):
        return by_name.setdefault(name, {"score": 0.0, "parts": []})

    for p in box.passing:
        s = slot(p.name)
        s["score"] += p.yards * 0.04 + p.touchdowns * 4 - p.interceptions * 2
        if p.yards >= 100 or p.touchdowns:
            s["parts"].append(f"{p.yards} passing yards" + (f", {p.touchdowns} TD" if p.touchdowns else ""))
    for r in box.rushing:
        s = slot(r.name)
        s["score"] += r.yards * 0.1 + r.touchdowns * 6
        if r.yards >= 40 or r.touchdowns:
            s["parts"].append(f"{r.yards} rushing yards" + (f", {r.touchdowns} TD" if r.touchdowns else ""))
    for r in box.receiving:
        s = slot(r.name)
        s["score"] += r.yards * 0.1 + r.touchdowns * 6 + r.receptions * 0.5
        if r.yards >= 40 or r.touchdowns:
            s["parts"].append(f"{r.receptions} catches for {r.yards} yards" + (f", {r.touchdowns} TD" if r.touchdowns else ""))
    for d in build_defensive_box_score(plays, abbr):
        s = slot(d.name)
        s["score"] += d.sacks * 3 + d.interceptions * 4 + d.defensive_touchdowns * 6 + d.forced_fumbles * 2 + d.solo_tackles * 0.3
        bits = []
        if d.sacks:
            bits.append(f"{d.sacks} sack{'s' if d.sacks != 1 else ''}")
        if d.interceptions:
            bits.append(f"{d.interceptions} INT")
        if d.defensive_touchdowns:
            bits.append(f"{d.defensive_touchdowns} defensive TD")
        if bits:
            s["parts"].append(", ".join(bits))
    return [(v["score"], name, "; ".join(v["parts"])) for name, v in by_name.items() if v["parts"]]


# ---------------------------------------------------------------------------
# Selection + rendering
# ---------------------------------------------------------------------------

def select_events(events: list[HeadlineEvent], league_seed: int, season_number: int, week_num) -> list[HeadlineEvent]:
    """The tier waterfall GDD Sec 12.2.1/12.2.2/12.2.3 already specifies:
    all Tier 1 (capped at 3), then Tier 2 fills to 4, then Tier 3 fills
    to 5. Within a tier, ordered by score descending; ties broken by a
    deterministic seed (GDD Sec 12.3, filled in 2026-09-12)."""
    def sort_key(e: HeadlineEvent):
        tie = stable_seed(league_seed, season_number, week_num, e.event_key)
        return (-e.score, -tie)

    by_tier = {1: [], 2: [], 3: []}
    for e in events:
        by_tier[e.tier].append(e)
    for t in by_tier:
        by_tier[t].sort(key=sort_key)

    selected = by_tier[1][:MAX_TIER1]
    for t in (2, 3):
        if len(selected) >= TARGET_TOTAL:
            break
        selected.extend(by_tier[t][: TARGET_TOTAL - len(selected)])
    return selected[:TARGET_TOTAL] if len(selected) >= MIN_TOTAL or not events else selected


TEMPLATES: dict[str, list[str]] = {
    "division_lead_change": [
        "{team_label} takes over first place in the {division}, passing {prev_label}.",
        "New leader in the {division}: {team_label} moves ahead of {prev_label}.",
        "{team_label} climbs to the top of the {division}, bumping {prev_label}.",
    ],
    "clinch_division": [
        "{team_label} clinches the {division} title.",
        "{team_label} locks up the {division} crown.",
        "It's official: {team_label} wraps up the {division}.",
    ],
    "clinch_berth": [
        "{team_label} clinches a playoff berth.",
        "{team_label} punches its ticket to the postseason.",
        "{team_label} is headed to the playoffs.",
    ],
    "clinch_bye": [
        "{team_label} locks up the {conference}'s No. 1 seed and a first-round bye.",
        "{team_label} clinches the top seed in the {conference} and a week off.",
    ],
    "single_season_record": [
        "{name} ({pos}, {team}) sets a new single-season record with {value} {stat}.",
        "Record book alert: {name} ({pos}, {team}) now owns the single-season {stat} mark at {value}.",
    ],
    "blowout": [
        "{winner_label} routs {loser_label}, {w_score}-{l_score}.",
        "{winner_label} cruises past {loser_label}, {w_score}-{l_score}.",
        "{winner_label} rolls over {loser_label}, {w_score}-{l_score}.",
        "No contest: {winner_label} buries {loser_label}, {w_score}-{l_score}.",
    ],
    "upset": [
        "{winner_label} upsets {loser_label}, {w_score}-{l_score}.",
        "{winner_label} shocks {loser_label}, {w_score}-{l_score}.",
        "Upset alert: {winner_label} stuns {loser_label}, {w_score}-{l_score}.",
        "Underdog {winner_label} knocks off {loser_label}, {w_score}-{l_score}.",
    ],
    "your_team_upset_loss": [
        "{team_label} falls to {opp_label} as the favorite, {opp_score}-{score}.",
        "{team_label} stumbles against underdog {opp_label}, {opp_score}-{score}.",
        "{opp_label} catches favored {team_label} off guard, {opp_score}-{score}.",
    ],
    "tie": [
        "{away_label} and {home_label} battle to a {score}-{score} tie.",
        "Deadlock: {away_label} and {home_label} finish level at {score}-{score}.",
        "Neither side blinks as {away_label} and {home_label} tie, {score}-{score}.",
    ],
    "explosive_offense": [
        "The {team_label} offense explodes for {points} points.",
        "{team_label} puts {points} points on the board.",
        "The {team_label} offense lights up the scoreboard with {points} points.",
    ],
    "shutout_defense": [
        "The {team_label} defense holds its opponent to just {allowed} points.",
        "{team_label} clamps down, allowing only {allowed} points.",
        "A stingy {team_label} defense gives up just {allowed} points.",
    ],
    "stat_milestone": [
        "{name} ({pos}, {team}) posts {value} {stat}.",
        "{name} ({pos}, {team}) racks up {value} {stat}.",
        "Big day for {name} ({pos}, {team}): {value} {stat}.",
        "{name} ({pos}, {team}) piles up {value} {stat}.",
    ],
    "int_milestone": [
        "{name} ({pos}, {team}) throws {value} interceptions.",
        "Rough outing: {name} ({pos}, {team}) is picked off {value} times.",
    ],
    "close_game": [
        "{winner_label} edges {loser_label} in a nail-biter, {w_score}-{l_score}.",
        "{winner_label} survives {loser_label}, {w_score}-{l_score}.",
        "{winner_label} holds off {loser_label}, {w_score}-{l_score}.",
        "Down to the wire: {winner_label} slips past {loser_label}, {w_score}-{l_score}.",
    ],
    "notable_injury": [
        "{team}'s {name} ({pos}) out {weeks_text} with {injury}.",
        "Injury: {team}'s {name} ({pos}) sidelined {weeks_text} with {injury}.",
        "{team} loses starter {name} ({pos}) for {weeks_text} with {injury}.",
    ],
    "win_streak": [
        "{team_label} extends its winning streak to {length} games.",
        "{team_label} makes it {length} straight wins.",
        "{team_label} is rolling: {length} wins in a row.",
    ],
    "losing_streak": [
        "{team_label} has now dropped {length} straight.",
        "The skid reaches {length} games for {team_label}.",
        "Losing streak hits {length} for {team_label}.",
    ],
    "preseason_result": [
        "Preseason: {winner_label} beats {loser_label}, {w_score}-{l_score}.",
        "Preseason: {winner_label} tops {loser_label}, {w_score}-{l_score}.",
    ],
    "playoff_result": [
        "{round}: {winner_label} beats {loser_label}, {w_score}-{l_score}.",
        "{round}: {winner_label} advances past {loser_label}, {w_score}-{l_score}.",
        "{winner_label} moves on, topping {loser_label} {w_score}-{l_score} in the {round}.",
    ],
    "playoff_blowout": [
        "{round}: {winner_label} routs {loser_label}, {w_score}-{l_score}.",
        "{round}: {winner_label} rolls past {loser_label}, {w_score}-{l_score}.",
    ],
    "playoff_upset": [
        "{round} upset: No. {w_seed} {winner_label} knocks off No. {l_seed} {loser_label}, {w_score}-{l_score}.",
        "{round} stunner: No. {w_seed} {winner_label} ousts No. {l_seed} {loser_label}, {w_score}-{l_score}.",
    ],
    "playoff_tie": [
        # The engine has no overtime model (playoffs.py docstring): a tied
        # score advances the home team. Said plainly rather than dressed up.
        "{round}: {winner_label} advances past {loser_label} after a {w_score}-{l_score} deadlock.",
    ],
    "conference_title": [
        "{winner_label} wins the {conference} Championship, beating {loser_label} {w_score}-{l_score}.",
        "{winner_label} is headed to the Super Bowl after topping {loser_label} {w_score}-{l_score}.",
    ],
    "super_bowl": [
        "{winner_label} wins the Super Bowl, beating {loser_label} {w_score}-{l_score}.",
        "{winner_label} are champions: Super Bowl win over {loser_label}, {w_score}-{l_score}.",
    ],
    "playoff_standout": [
        "{round} standout: {name} ({pos}, {team}) -- {stat_line}.",
        "{name} ({pos}, {team}) stars in the {round} with {stat_line}.",
        "{name} ({pos}, {team}) leads the way against {opp}: {stat_line}.",
    ],
}

# Order of every headline entry within one season -- lets the variety
# tracker tell "the previous entry" apart from a stale one left behind by a
# reset that reused this season_number.
_PLAYOFF_ORDER = {"WC": 41, "DIV": 42, "CONF": 43, "SB": 44}


def entry_order(entry_key) -> int:
    key = str(entry_key)
    if key.startswith("P") and key[1:].isdigit():
        return int(key[1:])
    if key.isdigit():
        return 10 + int(key)
    return _PLAYOFF_ORDER.get(key, 100)


def _render_events(events: list[HeadlineEvent], league_seed: int, season_number: int, entry_key) -> list[str]:
    """Renders each event, choosing a phrasing variant that (a) wasn't used
    for the same headline type in the previous entry (last week/round) and
    (b) isn't already used by another event of that type this entry --
    whenever enough variants exist. Deterministic for a given seed and
    prior entry. Persists what it used in headlines_history's meta."""
    from app.services import headlines_history

    order = entry_order(entry_key)
    meta = headlines_history.get_meta(season_number)
    prev_order = meta.get("last_order")
    prev_used = meta.get("last_variants", {}) if (prev_order is not None and prev_order < order) else {}

    used: dict[str, list[int]] = {}
    lines = []
    for e in events:
        variants = TEMPLATES[e.template_key]
        n = len(variants)
        taken = set(used.get(e.template_key, []))
        avoid = taken | set(prev_used.get(e.template_key, []))
        candidates = [i for i in range(n) if i not in avoid] or [i for i in range(n) if i not in taken] or list(range(n))
        idx = candidates[stable_seed(league_seed, season_number, str(entry_key), e.event_key, e.template_key) % len(candidates)]
        used.setdefault(e.template_key, []).append(idx)
        lines.append(variants[idx].format(**e.values))

    headlines_history.set_meta(season_number, {"last_order": order, "last_variants": used})
    return lines


def render_headline(event: HeadlineEvent, league_seed: int, season_number: int, week_num) -> str:
    """Single-event render (no cross-week variety tracking) -- kept for
    callers/tests that just need one line."""
    variants = TEMPLATES[event.template_key]
    idx = stable_seed(league_seed, season_number, week_num, event.event_key, event.template_key) % len(variants)
    return variants[idx].format(**event.values)


def weekly_headlines(season, week_num: int, prior_standings: dict, injuries_this_week: list,
                     starter_ids: set[str] | None = None) -> list[str]:
    """Orchestrates the whole pipeline for one just-simulated week.
    `prior_standings` is playoffs.final_division_standings(season)
    captured by the caller BEFORE this week's games were simulated;
    `starter_ids` from starter_ids_for_games() captured before injuries
    were rolled."""
    week_games = season.schedule[week_num - 1]
    events: list[HeadlineEvent] = []
    events += _detect_standings_events(season, prior_standings, season.user_team_abbr, week_num)
    events += _detect_record_events(season, week_num, week_games, season.user_team_abbr)
    events += _detect_game_events(season, week_games, season.user_team_abbr)
    events += _detect_streak_events(season, week_num, season.user_team_abbr)
    injury_events = _select_injuries(_detect_injury_events(injuries_this_week, season.user_team_abbr, starter_ids))

    selected = select_events(events, season.league_seed, season.season_number, week_num) + injury_events
    if not selected:
        return [f"Week {week_num} is in the books around the league."]
    return _render_events(selected, season.league_seed, season.season_number, week_num)


def preseason_round_headlines(season, round_idx: int, injuries_this_round: list,
                              starter_ids: set[str] | None = None) -> list[str]:
    """One preseason round: the round's biggest results/performances (with
    PRESEASON records -- these games never touch season.records) and any
    starter injuries. No upsets: every team enters preseason at the same
    rating with no record, so nobody is a real favorite yet."""
    games = season.preseason_schedule[round_idx - 1]
    rec_map = games_record_map(season.preseason_schedule[:round_idx])
    events = _detect_game_events(season, games, season.user_team_abbr, rec_map=rec_map, allow_upsets=False)
    for e in events:
        # "Preseason:" prefix on plain results so these never read as
        # regular-season games.
        if e.template_key in ("blowout", "close_game"):
            e.template_key = "preseason_result"
    injury_events = _select_injuries(_detect_injury_events(injuries_this_round, season.user_team_abbr, starter_ids))
    key = f"P{round_idx}"
    selected = select_events(events, season.league_seed, season.season_number, key) + injury_events
    if not selected:
        return [f"Preseason Round {round_idx} is in the books."]
    return _render_events(selected, season.league_seed, season.season_number, key)


MAX_PLAYOFF_STANDOUTS = 3


def playoff_round_headlines(season, round_matchups: list) -> list[str]:
    """Every result in a just-completed playoff round, named by round,
    plus the round's top standout performers from the real box scores."""
    if not round_matchups:
        return []
    round_name = round_matchups[0].round_name
    round_label = ROUND_LABELS.get(round_name, round_name)
    rec_map = season_record_map(season)
    positions_cache: dict[str, dict[str, str]] = {}
    events: list[HeadlineEvent] = []
    standouts: list[tuple[float, HeadlineEvent]] = []

    for m in round_matchups:
        if m.result is None:
            continue
        winner, loser = m.winner_abbr, (m.away_abbr if m.winner_abbr == m.home_abbr else m.home_abbr)
        w_seed = m.home_seed if winner == m.home_abbr else m.away_seed
        l_seed = m.away_seed if winner == m.home_abbr else m.home_seed
        h, a = m.result.home_score, m.result.away_score
        w_score, l_score = (h, a) if winner == m.home_abbr else (a, h)
        values = {"round": round_label, "winner": winner, "loser": loser,
                  "winner_label": _label(winner, rec_map), "loser_label": _label(loser, rec_map),
                  "w_score": w_score, "l_score": l_score, "w_seed": w_seed, "l_seed": l_seed,
                  "conference": m.conference or ""}
        if h == a:
            key = "playoff_tie"
        elif round_name == "SB":
            key = "super_bowl"
        elif round_name == "CONF":
            key = "conference_title"
        elif w_seed - l_seed >= PLAYOFF_UPSET_SEED_GAP:
            key = "playoff_upset"
        elif w_score - l_score >= 21:
            key = "playoff_blowout"
        else:
            key = "playoff_result"
        events.append(HeadlineEvent(tier=1, category="playoff_result", magnitude=0.0,
                                    is_user_team=season.user_team_abbr in (m.home_abbr, m.away_abbr),
                                    template_key=key, values=values, event_key=f"po|{round_name}|{m.home_abbr}|{m.away_abbr}"))

        for abbr, opp in ((m.home_abbr, m.away_abbr), (m.away_abbr, m.home_abbr)):
            for score, name, stat_line in _standouts_for_game(m.result.plays, abbr):
                # Winners' standouts are the story; a loser needs a truly
                # huge game to be named.
                weight = score if abbr == winner else score * 0.6
                if abbr not in positions_cache:
                    positions_cache[abbr] = _positions_by_name(abbr)
                standouts.append((weight, HeadlineEvent(
                    tier=2, category="playoff_standout", magnitude=score, is_user_team=abbr == season.user_team_abbr,
                    template_key="playoff_standout",
                    values={"round": round_label, "name": name, "pos": positions_cache[abbr].get(name, ""),
                            "team": abbr, "opp": opp, "stat_line": stat_line},
                    event_key=f"standout|{round_name}|{abbr}|{name}",
                )))

    standouts.sort(key=lambda t: (-t[0], t[1].event_key))
    top, seen_games = [], set()
    for _w, ev in standouts:
        game_teams = frozenset((ev.values["team"], ev.values["opp"]))
        if game_teams in seen_games and len(events) > 1:
            continue  # spread standouts across games when there's more than one
        seen_games.add(game_teams)
        top.append(ev)
        if len(top) >= MAX_PLAYOFF_STANDOUTS or (round_name == "SB" and len(top) >= 1):
            break
    return _render_events(events + top, season.league_seed, season.season_number, round_name)
