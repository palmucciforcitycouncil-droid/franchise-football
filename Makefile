# Franchise Football Makefile

PYTHON=.\.venv\Scripts\python.exe

init:
	python -m venv .venv
	 -m pip install --upgrade pip
	 -m pip install -e .
	@echo "�o. Virtual environment ready, dependencies installed"
	 -c "from app.models.database import create_db_and_tables; create_db_and_tables(); print('�o. Database initialized')"
	 scripts\generate_roster.py --out app\data\generated
	 scripts\import_roster.py --from app\data\generated
	@echo "�o. Roster generated and imported with seed={LEAGUE_SEED:-2025}"

run:
	 -m uvicorn app.main:app --reload

test:
	 -m coverage run -m pytest
	 -m coverage report -m

lint:
	 -m ruff check .

fmt:
	 -m ruff format .

seed-draft:
	 scripts\seed_draft.py

seed-draft:
	$(PYTHON) scripts\seed_draft.py
