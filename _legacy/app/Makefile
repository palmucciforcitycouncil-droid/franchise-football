.PHONY: qa e2e docker-build docker-run diag integrity

qa:
	pytest -q

e2e:
	pytest -q tests/e2e

diag:
	curl -s http://localhost:8000/api/admin/diagnostics | jq .

integrity:
	python -m scripts.check_integrity

docker-build:
	docker build -t franchise-football:latest .

docker-run:
	docker run --rm -p 8000:8000 franchise-football:latest

