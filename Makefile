# Franchise Football Makefile

PYTHON=.\.venv\Scripts\python.exe

init:
	python -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .
	@echo "✅ Virtual environment ready, dependencies installed"
	$(PYTHON) -c "from app.models.database import create_db_and_tables; create_db_and_tables(); print('✅ Database initialized')"
	$(PYTHON) scripts\generate_roster.py --out app\data\generated
	$(PYTHON) scripts\import_roster.py --from app\data\generated
	@echo "✅ Roster generated and imported with seed=$${DEFAULT_SEED:-2025}"

run:
	$(PYTHON) -m uvicorn app.ui.main:app --reload

test:
	$(PYTHON) -m coverage run -m pytest
	$(PYTHON) -m coverage report -m

lint:
	$(PYTHON) -m ruff check .

fmt:
	$(PYTHON) -m ruff format .
