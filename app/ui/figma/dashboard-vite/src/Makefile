# Franchise Football MVP Makefile

.PHONY: install dev test clean bench profile save load stats-game stats-season stats-career stats-validate api stats-test report weekly_awards export_season samples print_stats aggregate

# Development
install:
	pip install -r requirements.txt

dev:
	uvicorn app.ui.api:app --reload --port 8015

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
stats-game:
	python -m app.ui.cli_stats rollup --game $(GAME_ID)
	python -m app.ui.cli_stats dump-game-report --game $(GAME_ID)

stats-season:
	python -m app.ui.cli_stats materialize --scope season --year $(YEAR)

stats-career:
	python -m app.ui.cli_stats materialize --scope career

stats-validate:
	python -m app.ui.cli_stats validate --game $(GAME_ID)

api:
	uvicorn app.ui.api:app --reload --port 8015

stats-test:
	pytest tests/test_api_stats.py tests/test_stats_rollup_advanced.py tests/test_validators_advanced.py -v

report:
	python scripts/season_sanity_report.py

weekly_awards:
	python -m app.services.weekly_awards

export_season:
	python scripts/export_season_summary.py

samples:
	python scripts/print_stat_samples.py

print_stats:
	python scripts/run_and_print_stats.py --mode memory --weeks 2 --rows 200

aggregate:
	python scripts/aggregate_season.py --season $(season)

awards:
	python scripts/compute_awards.py --season $(season)

reports:
	python scripts/export_reports.py --season $(season) --out data/reports

progress:
	python scripts/apply_progression.py --season $(season) --seed 2025
