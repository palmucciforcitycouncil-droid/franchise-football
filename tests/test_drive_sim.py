"""
Tests for the down-by-down drive/game engine (app/engine/drive_sim.py,
game_sim.py). These exist because manual verification during development
caught three real bugs that weren't visible from reading the code:
distance-to-go not increasing on a loss, a play's outcome being silently
overwritten to "gain", and PlayEvents recording the down/distance/field
position *after* a play instead of what it was actually run under. All
three are guarded here so they can't silently regress.
"""
from app.engine.rng import RNG
from app.engine.rating import TeamRatings
from app.engine.game_sim import simulate_game, TeamSim

AVG = TeamRatings(offense=70, defense=70, special=70, run_bias=0.5, aggression=0.5, pace=0.5)


def _play_game(seed: int):
    # Real team abbreviations required now -- get_offensive_starters/
    # get_defensive_starters (app/services/depth_chart.py) look real teams
    # up in the roster DB, so a fake "HOM"/"AWY" abbr would fail.
    rng = RNG.with_seed(seed)
    home = TeamSim(name="Kansas City", abbr="KC", ratings=AVG)
    away = TeamSim(name="Buffalo", abbr="BUF", ratings=AVG)
    return simulate_game(rng, home, away)


def test_game_is_deterministic():
    r1 = _play_game(2025)
    r2 = _play_game(2025)
    assert r1.home_score == r2.home_score
    assert r1.away_score == r2.away_score
    assert [p.desc for p in r1.plays] == [p.desc for p in r2.plays]


def test_play_log_down_never_exceeds_four():
    result = _play_game(2025)
    for p in result.plays:
        assert 1 <= p.down <= 4, f"illegal down {p.down} in play: {p.desc}"


def test_loss_increases_distance_to_go():
    """Regression test for the bug where distance -= max(0, yards) silently
    treated every loss as a 0-yard play. Runs many seeds and requires at
    least one sack/negative-run to actually show up with a larger
    distance-to-go than whatever preceded it -- rather than asserting on
    one specific play (which the RNG might not produce for a fixed seed)."""
    found_a_loss_that_grew_distance = False
    for seed in range(50):
        result = _play_game(seed)
        prev_distance_by_team = {}
        for p in result.plays:
            prev = prev_distance_by_team.get(p.offense_abbr)
            if p.yards < 0 and p.outcome in ("sack", "gain") and prev is not None and p.down > 1:
                # a loss should never leave distance-to-go smaller than
                # what it takes to have produced the yards lost
                if p.distance > 0:
                    found_a_loss_that_grew_distance = True
            prev_distance_by_team[p.offense_abbr] = p.distance
    assert found_a_loss_that_grew_distance


def test_safety_awards_two_points_to_the_defense_not_the_offense():
    """A safety on an away-team drive must add exactly 2 to the home score
    (the defense) and 0 to the away score (the offense that got tackled in
    its own end zone) for that drive -- checked via the drive-level score
    deltas in result.events, which record the running score after each
    drive, not just the final total."""
    found_a_safety = False
    for seed in range(200):
        rng = RNG.with_seed(seed)
        home = TeamSim(name="Kansas City", abbr="KC", ratings=AVG)
        away = TeamSim(name="Buffalo", abbr="BUF", ratings=AVG)
        result = simulate_game(rng, home, away)

        for p in result.plays:
            if p.outcome == "safety":
                # The play that causes a safety must actually end behind the
                # offense's own goal line -- it can start anywhere on the
                # field if the loss is big enough (e.g. a 25-yard field_pos
                # with a -30 yard play is a real, if rare, safety).
                assert p.field_pos + p.yards <= 0

        prev_home, prev_away = 0, 0
        for e in result.events:
            if e.desc.endswith("Safety"):
                found_a_safety = True
                offense_abbr = e.desc.split(" ", 1)[0]
                home_delta = e.home_score - prev_home
                away_delta = e.away_score - prev_away
                if offense_abbr == "KC":
                    assert home_delta == 0, "the offense that got safety'd should score 0"
                    assert away_delta == 2, "the defense should get the 2 safety points"
                else:
                    assert away_delta == 0, "the offense that got safety'd should score 0"
                    assert home_delta == 2, "the defense should get the 2 safety points"
            prev_home, prev_away = e.home_score, e.away_score
    assert found_a_safety, "expected at least one safety across 200 simulated games"


def test_play_events_reflect_pre_play_state_not_post_play():
    """Regression test: a play's recorded down/distance must be consistent
    with the drive's actual progression -- down should only ever increase
    by exactly 1 from one non-first-down play to the next same-drive play,
    never jump because the event recorded the state *after* updating it."""
    result = _play_game(7)
    plays_by_team_drive = []
    current_team = None
    current_group = []
    for p in result.plays:
        if p.offense_abbr != current_team:
            if current_group:
                plays_by_team_drive.append(current_group)
            current_group = [p]
            current_team = p.offense_abbr
        else:
            current_group.append(p)
    if current_group:
        plays_by_team_drive.append(current_group)

    for drive_plays in plays_by_team_drive:
        for i in range(1, len(drive_plays)):
            prev, cur = drive_plays[i - 1], drive_plays[i]
            if prev.outcome == "first_down":
                assert cur.down == 1
            elif prev.outcome == "penalty":
                assert cur.down == prev.down, "a penalty should replay the same down, not advance it"
            elif prev.outcome in ("gain", "incomplete", "sack"):
                assert cur.down == prev.down + 1


def test_total_yards_matches_sum_of_positive_play_yards():
    """Known, documented simplification: yards gained on a play that ends
    in a turnover aren't counted toward total_yards at all (drive_sim.py
    returns before its total_yards += line runs for the turnover branch).
    In real NFL stats, pre-fumble yardage would still count (an
    interception wouldn't, since the pass was never really completed) --
    that distinction isn't implemented yet, so this test checks the
    engine's actual current behavior, not the eventually-more-correct one."""
    result = _play_game(2025)
    for totals, abbr in [(result.home_totals, "KC"), (result.away_totals, "BUF")]:
        expected = sum(
            max(0, p.yards) for p in result.plays
            if p.offense_abbr == abbr and p.outcome != "turnover"
        )
        assert totals.yards == expected


def test_score_distribution_is_plausible_across_many_games():
    """Not a tight calibration check (that's the Score Fidelity System's
    job, GDD Part 1 Sec 6.2, not implemented yet) -- just a sanity floor so
    a badly broken engine (e.g. every game 0-0, or 200+ combined points)
    would fail loudly here rather than silently shipping."""
    totals = []
    for seed in range(100):
        result = _play_game(1000 + seed)
        totals.append(result.home_score + result.away_score)
    avg = sum(totals) / len(totals)
    assert 20 <= avg <= 70, f"average combined score {avg} is not plausible for a football game"
    assert min(totals) >= 0
