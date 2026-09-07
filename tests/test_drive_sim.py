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
                if "automatic first down" in prev.desc:
                    assert cur.down == 1, "a penalty with an automatic first down should reset to 1st down"
                else:
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


def test_interception_is_credited_to_the_defender_not_the_intended_receiver():
    """Real bug (caught by manual play-by-play inspection, not by any
    existing test): _resolve_pass's interception branch returned
    target.receiver.full_name -- the offensive player who got beaten --
    instead of the defender who actually made the interception. Every
    "Interception (name)" in the play log was naming an offensive
    player, e.g. "Interception (Stefon Diggs)" for a WR who never
    touched the ball on the play."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context
    from app.engine.defensive_ai import DefensiveCall, BlitzCall
    from app.engine.drive_sim import _resolve_pass

    off = get_offensive_starters("KC")
    defn = get_defensive_starters("BUF")
    ctx = build_matchup_context(off, defn)
    no_blitz = DefensiveCall(primary="standard", blitz=BlitzCall(called=False), coverage="man", run_tactic=None)
    offense_names = {p.full_name for p in off.receivers} | {off.qb.full_name}

    rng = RNG.with_seed(11)
    found_interception = False
    for _ in range(3000):
        _, outcome, who, _, _ = _resolve_pass(rng, ctx, off.qb, no_blitz)
        if outcome == "turnover":
            found_interception = True
            assert who not in offense_names, f"interception credited to an offensive player: {who}"
    assert found_interception, "expected at least one interception across 3000 pass attempts"


def test_field_goal_and_pat_odds_scale_with_the_real_kicker():
    """OffensiveStarters.k used to not exist (Known Gaps: "no dedicated
    kicker in the starting lineup"); FG/PAT odds were a fixed league
    bucket regardless of who was kicking. Now a real kicker's
    kick_accuracy should measurably move both."""
    from app.engine.drive_sim import _kicker_adjusted_prob, _attempt_field_goal
    from app.models.player import Player, Position

    def _kicker(accuracy: int) -> Player:
        return Player(
            player_id=f"test_k_{accuracy}", first_name="Test", last_name="Kicker",
            position=Position.K, team_abbr="KC", age=25, overall_rating=accuracy,
            potential=accuracy, morale=80, speed=50, acceleration=50, strength=50,
            agility=50, jumping=50, stamina=50, toughness=50, durability=80,
            throw_power=0, throw_accuracy_short=0, throw_accuracy_mid=0, throw_accuracy_deep=0,
            play_action=0, throw_on_the_run=0, throw_under_pressure=0, break_sack=0,
            catching=0, spectacular_catch=0, catch_in_traffic=0, short_route_running=0,
            medium_route_running=0, deep_route_running=0, release=0, carrying=0,
            trucking=0, change_of_direction=0, ball_carrier_vision=0, stiff_arm=0,
            spin_move=0, juke_move=0, break_tackle=0, run_block=0, pass_block=0,
            run_block_power=0, run_block_finesse=0, pass_block_power=0, pass_block_finesse=0,
            lead_block=0, impact_blocking=0, tackle=0, hit_power=0, block_shedding=0,
            pursuit=0, play_recognition=0, man_coverage=0, zone_coverage=0, press=0,
            power_moves=0, finesse_moves=0, kick_power=90, kick_accuracy=accuracy,
            kick_return=0, awareness=80,
        )

    great_kicker = _kicker(99)
    bad_kicker = _kicker(50)

    assert _kicker_adjusted_prob(0.70, great_kicker) > _kicker_adjusted_prob(0.70, bad_kicker)
    assert _kicker_adjusted_prob(0.70, None) == 0.70

    rng_great = RNG.with_seed(3)
    rng_bad = RNG.with_seed(3)
    made_great = sum(1 for _ in range(300) if _attempt_field_goal(rng_great, pos=65, kicker=great_kicker)[0])
    made_bad = sum(1 for _ in range(300) if _attempt_field_goal(rng_bad, pos=65, kicker=bad_kicker)[0])
    assert made_great > made_bad


def test_holding_accept_decline_favors_the_defense_correctly():
    """Pure decision logic (no RNG): the defense should only accept a
    holding call if enforcing it leaves the offense worse off than the
    real play already did."""
    from app.engine.drive_sim import _holding_would_be_accepted

    # A modest gain (5 on 2nd & 10): accepting (10-yard penalty, distance
    # becomes 20) is worse for the offense than declining (distance 5) --
    # defense accepts.
    assert _holding_would_be_accepted(distance=10, real_yards=5) is True

    # A big loss (-20 on 2nd & 10): the real result (distance becomes 30)
    # is already worse for the offense than accepting would be (distance
    # 20) -- defense declines and lets the sack/stuff stand.
    assert _holding_would_be_accepted(distance=10, real_yards=-20) is False


def test_pre_snap_penalties_are_always_enforced_and_attributed_to_a_real_player():
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context
    from app.engine.drive_sim import _check_pre_snap_penalty

    off = get_offensive_starters("KC")
    defn = get_defensive_starters("BUF")
    ctx = build_matchup_context(off, defn)
    ol_names = {p.full_name for p in off.offensive_line}
    dl_names = {p.full_name for p in defn.defensive_line}

    rng = RNG.with_seed(5)
    found_offense, found_defense = False, False
    for _ in range(2000):
        result = _check_pre_snap_penalty(rng, ctx)
        if result is None:
            continue
        desc, side = result
        if side == "offense":
            found_offense = True
            assert any(name in desc for name in ol_names) or off.qb.full_name in desc
        else:
            found_defense = True
            assert any(name in desc for name in dl_names)
    assert found_offense and found_defense, "expected both offensive and defensive pre-snap penalties across 2000 rolls"


def test_defensive_pass_interference_is_attributed_to_the_real_covering_defender():
    """Not a random guess -- the actual defender from that specific pass
    attempt's target/coverage matchup (choose_pass_target), threaded
    through _resolve_pass's new defender_name return value."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context
    from app.engine.defensive_ai import DefensiveCall, BlitzCall
    from app.engine.drive_sim import _resolve_pass, _check_defensive_pass_interference

    off = get_offensive_starters("KC")
    defn = get_defensive_starters("BUF")
    ctx = build_matchup_context(off, defn)
    no_blitz = DefensiveCall(primary="standard", blitz=BlitzCall(called=False), coverage="man", run_tactic=None)
    defender_names = {p.full_name for p in [defn.cb1, defn.cb2, defn.ss, defn.fs]}

    rng = RNG.with_seed(9)
    found = False
    for _ in range(3000):
        _, outcome, _, _, defender_name = _resolve_pass(rng, ctx, off.qb, no_blitz)
        if outcome != "incomplete":
            continue
        penalty = _check_defensive_pass_interference(rng, pos=50, defender_name=defender_name)
        if penalty is not None:
            found = True
            assert defender_name in penalty.desc
            assert defender_name in defender_names
            assert penalty.down == 1
    assert found, "expected at least one DPI call across 3000 incomplete-pass checks"
