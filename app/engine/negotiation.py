"""
Contract negotiation mood (Brian's 2026-09-14 fixes doc) -- the stateful
layer GDD Sec 8.3.3 describes ("Mood Meter ... drains on rejections,
empties on insulting lowballs, locking the negotiation") that R4a/R4b and
the coach Extend Contract flow had each disclosed as a cut. Shared by all
three negotiations: GM Desk re-sign (contracts.py), Free Agency
(free_agency.py) and coach extensions (coach_contracts.py).

**Additive, never a reweight** (project rule): each module's existing
offer score is computed exactly as before; this layer only adds a bounded
mood bonus/penalty ON TOP (MOOD_SCORE_SWING) and then applies that
module's own unchanged ACCEPT/COUNTER thresholds.

The model, per offer:
1. Mood starts at MOOD_START (50, neutral). A better offer than the last
   one raises it (more for a bigger step); a same-or-worse offer lowers
   it; a lowball (raw score below the module's COUNTER threshold) lowers
   it further, an insulting one (INSULT_MARGIN below that) much further.
2. Mood 0 => permanent refusal for this negotiation window
   (negotiation_store.window_for): REFUSAL_MESSAGE, every later offer
   is refused without being scored.
3. Adjusted score = raw score + mood bonus. >= ACCEPT threshold => ACCEPT.
4. "Considering" band (just under ACCEPT): a seeded roll can still ACCEPT
   (~20-30% at neutral mood, higher with a better offer/mood) -- Brian's
   report that a Considering offer never signed.
5. Otherwise, a reasonable offer (>= COUNTER threshold) gets a COUNTER:
   the AAV that would clear ACCEPT ("their ask"), pulled toward the
   midpoint between that ask and the team's offer as mood rises above
   neutral. Offering at least a standing counter's terms is always
   accepted -- the person honors their own proposal.
6. Anything lower is a REJECT, whose message rotates through
   REJECTION_MESSAGES so consecutive rejections never read identically.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Callable

from app.engine.rng import RNG, stable_seed

MOOD_START = 50.0
MOOD_MIN = 0.0
MOOD_MAX = 100.0
# Mood -> additive score adjustment: +-0.05 at the extremes. Small next to
# the 0.17 gap between a module's COUNTER and ACCEPT thresholds -- mood
# nudges a borderline deal, it never turns a lowball into a signing.
MOOD_SCORE_SWING = 0.05
# How far below the COUNTER threshold reads as an insult, not just low.
INSULT_MARGIN = 0.10
# At mood 100 a counter lands on the midpoint between ask and offer; at
# neutral (50) or below it's the full ask.
MAX_CONCESSION = 0.5

# Mood deltas (this module's own documented tuning). With these, three
# insulting offers or four-five stagnant lowballs in a row exhaust a
# neutral negotiator; steady good-faith raises keep mood climbing.
FIRST_OFFER_INSULT = -25.0
FIRST_OFFER_LOWBALL = -12.0
FIRST_OFFER_STRONG = 5.0
IMPROVE_BASE = 4.0
IMPROVE_PER_POINT = 200.0      # +2 mood per 0.01 of score improvement...
IMPROVE_CAP = 12.0             # ...capped
STAGNANT_PENALTY = -10.0
WORSE_PENALTY = -18.0
REPEAT_INSULT_PENALTY = -10.0
REPEAT_LOWBALL_PENALTY = -4.0
IMPROVEMENT_EPSILON = 0.01

CONSIDERING_BASE_PROB = 0.20
CONSIDERING_BAND_BONUS = 0.10  # at the top of the band
CONSIDERING_MOOD_BONUS = 0.15  # at mood 100 (negative below neutral)
CONSIDERING_PROB_MIN = 0.05
CONSIDERING_PROB_MAX = 0.45

REFUSAL_MESSAGE = "We have had enough, we will not accept any more offers from your team."
REJECTION_MESSAGES = ("Rejected", "No way", "Not happening", "No thank you", "Pass")

ACCEPT = "ACCEPT"
COUNTER = "COUNTER"
REJECT = "REJECT"
REFUSED = "REFUSED"


@dataclass
class NegotiationState:
    mood: float = MOOD_START
    offers: list[dict] = field(default_factory=list)   # {"aav","years","guaranteed","score"}
    reject_count: int = 0
    counter: dict | None = None                         # standing {"aav","years","guaranteed_fraction"}
    refused: bool = False

    @classmethod
    def from_dict(cls, d: dict | None) -> "NegotiationState":
        if not d:
            return cls()
        return cls(
            mood=float(d.get("mood", MOOD_START)), offers=list(d.get("offers", [])),
            reject_count=int(d.get("reject_count", 0)), counter=d.get("counter"),
            refused=bool(d.get("refused", False)),
        )

    def to_dict(self) -> dict:
        return {"mood": self.mood, "offers": self.offers, "reject_count": self.reject_count,
                "counter": self.counter, "refused": self.refused}

    def copy(self) -> "NegotiationState":
        return NegotiationState.from_dict(self.to_dict())


@dataclass(frozen=True)
class ScoreModel:
    """One module's real thresholds + how to invert its AAV term. Every
    module scores AAV as W_AAV * min(AAV_POINTS_CAP, offered / expected),
    so the counter AAV is solved from that shared shape."""
    accept_threshold: float
    counter_threshold: float
    considering_floor: float
    w_aav: float
    expected_aav: float
    reaction: Callable[[float], str]
    aav_points_cap: float = 1.3


@dataclass(frozen=True)
class NegotiationOutcome:
    verdict: str
    score: float                 # mood-adjusted
    raw_score: float
    reaction: str
    mood: float
    message: str
    counter_aav: int | None = None
    counter_years: int | None = None


def mood_label(mood: float) -> str:
    if mood >= 75:
        return "Eager"
    if mood >= 55:
        return "Warming up"
    if mood >= 40:
        return "Neutral"
    if mood >= 20:
        return "Frustrated"
    return "Fed up"


def mood_bonus(mood: float) -> float:
    return (mood - MOOD_START) / (MOOD_MAX - MOOD_START) * MOOD_SCORE_SWING


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def mood_delta(state: NegotiationState, raw_score: float, counter_threshold: float) -> float:
    insulting = raw_score < counter_threshold - INSULT_MARGIN
    lowball = raw_score < counter_threshold
    if not state.offers:
        if insulting:
            return FIRST_OFFER_INSULT
        if lowball:
            return FIRST_OFFER_LOWBALL
        return 0.0 if raw_score < counter_threshold + INSULT_MARGIN else FIRST_OFFER_STRONG
    change = raw_score - float(state.offers[-1]["score"])
    if change >= IMPROVEMENT_EPSILON:
        delta = IMPROVE_BASE + min(IMPROVE_CAP, change * IMPROVE_PER_POINT)
    elif change > -IMPROVEMENT_EPSILON:
        delta = STAGNANT_PENALTY
    else:
        delta = WORSE_PENALTY
    if insulting:
        delta += REPEAT_INSULT_PENALTY
    elif lowball:
        delta += REPEAT_LOWBALL_PENALTY
    return delta


def _meets_counter(counter: dict | None, aav: float, years: int, guaranteed: float) -> bool:
    if not counter:
        return False
    total = aav * years
    fraction = guaranteed / total if total else 0.0
    return (aav >= counter["aav"] and years >= counter["years"]
            and fraction + 1e-6 >= counter.get("guaranteed_fraction", 0.0))


def considering_probability(score: float, mood: float, model: ScoreModel) -> float:
    band = max(1e-9, model.accept_threshold - model.considering_floor)
    position = _clamp((score - model.considering_floor) / band, 0.0, 1.0)
    p = (CONSIDERING_BASE_PROB + CONSIDERING_BAND_BONUS * position
         + CONSIDERING_MOOD_BONUS * (mood - MOOD_START) / (MOOD_MAX - MOOD_START))
    return _clamp(p, CONSIDERING_PROB_MIN, CONSIDERING_PROB_MAX)


def _counter_aav(adjusted_score: float, offered_aav: float, mood: float, model: ScoreModel) -> int:
    """Their ask: the AAV that, all else equal, lifts the mood-adjusted
    score to ACCEPT -- then conceded toward the team's offer by mood."""
    expected = model.expected_aav
    if not expected:
        return math.ceil(offered_aav)
    offered_points = min(model.aav_points_cap, offered_aav / expected)
    non_aav = adjusted_score - model.w_aav * offered_points
    needed_points = min(model.aav_points_cap, (model.accept_threshold - non_aav) / model.w_aav)
    ask = max(offered_aav, needed_points * expected)
    concession = MAX_CONCESSION * max(0.0, (mood - MOOD_START) / (MOOD_MAX - MOOD_START))
    return math.ceil(ask - concession * (ask - offered_aav))


def resolve_offer(
    state: NegotiationState, raw_score: float, offered_aav: float, offered_years: int,
    offered_guaranteed: float, model: ScoreModel, seed_parts: tuple, roll: bool = True,
) -> tuple[NegotiationOutcome, NegotiationState]:
    """Pure: returns the outcome plus the NEW state (the caller persists
    it, or discards it for a read-only preview). `roll=False` is the
    preview mode -- the Considering roll is never revealed ahead of a
    real submit, the label alone says "maybe"."""
    new = state.copy()
    if new.refused:
        return NegotiationOutcome(REFUSED, raw_score, raw_score, "Refuses to negotiate", new.mood,
                                  REFUSAL_MESSAGE), new

    if _meets_counter(new.counter, offered_aav, offered_years, offered_guaranteed):
        score = max(raw_score + mood_bonus(new.mood), model.accept_threshold)
        return NegotiationOutcome(ACCEPT, score, raw_score, model.reaction(score), new.mood,
                                  "We have a deal!"), new

    new.mood = _clamp(new.mood + mood_delta(new, raw_score, model.counter_threshold), MOOD_MIN, MOOD_MAX)
    total = offered_aav * offered_years
    new.offers.append({"aav": offered_aav, "years": offered_years, "guaranteed": offered_guaranteed,
                       "score": round(raw_score, 4)})
    if new.mood <= MOOD_MIN:
        new.refused = True
        new.counter = None
        return NegotiationOutcome(REFUSED, raw_score, raw_score, "Refuses to negotiate", new.mood,
                                  REFUSAL_MESSAGE), new

    score = raw_score + mood_bonus(new.mood)
    reaction = model.reaction(score)
    if score >= model.accept_threshold:
        return NegotiationOutcome(ACCEPT, score, raw_score, reaction, new.mood, "We have a deal!"), new

    if roll and score >= model.considering_floor:
        rng = RNG.with_seed(stable_seed(*seed_parts, len(new.offers), "considering"))
        if rng.prob(considering_probability(score, new.mood, model)):
            return NegotiationOutcome(ACCEPT, score, raw_score, reaction, new.mood, "We have a deal!"), new

    if score >= model.counter_threshold:
        counter_aav = _counter_aav(score, offered_aav, new.mood, model)
        new.counter = {"aav": counter_aav, "years": offered_years,
                       "guaranteed_fraction": (offered_guaranteed / total) if total else 0.0}
        return NegotiationOutcome(COUNTER, score, raw_score, reaction, new.mood, "How about this?",
                                  counter_aav=counter_aav, counter_years=offered_years), new

    message = REJECTION_MESSAGES[new.reject_count % len(REJECTION_MESSAGES)]
    new.reject_count += 1
    return NegotiationOutcome(REJECT, score, raw_score, reaction, new.mood, message), new
