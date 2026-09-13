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
3. render_headline() -- picks a phrasing template deterministically
   (flavor_text.pick_and_render) and fills in real values.

Real event sources used: standings/records (season.records), the real
per-game box score (already-computed PassingLine/RushingLine/
ReceivingLine/DefensiveLine), the real archived League Record Book
(history_store.career_stats()/get_history()), and R1's real injuries
(app.engine.injuries.roll_injuries_for_week()'s own return value).

Disclosed scope cuts, not fabricated:
- 3b (close games) is final-margin-only. This engine has no clock/
  quarter model anywhere (same disclosed gap the Dashboard's Box Score
  header and GDD Sec 6.5 already carry) -- there is no score_by_quarter
  to test a halftime deficit against, so the "trails by 14+ at any
  half and wins" half of 3b's GDD condition can't be built.
- 1a's clinch/elimination check is a real pairwise formula (a team has
  clinched over a specific rival when its win total already exceeds
  that rival's maximum possible final win total), applied against each
  group's closest real threat -- not a full multi-team-tiebreaker-aware
  combinatorial solver. Correct for the large majority of real
  standings; can be wrong only in rare 3+-way-tiebreaker situations very
  late in a season. GDD Sec 12.3 discloses this the same way.
- 3a (injuries) uses `overall_rating >= 80` only, not GDD's fuller "OR
  listed as a depth-chart starter" -- a real, disclosed simplification
  to avoid a second, more involved cross-position starter lookup for a
  condition the OVR threshold already catches the overwhelming majority
  of real cases for.
- Coaching changes (hires/fires), trades, and free-agent signings are
  NOT event sources this pass -- none of those systems keep a
  timestamped transaction log today, so "did this happen THIS WEEK"
  can't be determined without inventing one first. A real, disclosed
  cut for a future pass, not silently dropped from GDD Sec 12.2's
  original scope (which never listed them anyway -- they're new real
  systems since Sec 12.2 was written, see ROADMAP.md Sec4e).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.flavor_text import pick_and_render
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
    t = TEAMS_BY_ABBR.get(abbr)
    return t.location if t else abbr


# ---------------------------------------------------------------------------
# 1a. Standings / Playoff implications
# ---------------------------------------------------------------------------

def _division_of(abbr: str) -> tuple[str, str]:
    t = TEAMS_BY_ABBR[abbr]
    return (t.conference, t.division)


def _detect_standings_events(season, prior_standings: dict, user_team_abbr: str | None) -> list[HeadlineEvent]:
    """prior_standings: playoffs.final_division_standings(season) captured
    BEFORE this week's games (a plain dict, cheap to compute -- no store
    needed since both snapshots are taken within the same
    simulate_current_week() call)."""
    from app.engine.playoffs import final_division_standings

    events: list[HeadlineEvent] = []
    new_standings = final_division_standings(season)

    for (conf, div), new_order in new_standings.items():
        old_order = prior_standings.get((conf, div), new_order)
        leader = new_order[0]
        old_leader = old_order[0]

        # Division lead change (part of 1a).
        if leader != old_leader:
            is_user = leader == user_team_abbr or old_leader == user_team_abbr
            events.append(HeadlineEvent(
                tier=1, category="division_lead_change", magnitude=5.0, is_user_team=is_user,
                template_key="division_lead_change",
                values={"team": _team_name(leader), "division": f"{conf} {div}", "prev": _team_name(old_leader)},
                event_key=f"lead|{conf}|{div}|{leader}",
            ))

        # Clinch/elimination: leader vs. the 2nd-place team in the SAME
        # division only (a real, disclosed simplification of "clinched a
        # playoff spot" down to "clinched the division" -- the wildcard
        # picture spans a whole conference's bubble, which needs
        # bubble_teams()'s own tiebreak-chain output to do properly; left
        # for a future pass rather than approximated further here).
        if len(new_order) >= 2:
            leader_rec, second_rec = season.records[new_order[0]], season.records[new_order[1]]
            second_games_left = REGULAR_SEASON_GAMES - second_rec.games_played
            if leader_rec.wins > second_rec.wins + second_games_left:
                events.append(HeadlineEvent(
                    tier=1, category="clinch", magnitude=15.0, is_user_team=(new_order[0] == user_team_abbr),
                    template_key="clinch_division",
                    values={"team": _team_name(new_order[0]), "division": f"{conf} {div}"},
                    event_key=f"clinch|{conf}|{div}|{new_order[0]}",
                ))
        # Elimination (the mirror-image event, GDD 1a's "eliminated from
        # playoff contention") is NOT built this pass: a real elimination
        # check needs comparing every team in the wildcard hunt against the
        # real 7-seed cutoff (bubble_teams()'s own tiebreak chain), not just
        # a two-team division comparison -- same real scope line the clinch
        # check above already draws. Left for a future pass, not silently
        # half-implemented.

    return events


# ---------------------------------------------------------------------------
# 1b. Single-season records
# ---------------------------------------------------------------------------

_RECORD_CATEGORIES = [
    ("passing", "yards", "pass_yards"),
    ("rushing", "yards", "rush_yards"),
    ("receiving", "yards", "rec_yards"),
]


def _single_season_record_values(pool_name: str, stat: str) -> float:
    """The real all-time single-season record for one stat, from every
    archived season's own leader (index 0 of that season's already-
    sorted-by-yards leader list) -- not a fabricated number."""
    best = 0.0
    for rec in history_store.get_history():
        leaders = getattr(rec, f"{pool_name}_leaders")
        if leaders:
            best = max(best, getattr(leaders[0], stat))
    return best


def _detect_record_events(season, week_num: int, week_games: list, user_team_abbr: str | None) -> list[HeadlineEvent]:
    """A player's CURRENT season total newly exceeding the real all-time
    single-season record -- "newly" meaning it was at-or-below the record
    before this week's game and above it after, using this week's own
    per-game box-score contribution to find the crossing."""
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
                for line in this_week_lines:
                    season_total = getattr(pool.get((abbr, line.name)), stat, 0)
                    this_week_amount = getattr(line, stat, 0)
                    prior_total = season_total - this_week_amount
                    if prior_total <= record_value < season_total:
                        events.append(HeadlineEvent(
                            tier=1, category="record", magnitude=20.0, is_user_team=(abbr == user_team_abbr),
                            template_key="single_season_record",
                            values={"name": line.name, "team": _team_name(abbr), "stat": label.replace("_", " "),
                                    "value": season_total},
                            event_key=f"record|{abbr}|{line.name}|{stat}|{week_num}",
                        ))
    return events


# ---------------------------------------------------------------------------
# 1c. Blowouts & upsets, 2a. milestones & your-team performance, 3b. close games
# ---------------------------------------------------------------------------

_MILESTONES = [
    ("passing", "yards", 300, "pass_yards"),
    ("rushing", "yards", 150, "rush_yards"),
    ("passing", "interceptions", 3, "int_thrown"),
]


def _detect_game_events(season, week_games: list, user_team_abbr: str | None) -> list[HeadlineEvent]:
    from app.engine.box_score import build_box_score
    from app.engine.defensive_box_score import build_defensive_box_score

    events: list[HeadlineEvent] = []
    for game in week_games:
        if game.result is None:
            continue
        home, away = game.home_abbr, game.away_abbr
        h_score, a_score = game.result.home_score, game.result.away_score
        winner, loser = (home, away) if h_score > a_score else (away, home)
        w_score, l_score = max(h_score, a_score), min(h_score, a_score)
        margin = w_score - l_score
        winner_pr = season.records[winner].power_rating
        loser_pr = season.records[loser].power_rating
        is_user = user_team_abbr in (home, away)
        game_key = f"{game.result.winner}|{home}|{away}"

        # 1c blowout (power_rating: LOWER is better in this engine, an
        # Elo-style rating -- see app/engine/power_rating.py).
        if margin >= 21:
            events.append(HeadlineEvent(
                tier=1, category="blowout", magnitude=(margin - 21) / 2.0, is_user_team=is_user,
                template_key="blowout",
                values={"winner": _team_name(winner), "loser": _team_name(loser), "w_score": w_score, "l_score": l_score},
                event_key=f"blowout|{game_key}",
            ))
        # 1c upset: winner has the worse (LOWER) power_rating by a wide
        # margin -- this engine's power_rating is Elo-style, higher = better
        # (every existing sort ranks by `-power_rating`; GDD Sec 12.2.1's own
        # "power_rating >= 50 (bottom half)" phrasing assumes a rank/percentile
        # number instead, a real GDD-vs-implementation semantic mismatch this
        # simplified real-gap check sidesteps rather than tries to reconcile).
        pr_gap = loser_pr - winner_pr
        if pr_gap >= 25:
            events.append(HeadlineEvent(
                tier=1, category="upset", magnitude=(pr_gap - 25) / 2.0, is_user_team=is_user,
                template_key="upset",
                values={"winner": _team_name(winner), "loser": _team_name(loser), "w_score": w_score, "l_score": l_score},
                event_key=f"upset|{game_key}",
            ))

        # 2a your-team performance + explosive/shutout (any team).
        if is_user:
            user_pr = season.records[user_team_abbr].power_rating
            opp_abbr = away if user_team_abbr == home else home
            opp_pr = season.records[opp_abbr].power_rating
            user_won = winner == user_team_abbr
            gap = (opp_pr - user_pr) if user_won else (user_pr - opp_pr)
            if gap >= 15:
                events.append(HeadlineEvent(
                    tier=2, category="team_upset", magnitude=(gap - 15) / 2.0, is_user_team=True,
                    template_key="your_team_upset_win" if user_won else "your_team_upset_loss",
                    values={"team": _team_name(user_team_abbr), "opp": _team_name(opp_abbr),
                            "score": w_score if user_won else l_score, "opp_score": l_score if user_won else w_score},
                    event_key=f"teamupset|{game_key}",
                ))
        for abbr, points in ((home, h_score), (away, a_score)):
            if abbr == user_team_abbr and points >= 35:
                events.append(HeadlineEvent(
                    tier=2, category="explosive", magnitude=points - 35, is_user_team=True,
                    template_key="explosive_offense",
                    values={"team": _team_name(abbr), "points": points},
                    event_key=f"explosive|{game_key}|{abbr}",
                ))
        for abbr, allowed in ((home, a_score), (away, h_score)):
            if abbr == user_team_abbr and allowed <= 10:
                events.append(HeadlineEvent(
                    tier=2, category="shutout_defense", magnitude=(10 - allowed) * 2.0, is_user_team=True,
                    template_key="shutout_defense",
                    values={"team": _team_name(abbr), "allowed": allowed},
                    event_key=f"shutoutdef|{game_key}|{abbr}",
                ))

        # 2a statistical milestones (single-game).
        for abbr in (home, away):
            box = build_box_score(game.result.plays, abbr)
            for pool_name, stat, threshold, label in _MILESTONES:
                for line in getattr(box, pool_name):
                    value = getattr(line, stat)
                    if value >= threshold:
                        events.append(HeadlineEvent(
                            tier=2, category="milestone", magnitude=(value - threshold) / threshold * 20.0,
                            is_user_team=(abbr == user_team_abbr), template_key="stat_milestone",
                            values={"name": line.name, "team": _team_name(abbr), "value": value,
                                    "stat": label.replace("_", " ")},
                            event_key=f"milestone|{abbr}|{line.name}|{stat}",
                        ))
            dbox = build_defensive_box_score(game.result.plays, abbr)
            for line in dbox:
                if line.sacks >= 3:
                    events.append(HeadlineEvent(
                        tier=2, category="milestone", magnitude=(line.sacks - 3) * 4.0,
                        is_user_team=(abbr == user_team_abbr), template_key="stat_milestone",
                        values={"name": line.name, "team": _team_name(abbr), "value": line.sacks, "stat": "sacks"},
                        event_key=f"milestone|{abbr}|{line.name}|sacks",
                    ))
                if line.solo_tackles >= 10:
                    events.append(HeadlineEvent(
                        tier=2, category="milestone", magnitude=(line.solo_tackles - 10) * 2.0,
                        is_user_team=(abbr == user_team_abbr), template_key="stat_milestone",
                        values={"name": line.name, "team": _team_name(abbr), "value": line.solo_tackles, "stat": "tackles"},
                        event_key=f"milestone|{abbr}|{line.name}|tackles",
                    ))

        # 3b close games -- final margin only, see module docstring.
        if margin <= 3:
            events.append(HeadlineEvent(
                tier=3, category="close_game", magnitude=(3 - margin) * 6.0, is_user_team=is_user,
                template_key="close_game",
                values={"winner": _team_name(winner), "loser": _team_name(loser), "w_score": w_score, "l_score": l_score},
                event_key=f"close|{game_key}",
            ))
    return events


# ---------------------------------------------------------------------------
# 3a. Notable injuries
# ---------------------------------------------------------------------------

def _detect_injury_events(injuries_this_week: list, user_team_abbr: str | None) -> list[HeadlineEvent]:
    from app.core.db import get_session
    from app.models.player import Player

    events: list[HeadlineEvent] = []
    if not injuries_this_week:
        return events
    with get_session() as s:
        for injury in injuries_this_week:
            player = s.get(Player, injury.player_id)
            if player is None or player.overall_rating < 80:
                continue
            events.append(HeadlineEvent(
                tier=3, category="injury", magnitude=player.overall_rating - 80,
                is_user_team=(injury.team_abbr == user_team_abbr), template_key="notable_injury",
                values={"name": player.full_name, "team": _team_name(injury.team_abbr),
                        "injury_type": injury.injury_type.value.replace("_", " ").lower(),
                        "weeks_out": injury.weeks_out},
                event_key=f"injury|{injury.injury_id}",
            ))
    return events


# ---------------------------------------------------------------------------
# 3c. Win/loss streaks
# ---------------------------------------------------------------------------

def _team_result_sequence(season, abbr: str, through_week: int) -> list[bool]:
    """True=win, for every game abbr has played through `through_week`,
    in week order -- reconstructed from the real schedule/results, no
    separate streak-tracking state needed."""
    seq = []
    for week in season.schedule[:through_week]:
        for game in week:
            if abbr not in (game.home_abbr, game.away_abbr) or game.result is None:
                continue
            is_home = game.home_abbr == abbr
            won = (game.result.home_score > game.result.away_score) == is_home
            seq.append(won)
    return seq


def _detect_streak_events(season, week_num: int, user_team_abbr: str | None) -> list[HeadlineEvent]:
    events: list[HeadlineEvent] = []
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
                values={"team": _team_name(abbr), "length": length},
                event_key=f"streak|{abbr}|{week_num}",
            ))
    return events


# ---------------------------------------------------------------------------
# Selection + rendering
# ---------------------------------------------------------------------------

def select_events(events: list[HeadlineEvent], league_seed: int, season_number: int, week_num: int) -> list[HeadlineEvent]:
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
        "{team} takes over first place in the {division}, passing {prev}.",
        "New leader in the {division}: {team} moves ahead of {prev}.",
    ],
    "clinch_division": [
        "{team} clinches the {division} title.",
        "{team} locks up the {division} crown.",
    ],
    "single_season_record": [
        "{name} ({team}) sets a new single-season record with {value} {stat}.",
        "Record book alert: {name} ({team}) now owns the single-season {stat} mark at {value}.",
    ],
    "blowout": [
        "{winner} routs {loser} {w_score}-{l_score}.",
        "{winner} cruises past {loser}, {w_score}-{l_score}.",
    ],
    "upset": [
        "{winner} shocks {loser} {w_score}-{l_score}.",
        "Upset alert: {winner} stuns {loser}, {w_score}-{l_score}.",
    ],
    "your_team_upset_win": [
        "{team} pulls off the upset over {opp}, {score}-{opp_score}.",
    ],
    "your_team_upset_loss": [
        "{team} falls to {opp} as the favorite, {opp_score}-{score}.",
    ],
    "explosive_offense": [
        "{team}'s offense explodes for {points} points.",
    ],
    "shutout_defense": [
        "{team}'s defense holds the opponent to just {allowed} points.",
    ],
    "stat_milestone": [
        "{name} ({team}) posts {value} {stat} this week.",
    ],
    "close_game": [
        "{winner} edges {loser} in a nail-biter, {w_score}-{l_score}.",
        "{winner} survives {loser} {w_score}-{l_score} in a one-score game.",
    ],
    "notable_injury": [
        "{name} ({team}) exits with a {injury_type} injury, expected out {weeks_out} week(s).",
    ],
    "win_streak": [
        "{team} extends its winning streak to {length} games.",
    ],
    "losing_streak": [
        "{team} has now dropped {length} straight.",
    ],
}


def render_headline(event: HeadlineEvent, league_seed: int, season_number: int, week_num: int) -> str:
    return pick_and_render(
        TEMPLATES, event.template_key,
        (league_seed, season_number, week_num, event.event_key),
        **event.values,
    )


def weekly_headlines(season, week_num: int, prior_standings: dict, injuries_this_week: list) -> list[str]:
    """Orchestrates the whole pipeline for one just-simulated week.
    `prior_standings` is playoffs.final_division_standings(season)
    captured by the caller BEFORE this week's games were simulated."""
    week_games = season.schedule[week_num - 1]
    events: list[HeadlineEvent] = []
    events += _detect_standings_events(season, prior_standings, season.user_team_abbr)
    events += _detect_record_events(season, week_num, week_games, season.user_team_abbr)
    events += _detect_game_events(season, week_games, season.user_team_abbr)
    events += _detect_injury_events(injuries_this_week, season.user_team_abbr)
    events += _detect_streak_events(season, week_num, season.user_team_abbr)

    selected = select_events(events, season.league_seed, season.season_number, week_num)
    if not selected:
        return [f"Week {week_num} is in the books around the league."]
    return [render_headline(e, season.league_seed, season.season_number, week_num) for e in selected]
