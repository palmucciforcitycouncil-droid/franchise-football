# Franchise Football MVP Makefile

.PHONY: install dev test clean bench profile save load stats-rollup stats-materialize stats-validate stats-leaders stats-teams stats-test

# Development
install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Performance testing
bench:
	python -m scripts.benchmark_season

profile:
	python -m scripts.profile_sim

# Save/Load operations (requires server running)
save:
	curl -s -X POST http://localhost:8000/api/save > /tmp/league.json && echo "Saved to /tmp/league.json"

load:
	curl -s -X POST http://localhost:8000/api/load -H 'Content-Type: application/json' --data-binary @/tmp/league.json && echo "Loaded from /tmp/league.json"

# Stats operations
stats-rollup:
	python stats_cli.py rollup $(GAME_ID)

stats-materialize:
	python stats_cli.py materialize $(SEASON)

stats-validate:
	python stats_cli.py validate $(SEASON) $(if $(GAME_ID),--game $(GAME_ID))

stats-leaders:
	python stats_cli.py leaders $(SEASON) $(STAT) $(if $(TOP),--top $(TOP))

stats-teams:
	python stats_cli.py teams $(SEASON) $(if $(TEAM_ID),--team $(TEAM_ID))

stats-test:
	python comprehensive_stats_test.py
