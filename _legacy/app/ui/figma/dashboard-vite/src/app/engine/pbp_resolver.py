from __future__ import annotations
import random
from app.engine.pbp_curves import third_down_logit, red_zone_td_prob, fourth_down_decision, weather_adjustments, sigmoid
from app.engine.pbp_modifiers import compose_pass_complete_logit, pressure_probability_logit, sack_prob_from_pressure, draw_pos_noise, PosVarianceCaps
from app.engine.safety_controller import SafetyController
from app.telemetry.game_metrics import GameMetrics
from app.services.team_priors import get_team_priors

class PBPPlayResolver:
    def __init__(self, session, season: int, game_seed: int, is_indoor: bool, wind_mph: float, precip: str):
        self.session = session
        self.season = season
        self.rng = random.Random(game_seed)
        self.weather = weather_adjustments(is_indoor, wind_mph, precip)
        self.safety = SafetyController()
        self.metrics = GameMetrics()
        self.varcaps = PosVarianceCaps()

    def resolve_pass_play(self, ctx):
        # ctx contains: offense_team_id, defense_team_id, down, ytg, yardline, depth_secs, qb_cov, wr_db, ol_dl, coach_agg, kicker_max
        offp = get_team_priors(self.session, self.season, ctx.offense_team_id)
        defp = get_team_priors(self.session, self.season, ctx.defense_team_id)

        # per-drive / per-game small noise by role (use WR cap for WR-targeted play, etc.)
        noise_off = draw_pos_noise(self.rng, self.varcaps.wr)
        noise_def = draw_pos_noise(self.rng, self.varcaps.d)

        sit = third_down_logit(ctx.ytg) if ctx.down == 3 else 0.0
        logit_c = compose_pass_complete_logit(ctx.qb_cov, ctx.wr_db, ctx.ol_dl,
                                              offp.__dict__, defp.__dict__,
                                              sit, noise_off, noise_def,
                                              self.weather["pass_logit"])
        # Safety nudge (late game only, tiny)
        nudge = self.safety.evaluate(ctx.quarter, self.metrics.as_live())
        logit_c += nudge.logit_delta

        p_complete = sigmoid(logit_c)

        # pressure/sack branch
        logit_press = pressure_probability_logit(ctx.ol_dl, ctx.depth_secs, defp.pressure_mod, noise_def)
        p_pressure = sigmoid(logit_press)
        p_sack = sack_prob_from_pressure(p_pressure, ctx.depth_secs)

        # sample outcome (respect ordering: sack > throw)
        x = self.rng.random()
        if x < p_sack:
            ctx.outcome = "SACK"; self.metrics.sacks += 1; return ctx

        # throw outcome (simplified; your engine may already have INT logic)
        y = self.rng.random()
        if y < p_complete:
            ctx.outcome = "COMPLETE"
            # yard sampling happens elsewhere; update yards, possible conversion...
        else:
            # interception branch probability can depend on pressure flag + qb risk
            ctx.outcome = "INCOMPLETE"
        return ctx

    def fourth_down_call(self, ctx):
        return fourth_down_decision(self.rng, ctx.yardline, ctx.to_go, ctx.kicker_max, ctx.coach_agg)
