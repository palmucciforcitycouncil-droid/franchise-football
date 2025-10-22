from app.services.playoffs_service import build_bracket
from types import SimpleNamespace

def _team(id, conf, wins, pr):
    return SimpleNamespace(id=id, conference=conf, division="East", wins=wins, losses=0, power_rating=pr)

def test_bracket_shapes_and_wc_pairs():
    # 16 per conf so we can test "in the hunt" properly (like real NFL)
    afc = [_team(100+i,"AFC",wins=12-i%4, pr=1500+i) for i in range(16)]
    nfc = [_team(200+i,"NFC",wins=11-i%4, pr=1400+i) for i in range(16)]
    bracket = build_bracket(2025, afc+nfc)
    assert bracket.season_year == 2025
    wc = [m for r in bracket.rounds if r.round_name=="WC" for m in r.matchups]
    assert len(wc) == 6  # 3 per conference
    # 2v7 exists for both sides
    pairs = {(m.side, m.higher_seed_team.seed, m.lower_seed_team.seed) for m in wc}
    assert ("AFC",2,7) in pairs and ("NFC",2,7) in pairs
    # hunt cards - should have 6 total (3 per conference for teams 8-10)
    assert len(bracket.in_the_hunt) == 6
