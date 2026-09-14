"""
Contract negotiation mood layer (app/engine/negotiation.py +
app/services/negotiation_store.py) and the 2026-09-14 Staff page overhaul
(staff salary cap, 4-assistant limit, coach extensions through the shared
Negotiation modal). Pure-math tests use hand-built ScoreModels; route
tests run against conftest's per-test DB copy and throwaway stores.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.engine import negotiation
from app.engine.negotiation import NegotiationState, ScoreModel
from app.main import app
from app.services import season_state

client = TestClient(app)


def _model(expected: float = 1_000_000.0) -> ScoreModel:
    # Same shape as contracts.py: ACCEPT 0.97, COUNTER 0.80, Considering 0.88, W_AAV 0.65.
    from app.engine.contracts import offer_reaction
    return ScoreModel(accept_threshold=0.97, counter_threshold=0.80, considering_floor=0.88,
                      w_aav=0.65, expected_aav=expected, reaction=offer_reaction)


def _raw_score(aav: float, expected: float = 1_000_000.0, other: float = 0.30) -> float:
    return 0.65 * min(1.3, aav / expected) + other


def _offer(state, aav, roll=False, seed=("t",), expected=1_000_000.0, other=0.30, years=3):
    return negotiation.resolve_offer(state, _raw_score(aav, expected, other), aav, years, 0.0,
                                     _model(expected), seed_parts=seed, roll=roll)


# --------------------------------------------------------------------
# Pure mood math
# --------------------------------------------------------------------

def test_a_clearly_good_offer_is_accepted_immediately():
    outcome, _ = _offer(NegotiationState(), 1_100_000)
    assert outcome.verdict == negotiation.ACCEPT


def test_an_insulting_opening_offer_sours_mood_and_is_rejected():
    outcome, state = _offer(NegotiationState(), 300_000)
    assert outcome.verdict == negotiation.REJECT
    assert state.mood < negotiation.MOOD_START


def test_improving_offers_raise_mood_and_repeated_ones_lower_it():
    _, s1 = _offer(NegotiationState(), 760_000)
    _, s2 = _offer(s1, 820_000)
    assert s2.mood > s1.mood
    _, s3 = _offer(s2, 820_000)
    assert s3.mood < s2.mood


def test_rejection_messages_rotate_so_consecutive_rejections_differ():
    state = NegotiationState(mood=100.0)
    messages = []
    for _ in range(5):
        outcome, state = _offer(state, 100_000)
        if outcome.verdict != negotiation.REJECT:
            break
        messages.append(outcome.message)
    assert messages[:3] == ["Rejected", "No way", "Not happening"]
    assert all(a != b for a, b in zip(messages, messages[1:]))


def test_repeated_lowballs_end_in_a_permanent_refusal():
    state = NegotiationState()
    outcome = None
    for _ in range(10):
        outcome, state = _offer(state, 200_000)
        if outcome.verdict == negotiation.REFUSED:
            break
    assert outcome.verdict == negotiation.REFUSED
    assert outcome.message == "We have had enough, we will not accept any more offers from your team."
    # Even a great offer is refused afterward.
    after, _ = _offer(state, 5_000_000)
    assert after.verdict == negotiation.REFUSED


def test_a_reasonable_offer_draws_a_counter_that_is_honored_on_resubmission():
    outcome, state = _offer(NegotiationState(), 800_000)
    assert outcome.verdict == negotiation.COUNTER
    assert outcome.counter_aav > 800_000
    again, _ = _offer(state, outcome.counter_aav, years=outcome.counter_years)
    assert again.verdict == negotiation.ACCEPT


def test_a_better_mood_counters_closer_to_the_teams_offer():
    neutral, _ = _offer(NegotiationState(mood=50.0), 800_000)
    warm, _ = _offer(NegotiationState(mood=95.0), 800_000)
    assert neutral.verdict == warm.verdict == negotiation.COUNTER
    assert warm.counter_aav < neutral.counter_aav


def test_considering_offers_sometimes_sign_but_not_always():
    """Brian's report: a "Considering" offer never signed. Across many
    independent negotiations (different seeds) some must accept, most not."""
    aav = 900_000  # raw 0.885 -> Considering band
    assert _model().reaction(_raw_score(aav)) == "Considering"
    accepted = sum(
        1 for i in range(400)
        if _offer(NegotiationState(), aav, roll=True, seed=("considering", i))[0].verdict == negotiation.ACCEPT
    )
    assert 0.10 * 400 < accepted < 0.45 * 400


def test_considering_roll_is_reproducible_and_never_used_by_previews():
    a, _ = _offer(NegotiationState(), 900_000, roll=True, seed=("same",))
    b, _ = _offer(NegotiationState(), 900_000, roll=True, seed=("same",))
    assert a.verdict == b.verdict
    preview, _ = _offer(NegotiationState(), 900_000, roll=False)
    assert preview.verdict == negotiation.COUNTER


def test_mood_bonus_is_additive_and_neutral_mood_changes_nothing():
    assert negotiation.mood_bonus(negotiation.MOOD_START) == 0.0
    assert negotiation.mood_bonus(100.0) == pytest.approx(negotiation.MOOD_SCORE_SWING)


def test_negotiation_store_keeps_only_the_current_window():
    from app.services import negotiation_store
    negotiation_store.put("24:season", "KC", "p1", {"mood": 40})
    assert negotiation_store.get("24:season", "KC", "p1") == {"mood": 40}
    negotiation_store.put("24:resign", "KC", "p2", {"mood": 60})
    assert negotiation_store.get("24:season", "KC", "p1") is None
    assert negotiation_store.get("24:resign", "KC", "p2") == {"mood": 60}


def test_negotiation_store_is_redirected_per_save():
    from pathlib import Path
    from app.services import negotiation_store, save_manager
    assert save_manager._paths_for(Path("x"))["negotiations"] == Path("x") / "negotiations.json"


# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------

def _free_agent():
    from app.core.db import get_session
    from app.models.player import Player
    with get_session() as s:
        return s.exec(select(Player).where(Player.team_abbr == None).order_by(Player.overall_rating.desc())).first()  # noqa: E711


def test_free_agency_rejections_rotate_and_refusal_greys_out_further_offers():
    season_state.reset_season()
    season_state.set_user_team("KC")
    fa = _free_agent()
    if fa is None:
        pytest.skip("no free agents in this database")
    verdicts, messages = [], []
    for _ in range(12):
        data = client.post("/free-agency/offer", data={"player_id": fa.player_id, "aav": 1, "years": 1}).json()
        verdicts.append(data["verdict"])
        messages.append(data.get("message"))
        if data["verdict"] == "REFUSED":
            break
    assert verdicts[0] == "REJECT"
    assert messages[0] == "Rejected" and messages[1] == "No way"
    assert verdicts[-1] == "REFUSED"
    assert messages[-1] == negotiation.REFUSAL_MESSAGE
    preview = client.get("/free-agency/offer/preview",
                         params={"player_id": fa.player_id, "aav": 50_000_000, "years": 3}).json()
    assert preview["refused"] is True


def _user_coach(role):
    from app.services import coach_store
    from app.models.coach import CoachRole
    if role is CoachRole.AC:
        acs = coach_store.assistants("KC")
        return acs[0] if acs else None
    return coach_store.coach_in_role("KC", role)


def test_staff_page_shows_staff_cap_real_contract_status_and_no_out_of_99():
    from app.services import coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported")
    from app.engine import contracts
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    resp = client.get("/staff")
    assert resp.status_code == 200
    cap_text = "/ ${:.1f}M".format(contracts.coach_salary_cap_for_season(season.season_number) / 1_000_000)
    assert "Coach Salary" in resp.text and cap_text in resp.text, cap_text
    assert "/99" not in resp.text
    assert "yr(s) left" not in resp.text
    assert "Extend Contract" in resp.text
    assert "/staff/KC/" in resp.text and "/extend/preview" in resp.text


def test_coach_extension_preview_and_submit_return_json_with_mood():
    from app.models.coach import CoachRole
    from app.services import coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported")
    season_state.reset_season()
    season_state.set_user_team("KC")
    hc = _user_coach(CoachRole.HC)
    preview = client.get(f"/staff/KC/{hc.coach_id}/extend/preview", params={"aav": hc.salary_aav, "years": 3})
    assert preview.status_code == 200
    body = preview.json()
    assert {"verdict", "reaction", "mood", "mood_label", "refused"} <= body.keys()
    submit = client.post(f"/staff/KC/{hc.coach_id}/extend", data={"aav": 1_000, "years": 1})
    assert submit.status_code == 200
    assert submit.json()["verdict"] in ("REJECT", "COUNTER", "REFUSED")


def test_coach_extension_over_the_staff_cap_is_refused_with_a_message():
    from app.models.coach import CoachRole
    from app.services import coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported")
    season_state.reset_season()
    season_state.set_user_team("KC")
    hc = _user_coach(CoachRole.HC)
    data = client.post(f"/staff/KC/{hc.coach_id}/extend", data={"aav": 40_000_000, "years": 3}).json()
    assert data["verdict"] == "OVER_CAP"
    assert "salary cap" in data["message"]


def test_hiring_a_fifth_assistant_is_blocked():
    from app.engine import coach_contracts
    from app.models.coach import CoachRole
    from app.services import coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported")
    season_state.reset_season()
    season_state.set_user_team("KC")
    assert len(coach_store.assistants("KC")) == coach_contracts.MAX_ASSISTANTS
    candidate = next((c for c in coach_store.free_agents() if CoachRole(c.role) is CoachRole.AC), None)
    if candidate is None:
        pytest.skip("no free-agent assistants")
    resp = client.post("/staff/KC/hire", data={"role": "AC", "coach_id": candidate.coach_id}, follow_redirects=False)
    assert resp.status_code == 303
    assert "staff_error" in resp.headers["location"]
    coach_store.clear_cache()
    assert len(coach_store.assistants("KC")) == coach_contracts.MAX_ASSISTANTS
    # The page itself never offers a 5th assistant.
    assert "Hire Assistant" not in client.get("/staff").text


def test_an_open_assistant_seat_can_be_filled_within_the_cap():
    from app.engine import coach_contracts, coach_replacement
    from app.models.coach import CoachRole
    from app.services import coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported")
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    coach_replacement.execute_fire(coach_store.assistants("KC")[0].coach_id)
    page = client.get("/staff").text
    assert "Hire Assistant" in page
    candidate = max((c for c in coach_store.free_agents() if CoachRole(c.role) is CoachRole.AC),
                    key=lambda c: c.overall, default=None)
    if candidate is None:
        pytest.skip("no free-agent assistants")
    resp = client.post("/staff/KC/hire", data={"role": "AC", "coach_id": candidate.coach_id}, follow_redirects=False)
    assert resp.status_code == 303
    coach_store.clear_cache()
    hired = coach_store.by_id(candidate.coach_id)
    assert hired.team_abbr == "KC" and hired.salary_aav > 0
    assert coach_contracts.staff_cap_room("KC", season.season_number) >= 0
    assert len(coach_store.assistants("KC")) == coach_contracts.MAX_ASSISTANTS


def test_ai_backfill_restores_four_assistants_and_respects_the_cap():
    from app.engine import coach_contracts, coach_replacement, contracts
    from app.services import coach_ai, coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported")
    season = season_state.reset_season()
    for coach in list(coach_store.assistants("BUF"))[:2]:
        coach_replacement.execute_fire(coach.coach_id)
    assert len(coach_store.assistants("BUF")) == 2
    coach_ai.backfill_assistants(season, exclude_team_abbr="KC")
    assert len(coach_store.assistants("BUF")) == coach_contracts.MAX_ASSISTANTS
    assert coach_contracts.team_staff_payroll("BUF") <= contracts.coach_salary_cap_for_season(season.season_number)
