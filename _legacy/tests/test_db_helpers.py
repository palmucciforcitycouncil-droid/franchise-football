from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import text  # 👈 wrap SQL strings with text()
from app.models.database import get_engine, create_db_and_tables, session_scope
from app.models import Team, Conference, Division

def test_get_engine_default_and_create(tmp_path):
    url = f"sqlite:///{tmp_path/'x.db'}"
    # create tables via helper
    create_db_and_tables(url)
    # engine opens with sqlite connect args set
    eng = get_engine(url)
    with eng.connect() as conn:
        # SQLAlchemy 2.x: wrap raw SQL in text()
        res = conn.execute(text("select 1")).scalar()
        assert res == 1

def test_session_scope_context(tmp_path):
    url = f"sqlite:///{tmp_path/'y.db'}"
    create_db_and_tables(url)
    with session_scope(url) as s:  # type: Session
        t = Team(location_name="Testville", nickname="Generics", conference=Conference.AFC, division=Division.EAST)
        s.add(t)
    # after context, row is committed
    eng = get_engine(url)
    with eng.connect() as conn:
        count = conn.execute(text("select count(*) from teams")).scalar()
        assert count == 1
