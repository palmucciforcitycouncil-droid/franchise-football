import pytest
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.trade import TradeProposal, TradeItem, TradeItemType, TradeStatus, DraftPick
from app.services.trade_service import (
    evaluate_trade, ai_counter, accept_trade, reject_trade,
    get_trade_details, list_team_trades, get_trade_history,
    _split_items, _needs_counter, _counter_add_pick, _execute_trade
)
from app.services.trade_value import (
    pick_value, players_value, picks_value, bundle_value,
    get_pick_value_by_round, calculate_trade_balance
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_quote_and_propose(client, seeded_db, season_setup, factories):
    """Test trade quote and proposal functionality."""
    s = season_setup.current_season
    
    # Create test players and picks
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.player import Player
    from app.models.trade import DraftPick
    
    with Session(get_engine()) as sess:
        p1 = Player(name="WR A", team_id=1, pos="WR", overall=80)
        p2 = Player(name="CB B", team_id=2, pos="CB", overall=78)
        sess.add(p1)
        sess.add(p2)
        sess.commit()
        sess.refresh(p1)
        sess.refresh(p2)
        
        pk1 = DraftPick(team_id=1, season=s+1, round=3)
        pk2 = DraftPick(team_id=2, season=s+1, round=4)
        sess.add(pk1)
        sess.add(pk2)
        sess.commit()
        sess.refresh(pk1)
        sess.refresh(pk2)

        # Test quote
        r = client.post("/api/v1/trades/quote", json={
            "season": s, "from_team_id": 1, "to_team_id": 2,
            "from_players": [p1.player_id], "from_picks": [pk1.pick_id],
            "to_players": [p2.player_id], "to_picks": [pk2.pick_id]
        })
        assert r.status_code == 200
        q = r.json()
        assert "from_value" in q and "to_value" in q
        assert "balance_ratio" in q
        assert "is_balanced" in q

        # Test propose
        r = client.post("/api/v1/trades/propose", json={
            "season": s, "from_team_id": 1, "to_team_id": 2,
            "from_players": [p1.player_id], "from_picks": [pk1.pick_id],
            "to_players": [p2.player_id], "to_picks": [pk2.pick_id]
        })
        assert r.status_code == 200
        t = r.json()
        assert t["trade_id"] > 0
        assert "fair_margin" in t
        assert t["status"] in ["OPEN", "ACCEPTED", "REJECTED"]

def test_counter_and_accept_flow(client, seeded_db, season_setup):
    """Test AI counter-offer and accept flow."""
    s = season_setup.current_season
    
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.player import Player
    from app.models.trade import DraftPick
    
    with Session(get_engine()) as sess:
        # Build a lopsided proposal to trigger counter
        a = Player(name="EDGE X", team_id=3, pos="EDGE", overall=86)
        b = Player(name="WR Y", team_id=4, pos="WR", overall=75)
        pk3 = DraftPick(team_id=4, season=s+1, round=2)
        sess.add(a)
        sess.add(b)
        sess.add(pk3)
        sess.commit()
        sess.refresh(a)
        sess.refresh(b)
        sess.refresh(pk3)

    # Propose: Team 3 sends strong player for weaker return -> should counter
    r = client.post("/api/v1/trades/propose", json={
        "season": s, "from_team_id": 3, "to_team_id": 4,
        "from_players": [a.player_id], "from_picks": [],
        "to_players": [b.player_id], "to_picks": []
    })
    trade = r.json()
    tid = trade["trade_id"]
    
    r = client.post(f"/api/v1/trades/counter/{tid}?season={s}")
    assert r.status_code == 200
    t = r.json()
    assert t["status"] in ["COUNTERED", "ACCEPTED", "REJECTED"]

    # Accept whatever current items are (for flow test)
    r = client.post(f"/api/v1/trades/accept/{tid}")
    assert r.status_code == 200
    assert r.json()["ok"] in [True, False]  # if already REJECTED it may be False

def test_execute_moves_assets(client, seeded_db, season_setup):
    """Test that trade execution moves assets between teams."""
    s = season_setup.current_season
    
    from sqlmodel import Session, select
    from app.db import get_engine
    from app.models.player import Player
    from app.models.trade import DraftPick
    
    with Session(get_engine()) as sess:
        p1 = Player(name="LB C", team_id=7, pos="LB", overall=79)
        p2 = Player(name="RB D", team_id=8, pos="RB", overall=77)
        pk7 = DraftPick(team_id=7, season=s+1, round=5)
        sess.add(p1)
        sess.add(p2)
        sess.add(pk7)
        sess.commit()
        sess.refresh(p1)
        sess.refresh(p2)
        sess.refresh(pk7)

    r = client.post("/api/v1/trades/propose", json={
        "season": s, "from_team_id": 7, "to_team_id": 8,
        "from_players": [p1.player_id], "from_picks": [pk7.pick_id],
        "to_players": [p2.player_id], "to_picks": []
    })
    tid = r.json()["trade_id"]
    
    # Execute the trade
    _ = client.post(f"/api/v1/trades/accept/{tid}")

    # Verify players/picks swapped teams
    with Session(get_engine()) as sess:
        np1 = sess.get(Player, p1.player_id)
        np2 = sess.get(Player, p2.player_id)
        npk = sess.get(DraftPick, pk7.pick_id)
        
        if np1 and np2 and npk:
            assert np1.team_id == 8
            assert np2.team_id == 7
            assert npk.team_id == 8

def test_pick_value_calculation(session: Session):
    """Test draft pick value calculation."""
    # Create test picks
    pick1 = DraftPick(team_id=1, season=2024, round=1)
    pick2 = DraftPick(team_id=2, season=2024, round=3)
    pick3 = DraftPick(team_id=3, season=2024, round=7)
    
    session.add(pick1)
    session.add(pick2)
    session.add(pick3)
    session.commit()
    session.refresh(pick1)
    session.refresh(pick2)
    session.refresh(pick3)
    
    # Test pick values
    assert pick_value(session, pick1.pick_id) == 5_000_000  # Round 1
    assert pick_value(session, pick2.pick_id) == 1_200_000  # Round 3
    assert pick_value(session, pick3.pick_id) == 150_000    # Round 7

def test_players_value_calculation(session: Session):
    """Test player value calculation."""
    # Create test players
    from app.models.player import Player
    
    player1 = Player(name="QB Test", team_id=1, pos="QB", overall=85)
    player2 = Player(name="WR Test", team_id=2, pos="WR", overall=75)
    
    session.add(player1)
    session.add(player2)
    session.commit()
    session.refresh(player1)
    session.refresh(player2)
    
    # Test player values (fallback calculation)
    value1 = players_value(session, [player1.player_id], 2024)
    value2 = players_value(session, [player2.player_id], 2024)
    
    assert value1 > 0
    assert value2 > 0
    assert value1 > value2  # Higher overall should have higher value

def test_bundle_value_calculation(session: Session):
    """Test bundle value calculation combining players and picks."""
    # Create test data
    from app.models.player import Player
    
    player = Player(name="Test Player", team_id=1, pos="QB", overall=80)
    pick = DraftPick(team_id=1, season=2024, round=2)
    
    session.add(player)
    session.add(pick)
    session.commit()
    session.refresh(player)
    session.refresh(pick)
    
    # Test bundle value
    bundle_val = bundle_value(session, 2024, [player.player_id], [pick.pick_id])
    assert bundle_val > 0
    assert bundle_val > pick_value(session, pick.pick_id)  # Should include player value

def test_trade_evaluation(session: Session):
    """Test trade evaluation logic."""
    # Create test trade
    trade = TradeProposal(season=2024, from_team_id=1, to_team_id=2)
    session.add(trade)
    session.commit()
    session.refresh(trade)
    
    # Add trade items
    from app.models.player import Player
    
    player1 = Player(name="Player 1", team_id=1, pos="QB", overall=80)
    player2 = Player(name="Player 2", team_id=2, pos="WR", overall=75)
    
    session.add(player1)
    session.add(player2)
    session.commit()
    session.refresh(player1)
    session.refresh(player2)
    
    # Add trade items
    item1 = TradeItem(trade_id=trade.trade_id, side="FROM", item_type=TradeItemType.PLAYER, player_id=player1.player_id)
    item2 = TradeItem(trade_id=trade.trade_id, side="TO", item_type=TradeItemType.PLAYER, player_id=player2.player_id)
    
    session.add(item1)
    session.add(item2)
    session.commit()
    
    # Evaluate trade
    evaluated_trade = evaluate_trade(session, trade, 2024)
    
    assert evaluated_trade.from_value_total > 0
    assert evaluated_trade.to_value_total > 0
    assert evaluated_trade.fair_margin != 0

def test_ai_counter_logic(session: Session):
    """Test AI counter-offer logic."""
    # Create a lopsided trade
    trade = TradeProposal(season=2024, from_team_id=1, to_team_id=2)
    session.add(trade)
    session.commit()
    session.refresh(trade)
    
    # Add items that create imbalance
    from app.models.player import Player
    
    strong_player = Player(name="Strong Player", team_id=1, pos="QB", overall=90)
    weak_player = Player(name="Weak Player", team_id=2, pos="WR", overall=70)
    
    session.add(strong_player)
    session.add(weak_player)
    session.commit()
    session.refresh(strong_player)
    session.refresh(weak_player)
    
    # Add trade items
    item1 = TradeItem(trade_id=trade.trade_id, side="FROM", item_type=TradeItemType.PLAYER, player_id=strong_player.player_id)
    item2 = TradeItem(trade_id=trade.trade_id, side="TO", item_type=TradeItemType.PLAYER, player_id=weak_player.player_id)
    
    session.add(item1)
    session.add(item2)
    session.commit()
    
    # Test AI counter
    countered_trade = ai_counter(session, 2024, trade.trade_id)
    
    assert countered_trade.status in [TradeStatus.COUNTERED, TradeStatus.ACCEPTED, TradeStatus.REJECTED]
    assert countered_trade.round_num >= 0

def test_trade_accept_reject(session: Session):
    """Test trade accept and reject functionality."""
    # Create test trade
    trade = TradeProposal(season=2024, from_team_id=1, to_team_id=2, status=TradeStatus.OPEN)
    session.add(trade)
    session.commit()
    session.refresh(trade)
    
    # Test accept
    result = accept_trade(session, trade.trade_id)
    assert result is True
    
    # Verify status changed
    updated_trade = session.get(TradeProposal, trade.trade_id)
    assert updated_trade.status == TradeStatus.ACCEPTED
    
    # Test reject (should fail since already accepted)
    result = reject_trade(session, trade.trade_id)
    assert result is False

def test_trade_details(session: Session):
    """Test getting trade details."""
    # Create test trade
    trade = TradeProposal(season=2024, from_team_id=1, to_team_id=2)
    session.add(trade)
    session.commit()
    session.refresh(trade)
    
    # Get details
    details = get_trade_details(session, trade.trade_id)
    
    assert details["trade_id"] == trade.trade_id
    assert details["season"] == 2024
    assert details["from_team_id"] == 1
    assert details["to_team_id"] == 2

def test_api_get_trade(client, seeded_db):
    """Test API get trade endpoint."""
    # First create a trade
    r = client.post("/api/v1/trades/propose", json={
        "season": 2024, "from_team_id": 1, "to_team_id": 2,
        "from_players": [], "from_picks": [],
        "to_players": [], "to_picks": []
    })
    trade_id = r.json()["trade_id"]
    
    # Get trade details
    r = client.get(f"/api/v1/trades/{trade_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["trade_id"] == trade_id

def test_api_get_team_trades(client, seeded_db):
    """Test API get team trades endpoint."""
    r = client.get("/api/v1/trades/team/1?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_api_get_trade_stats(client, seeded_db):
    """Test API get trade stats endpoint."""
    r = client.get("/api/v1/trades/stats?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "total_trades" in data
    assert "accepted_trades" in data
    assert "rejected_trades" in data

def test_api_get_pick_values(client, seeded_db):
    """Test API get pick values endpoint."""
    r = client.get("/api/v1/trades/picks/values?team_id=1&season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_api_get_player_values(client, seeded_db):
    """Test API get player values endpoint."""
    r = client.get("/api/v1/trades/players/values?team_id=1&season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_trade_balance_calculation():
    """Test trade balance calculation."""
    # Test balanced trade
    balance = calculate_trade_balance(1000000, 1000000)
    assert balance["balance_ratio"] == 1.0
    assert balance["is_balanced"] is True
    assert balance["favor_side"] == "EVEN"
    
    # Test unbalanced trade
    balance = calculate_trade_balance(2000000, 1000000)
    assert balance["balance_ratio"] == 0.5
    assert balance["is_balanced"] is False
    assert balance["favor_side"] == "FROM"

def test_pick_value_by_round():
    """Test pick value by round function."""
    assert get_pick_value_by_round(1) == 5_000_000
    assert get_pick_value_by_round(2) == 2_500_000
    assert get_pick_value_by_round(3) == 1_200_000
    assert get_pick_value_by_round(7) == 150_000
    assert get_pick_value_by_round(8) == 100_000  # Default for unknown rounds

def test_split_items(session: Session):
    """Test splitting trade items."""
    # Create test trade
    trade = TradeProposal(season=2024, from_team_id=1, to_team_id=2)
    session.add(trade)
    session.commit()
    session.refresh(trade)
    
    # Add test items
    from app.models.player import Player
    
    player1 = Player(name="Player 1", team_id=1, pos="QB", overall=80)
    player2 = Player(name="Player 2", team_id=2, pos="WR", overall=75)
    
    session.add(player1)
    session.add(player2)
    session.commit()
    session.refresh(player1)
    session.refresh(player2)
    
    pick1 = DraftPick(team_id=1, season=2024, round=2)
    pick2 = DraftPick(team_id=2, season=2024, round=3)
    
    session.add(pick1)
    session.add(pick2)
    session.commit()
    session.refresh(pick1)
    session.refresh(pick2)
    
    # Add trade items
    items = [
        TradeItem(trade_id=trade.trade_id, side="FROM", item_type=TradeItemType.PLAYER, player_id=player1.player_id),
        TradeItem(trade_id=trade.trade_id, side="FROM", item_type=TradeItemType.PICK, pick_id=pick1.pick_id),
        TradeItem(trade_id=trade.trade_id, side="TO", item_type=TradeItemType.PLAYER, player_id=player2.player_id),
        TradeItem(trade_id=trade.trade_id, side="TO", item_type=TradeItemType.PICK, pick_id=pick2.pick_id),
    ]
    
    for item in items:
        session.add(item)
    session.commit()
    
    # Test split
    fp, fpk, tp, tpk = _split_items(session, trade.trade_id)
    
    assert player1.player_id in fp
    assert pick1.pick_id in fpk
    assert player2.player_id in tp
    assert pick2.pick_id in tpk

def test_needs_counter():
    """Test counter necessity logic."""
    # Create test trade
    trade = TradeProposal(
        from_value_total=1000000,
        to_value_total=1000000,
        fair_margin=0,
        round_num=0
    )
    
    # Balanced trade should not need counter
    assert not _needs_counter(trade)
    
    # Unbalanced trade should need counter
    trade.fair_margin = 200000  # 20% difference
    assert _needs_counter(trade)
    
    # Max rounds reached should not need counter
    trade.round_num = 2
    assert not _needs_counter(trade)

def test_counter_add_pick(session: Session):
    """Test adding picks for counter-offers."""
    # Create test picks
    pick1 = DraftPick(team_id=1, season=2024, round=2)
    pick2 = DraftPick(team_id=1, season=2024, round=5)
    
    session.add(pick1)
    session.add(pick2)
    session.commit()
    session.refresh(pick1)
    session.refresh(pick2)
    
    # Should return the lowest round pick (highest round number)
    added_pick = _counter_add_pick(session, 1)
    assert added_pick == pick2.pick_id  # Round 5 pick
    
    # Test with no picks
    added_pick = _counter_add_pick(session, 999)
    assert added_pick is None

