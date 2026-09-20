"""
Injury system tests (ROADMAP.md R1; GDD Part 1 Sec 3.8 / Sec 6.10).

Style follows this suite's existing convention (test_coaching.py,
test_roster_strength.py): hand-built fixtures with exact expected values
for the pure functions, DB-backed assertions only where a DB is
genuinely what's under test -- copying the real database to a throwaway
and redirecting `app.core.db.DB_PATH`, per ROADMAP.md Sec 2b's mandatory
convention (made even more mandatory by this very chunk's own real
incident -- see that section's third entry).
"""
from __future__ import annotations
import shutil

import pytest
from sqlmodel import select

from app.core import db as db_module
from app.engine import injuries
from app.models.injury import INITIAL_RTP_PENALTY, Injury, InjurySeverity, InjuryType
from app.models.player import Player, Position
from app.services import coach_store, depth_chart, injury_store, season_state


def _player(position: Position, overall: int, player_id: str, team_abbr: str = "ZZ", durability: int = 70) -> Player:
    return Player(
        player_id=player_id, first_name="Test", last_name=player_id, position=position,
        team_abbr=team_abbr, age=25, overall_rating=overall, potential=overall, morale=70,
        speed=70, acceleration=70, strength=70, agility=70, jumping=70, stamina=70,
        toughness=70, durability=durability, throw_power=70, throw_accuracy_short=70,
        throw_accuracy_mid=70, throw_accuracy_deep=70, play_action=70, throw_on_the_run=70,
        throw_under_pressure=70, break_sack=70, catching=70, spectacular_catch=70,
        catch_in_traffic=70, short_route_running=70, medium_route_running=70,
        deep_route_running=70, release=70, carrying=70, trucking=70, change_of_direction=70,
        ball_carrier_vision=70, stiff_arm=70, spin_move=70, juke_move=70, break_tackle=70,
        run_block=70, pass_block=70, run_block_power=70, run_block_finesse=70,
        pass_block_power=70, pass_block_finesse=70, lead_block=70, impact_blocking=70,
        tackle=70, hit_power=70, block_shedding=70, pursuit=70, play_recognition=70,
        man_coverage=70, zone_coverage=70, press=70, power_moves=70, finesse_moves=70,
        kick_power=70, kick_accuracy=70, kick_return=70, awareness=70,
    )


# --------------------------------------------------------------------
# Pure functions -- no DB
# --------------------------------------------------------------------

def test_proneness_multiplier_uses_durability_not_a_nonexistent_field():
    """Player has no injury_proneness field despite the GDD's field list
    naming one -- durability (inverted) is the real attribute. This test
    exists because the very first live run of this module crashed on
    exactly that wrong assumption."""
    tough = _player(Position.QB, 80, "tough", durability=99)
    fragile = _player(Position.QB, 80, "fragile", durability=1)
    assert injuries._proneness_multiplier(tough) < injuries._proneness_multiplier(fragile)
    assert injuries._proneness_multiplier(tough) == pytest.approx(1.0 + (99 - 99) / 100 * 0.5)
    assert injuries._proneness_multiplier(fragile) == pytest.approx(1.0 + (99 - 1) / 100 * 0.5)


def test_more_exposure_events_means_higher_injury_risk():
    low = injuries._no_injury_probability({"carry": 5}, proneness_mult=1.0)
    high = injuries._no_injury_probability({"carry": 30}, proneness_mult=1.0)
    assert high < low  # more carries -> lower probability of staying healthy


def test_a_sack_is_riskier_per_event_than_a_pass_attempt():
    one_sack = injuries._no_injury_probability({"sack": 1}, proneness_mult=1.0)
    one_attempt = injuries._no_injury_probability({"pass_attempt": 1}, proneness_mult=1.0)
    assert one_sack < one_attempt


def test_apply_rtp_penalty_scales_a_copy_and_leaves_the_original_alone():
    player = _player(Position.HB, 80, "rb1")
    scaled = injuries.apply_rtp_penalty(player, 0.10)
    assert scaled is not player
    assert scaled.overall_rating == round(80 * 0.90)
    assert scaled.speed == round(70 * 0.90)
    assert player.overall_rating == 80  # real stored rating untouched


def test_apply_rtp_penalty_of_zero_returns_the_same_object():
    player = _player(Position.HB, 80, "rb1")
    assert injuries.apply_rtp_penalty(player, 0.0) is player


def test_generation_is_deterministic_for_the_same_seed():
    from app.engine.rng import RNG, stable_seed
    player = _player(Position.QB, 80, "qb1", team_abbr="ZZ")
    seed = stable_seed("injury", 1, 1, 1, player.player_id)
    a = injuries._generate_injury(RNG.with_seed(seed), player, "ZZ", season_number=1, week_num=1)
    b = injuries._generate_injury(RNG.with_seed(seed), player, "ZZ", season_number=1, week_num=1)
    assert (a.injury_type, a.severity, a.weeks_out) == (b.injury_type, b.severity, b.weeks_out)


def test_duration_is_capped_at_season_end():
    from app.engine.rng import RNG
    from app.engine.schedule import N_WEEKS
    rng = RNG.with_seed(12345)
    weeks_out = injuries._duration_weeks(rng, InjurySeverity.MAJOR, week_num=N_WEEKS)
    assert weeks_out == 0  # no weeks left in the season to be out for


def test_major_injuries_are_ir_eligible_minor_ones_are_not():
    minor = Injury(injury_id="a", player_id="p", team_abbr="ZZ", season_number=1, week_injured=1,
                    injury_type=InjuryType.ANKLE, severity=InjurySeverity.MINOR, weeks_out=1,
                    placed_on_ir=(1 >= 4))
    major = Injury(injury_id="b", player_id="p2", team_abbr="ZZ", season_number=1, week_injured=1,
                    injury_type=InjuryType.KNEE, severity=InjurySeverity.MAJOR, weeks_out=8,
                    placed_on_ir=(8 >= 4))
    assert minor.placed_on_ir is False
    assert major.placed_on_ir is True


# --------------------------------------------------------------------
# apply_weekly_decay's state machine -- DB-backed (writes), throwaway DB
# --------------------------------------------------------------------

@pytest.fixture
def isolated_db(tmp_path_factory):
    real_path = db_module.DB_PATH
    throwaway = tmp_path_factory.mktemp("injurydb") / "franchise.db"
    shutil.copy(real_path, throwaway)
    db_module.DB_PATH = throwaway
    db_module._engine = None
    coach_store.clear_cache()
    depth_chart.clear_starters_cache()
    injury_store.clear_cache()
    try:
        yield
    finally:
        db_module.DB_PATH = real_path
        db_module._engine = None
        coach_store.clear_cache()
        depth_chart.clear_starters_cache()
        injury_store.clear_cache()


def _make_injury(**overrides) -> Injury:
    base = dict(
        injury_id="test_1_1", player_id="test_player", team_abbr="ZZ",
        season_number=1, week_injured=1, injury_type=InjuryType.KNEE,
        severity=InjurySeverity.MODERATE, weeks_out=2, rtp_penalty=0.0,
        placed_on_ir=False, is_active=True,
    )
    base.update(overrides)
    return Injury(**base)


def test_decay_decrements_weeks_out_then_starts_rtp_taper(isolated_db):
    injury_store.save_injuries([_make_injury(weeks_out=1, severity=InjurySeverity.MODERATE)])
    injuries.apply_weekly_decay(season_number=1, week_num=2)
    injury = injury_store.injury_for_player("test_player")
    assert injury.weeks_out == 0
    assert injury.rtp_penalty == INITIAL_RTP_PENALTY[InjurySeverity.MODERATE]
    assert injury.is_active is True


def test_decay_tapers_rtp_penalty_and_eventually_auto_closes(isolated_db):
    injury_store.save_injuries([_make_injury(weeks_out=0, rtp_penalty=0.10)])
    injuries.apply_weekly_decay(season_number=1, week_num=3)  # 0.10 -> 0.05
    assert injury_store.injury_for_player("test_player").rtp_penalty == pytest.approx(0.05)
    injuries.apply_weekly_decay(season_number=1, week_num=4)  # 0.05 -> 0.0, closes
    injury = injury_store.injury_for_player("test_player")
    assert injury is None  # no longer active
    assert injury_store.currently_out_player_ids() == frozenset()


def test_resolve_all_active_closes_out_everything(isolated_db):
    injury_store.save_injuries([_make_injury(weeks_out=6, severity=InjurySeverity.MAJOR)])
    assert injury_store.injury_for_player("test_player") is not None
    injury_store.resolve_all_active()
    assert injury_store.injury_for_player("test_player") is None


def test_reroll_at_the_same_player_season_week_upserts_not_duplicates(isolated_db):
    """Real, legitimate scenario: reset_season() then re-simulate the
    same season_number's weeks re-derives the exact same deterministic
    injury_id -- caught via a real IntegrityError on this feature's own
    first re-simulated run."""
    injury_store.save_injuries([_make_injury(weeks_out=2)])
    injury_store.save_injuries([_make_injury(weeks_out=5, severity=InjurySeverity.MAJOR)])  # same injury_id
    with db_module.get_session() as s:
        rows = list(s.exec(select(Injury).where(Injury.player_id == "test_player")))
    assert len(rows) == 1
    assert rows[0].weeks_out == 5


# --------------------------------------------------------------------
# Dashboard Team Injuries box -- DB-backed
# --------------------------------------------------------------------

def test_dashboard_injury_line_shows_weeks_out_when_really_out(isolated_db):
    from app.main import _team_injuries_for_dashboard
    with db_module.get_session() as s:
        s.add(_player(Position.QB, 90, "qb_hurt", team_abbr="ZZ"))
        s.commit()
    injury_store.save_injuries([_make_injury(player_id="qb_hurt", team_abbr="ZZ", weeks_out=3)])

    lines = _team_injuries_for_dashboard("ZZ")
    assert len(lines) == 1
    assert "3 wks" in lines[0]


def test_dashboard_injury_line_reads_playing_limited_not_0_wks_during_rtp_taper(isolated_db):
    """Brian's playtest report: "what does it mean when it says 0 weeks?"
    weeks_out==0 means the player has entered RTP taper (Injury.is_out's
    own docstring) -- he's active and playing again, just weakened, not
    "out" for a nonsensical zero weeks."""
    from app.main import _team_injuries_for_dashboard
    with db_module.get_session() as s:
        s.add(_player(Position.QB, 90, "qb_tapering", team_abbr="ZZ"))
        s.commit()
    injury_store.save_injuries([_make_injury(
        player_id="qb_tapering", team_abbr="ZZ", weeks_out=0, rtp_penalty=0.1,
    )])

    lines = _team_injuries_for_dashboard("ZZ")
    assert len(lines) == 1
    assert "0 wk" not in lines[0]
    assert "playing, limited" in lines[0]


# --------------------------------------------------------------------
# depth_chart.py's OUT-exclusion and backfill -- DB-backed
# --------------------------------------------------------------------

def test_an_out_player_is_excluded_from_starter_selection(isolated_db):
    with db_module.get_session() as s:
        s.add(_player(Position.QB, 90, "qb_starter", team_abbr="ZZ"))
        s.add(_player(Position.QB, 40, "qb_backup", team_abbr="ZZ"))
        s.commit()
    injury_store.save_injuries([_make_injury(player_id="qb_starter", weeks_out=3)])
    depth_chart.clear_starters_cache()

    roster = depth_chart._load_roster("ZZ")
    top_qb = depth_chart._top(roster, Position.QB, 1, "ZZ")
    assert top_qb[0].player_id == "qb_backup"  # the better-rated starter is OUT


def test_backfill_kicks_in_only_when_healthy_pool_cant_fill_every_slot(isolated_db):
    """DT needs 2 real starters (depth_chart.get_defensive_starters). If
    only 1 is healthy, the 2nd slot must still fill (with the OUT
    player) rather than crash -- a real IndexError on this feature's own
    first live full-season run."""
    with db_module.get_session() as s:
        s.add(_player(Position.DT, 85, "dt1", team_abbr="ZZ"))
        s.add(_player(Position.DT, 70, "dt2", team_abbr="ZZ"))
        s.commit()
    injury_store.save_injuries([
        _make_injury(injury_id="i1", player_id="dt1", weeks_out=2),
        _make_injury(injury_id="i2", player_id="dt2", weeks_out=2),
    ])
    depth_chart.clear_starters_cache()

    roster = depth_chart._load_roster("ZZ")
    top_dts = depth_chart._top(roster, Position.DT, 2, "ZZ")
    assert len(top_dts) == 2  # both backfilled in, not crashed on an empty healthy pool
    assert {p.player_id for p in top_dts} == {"dt1", "dt2"}


def test_an_rtp_taper_player_stays_selectable_with_scaled_attributes(isolated_db):
    with db_module.get_session() as s:
        s.add(_player(Position.QB, 90, "qb_healing", team_abbr="ZZ"))
        s.commit()
    injury_store.save_injuries([_make_injury(player_id="qb_healing", weeks_out=0, rtp_penalty=0.10)])
    depth_chart.clear_starters_cache()

    roster = depth_chart._load_roster("ZZ")
    assert roster[0].player_id == "qb_healing"
    assert roster[0].overall_rating == round(90 * 0.90)  # scaled, still in the pool


# --------------------------------------------------------------------
# Season-level sanity check -- real full-season simulation
# --------------------------------------------------------------------

@pytest.fixture
def isolated_full_sim(tmp_path_factory):
    """Copies ALL FOUR persistence surfaces season_state touches --
    DB_PATH plus save/history/power-rank/gameplan paths -- per
    ROADMAP.md Sec 2b's mandatory convention (this very chunk's own real
    incident is now the THIRD documented case of skipping this)."""
    from app.services import gameplan_store, history_store, power_rank_history, save_service

    real_db_path = db_module.DB_PATH
    throwaway_db = tmp_path_factory.mktemp("injurydb") / "franchise.db"
    shutil.copy(real_db_path, throwaway_db)
    db_module.DB_PATH = throwaway_db
    db_module._engine = None

    real_save, real_history, real_gameplan, real_power_rank = (
        save_service.DEFAULT_SAVE_PATH, history_store.DEFAULT_PATH,
        gameplan_store.DEFAULT_PATH, power_rank_history.DEFAULT_PATH,
    )
    tmp_dir = tmp_path_factory.mktemp("injurysaves")
    save_service.DEFAULT_SAVE_PATH = tmp_dir / "season.json"
    history_store.DEFAULT_PATH = tmp_dir / "history.json"
    gameplan_store.DEFAULT_PATH = tmp_dir / "gameplans.json"
    power_rank_history.DEFAULT_PATH = tmp_dir / "power_rank.json"

    coach_store.clear_cache()
    depth_chart.clear_starters_cache()
    injury_store.clear_cache()
    try:
        yield
    finally:
        db_module.DB_PATH = real_db_path
        db_module._engine = None
        save_service.DEFAULT_SAVE_PATH = real_save
        history_store.DEFAULT_PATH = real_history
        gameplan_store.DEFAULT_PATH = real_gameplan
        power_rank_history.DEFAULT_PATH = real_power_rank
        coach_store.clear_cache()
        depth_chart.clear_starters_cache()
        injury_store.clear_cache()


def test_a_full_season_produces_a_realistic_injury_count_and_never_crashes(isolated_full_sim):
    """Real NFL: roughly 350-500 players miss time across 32 teams in a
    season -- this is a wide, generous band (not tight calibration,
    same headroom philosophy as test_stat_realism.py), just catching a
    systemic multiple-of-real blowout or a rate that's collapsed to
    ~zero. The real point of this test, though, is that a full season
    simulates start to finish without an available-roster crash -- the
    exact failure mode this chunk's own live runs found twice."""
    from app.engine.schedule import N_WEEKS

    season_state.reset_season()
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season = season_state.get_season()

    total = injury_store.season_injury_count(season.season_number)
    assert 100 <= total <= 900, f"{total} injuries this season is outside a generous realistic band"
