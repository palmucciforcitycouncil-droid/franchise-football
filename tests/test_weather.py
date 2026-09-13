"""
Tests for R7 (GDD Sec 6.9.2 / Part 2): deterministic weather generation
(app/engine/weather.py) and its real modifier hookup into drive_sim.py's
outcomes.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

from app.engine.rng import RNG
from app.engine.game_sim import simulate_game, TeamSim
from app.engine.rating import TeamRatings
from app.engine.weather import (
    Weather, STADIUM_DATA, generate_weather, _month_for_week,
)

AVG = TeamRatings(offense=70, defense=70, special=70, run_bias=0.5, aggression=0.5, pace=0.5)


def test_weather_is_deterministic():
    w1 = generate_weather(2025, 0, 1, "KC")
    w2 = generate_weather(2025, 0, 1, "KC")
    assert w1 == w2


def test_weather_differs_by_league_seed():
    """Sanity: this isn't secretly ignoring its seed inputs."""
    results = {generate_weather(seed, 0, 10, "GB") for seed in range(20)}
    assert len(results) > 1


def test_dome_stadiums_are_always_indoors_and_neutral():
    dome_teams = [abbr for abbr, s in STADIUM_DATA.items() if s["roof"] == "Dome"]
    assert dome_teams  # sanity: at least one real dome exists in the data
    for abbr in dome_teams:
        for week in range(1, 19):
            w = generate_weather(2025, 0, week, abbr)
            assert w.is_indoors
            assert w.preset == "Clear"
            assert w.temp_f == 72


def test_outdoor_stadium_can_produce_multiple_presets_across_a_season():
    """A real, non-dome, non-retractable stadium should see real weather
    variety across a mock 18-week season, not always the same forecast."""
    presets = {generate_weather(2025, 0, week, "GB").preset for week in range(1, 19)}
    assert len(presets) > 1


def test_retractable_roof_can_be_open_or_closed():
    """A retractable-roof stadium (e.g. DAL) should show BOTH real
    indoor (roof closed) and real outdoor games across many weeks/seeds
    -- never unconditionally one or the other."""
    saw_indoors = saw_outdoors = False
    for seed in range(30):
        for week in range(1, 19):
            w = generate_weather(seed, 0, week, "DAL")
            if w.is_indoors:
                saw_indoors = True
            else:
                saw_outdoors = True
        if saw_indoors and saw_outdoors:
            break
    assert saw_indoors and saw_outdoors


def test_all_32_teams_have_stadium_data():
    from app.data.teams import TEAMS
    for t in TEAMS:
        assert t.abbr in STADIUM_DATA, f"{t.abbr} missing from STADIUM_DATA"


def test_month_for_week_covers_the_full_season():
    months = {_month_for_week(w) for w in range(1, 19)}
    assert months == {9, 10, 11, 12, 1}


def test_get_modifiers_returns_the_presets_dict_for_this_weather():
    w = Weather(preset="Rain", temp_f=45, wind_mph=10, precip="rain", is_indoors=False)
    mods = w.get_modifiers()
    assert mods["pass_acc"] == -0.05
    assert mods["fumble"] == 0.07


def test_summary_string_matches_indoor_and_outdoor_shape():
    indoors = Weather(preset="Clear", temp_f=72, wind_mph=0, precip=None, is_indoors=True)
    assert indoors.summary() == "Indoors"

    outdoors = Weather(preset="Rain", temp_f=45, wind_mph=10, precip="rain", is_indoors=False)
    assert outdoors.summary() == "Outdoors, 45°F, rain"

    windy = Weather(preset="Windy", temp_f=60, wind_mph=25, precip=None, is_indoors=False)
    assert "25 mph wind" in windy.summary()


# --- Real modifier hookup into drive_sim.py / game_sim.py -------------------

def _play_game(seed: int, weather: Weather | None):
    rng = RNG.with_seed(seed)
    home = TeamSim(name="Kansas City", abbr="KC", ratings=AVG)
    away = TeamSim(name="Buffalo", abbr="BUF", ratings=AVG)
    return simulate_game(rng, home, away, weather=weather)


def test_weather_none_behaves_exactly_like_before_this_system_existed():
    """No weather (the default, e.g. the standalone single-game
    simulator) must apply exactly zero modifiers -- same result as
    passing an explicit neutral "Clear" weather."""
    clear = Weather(preset="Clear", temp_f=70, wind_mph=5, precip=None, is_indoors=False)
    for seed in range(5):
        r_none = _play_game(seed, None)
        r_clear = _play_game(seed, clear)
        assert r_none.home_score == r_clear.home_score
        assert r_none.away_score == r_clear.away_score


def test_heavy_rain_meaningfully_increases_fumbles_over_many_games():
    """Real modifier application, not just a stored-but-unused field --
    Heavy Rain's +0.12 fumble modifier should measurably raise the
    turnover-by-fumble rate over a clear-weather baseline across enough
    simulated games to smooth out per-game noise."""
    heavy_rain = Weather(preset="Heavy Rain", temp_f=40, wind_mph=10, precip="rain", is_indoors=False)
    clear = Weather(preset="Clear", temp_f=70, wind_mph=5, precip=None, is_indoors=False)

    def fumble_count(weather):
        total = 0
        for seed in range(15):
            result = _play_game(seed, weather)
            total += sum(
                1 for p in result.plays
                if p.play_type == "run" and p.outcome == "turnover"
            )
        return total

    assert fumble_count(heavy_rain) > fumble_count(clear)


def test_windy_meaningfully_reduces_field_goal_accuracy_over_many_games():
    windy = Weather(preset="Windy", temp_f=45, wind_mph=25, precip=None, is_indoors=False)
    clear = Weather(preset="Clear", temp_f=70, wind_mph=5, precip=None, is_indoors=False)

    def fg_make_rate(weather):
        made = attempted = 0
        for seed in range(20):
            result = _play_game(seed, weather)
            for p in result.plays:
                if p.play_type != "field_goal":
                    continue
                attempted += 1
                if p.outcome == "field_goal":
                    made += 1
        return made / attempted if attempted else None

    windy_rate = fg_make_rate(windy)
    clear_rate = fg_make_rate(clear)
    assert windy_rate is not None and clear_rate is not None
    assert windy_rate < clear_rate
