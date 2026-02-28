# Franchise Football

Text-based American football management simulator. Python 3.11+ / FastAPI / SQLModel (SQLite) / pytest.

## Cursor Cloud specific instructions

### Project overview

Single Python application (not a monorepo). The API is in `app/ui/api.py`, models in `app/models/`, game simulation engine in `app/engine/`, and the importer in `app/services/importer/`. Database is SQLite (file-based at `db/ff.db`), no external services required.

### Running the application

Activate the venv and start the dev server:

```bash
source /workspace/.venv/bin/activate
python -m uvicorn app.ui.api:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI available at `http://localhost:8000/docs`.

### Key commands

| Task | Command |
|------|---------|
| Lint | `python -m ruff check .` |
| Format | `python -m ruff format .` |
| Test | `python -m coverage run -m pytest` |
| Coverage report | `python -m coverage report -m` |
| Dev server | `python -m uvicorn app.ui.api:app --reload` |

All commands assume the venv is activated (`source /workspace/.venv/bin/activate`).

### Gotchas

- The `Makefile` uses **Windows paths** (backslashes, `.venv\Scripts\python.exe`). On Linux, use the commands from the table above directly.
- `pyproject.toml` requires a `[tool.setuptools.packages.find]` section with `include = ["app*"]` to avoid setuptools discovering the top-level `data/` directory as a package. This has been added.
- The `get_session()` function in `app/models/database.py` is a **generator** (yields a session) designed as a FastAPI dependency. It cannot be used with `with get_session() as session:` in non-FastAPI contexts. Use `Session(get_engine())` directly instead.
- The `Player` model has `salary` and `contract_years` as **read-only properties** (not DB columns). The `scripts/import_roster.py` CLI will fail when trying to set these via `set_if_attr`. To seed data, create `Player` objects directly via SQLModel.
- `Division` enum values are uppercase (`EAST`, `NORTH`, `SOUTH`, `WEST`), while `scripts/generate_roster.py` outputs mixed-case (`East`, etc.). Use the enum constants from `app.models.team` when seeding data directly.
- Database defaults to `sqlite:///db/ff.db`. Ensure the `db/` directory exists before initializing.
- Two test files have pre-existing collection errors: `test_calibration_acceptance.py` (syntax error) and `test_db_helpers.py` (imports non-existent `session_scope`). Additional test failures in `test_importer_ingest.py` stem from the `get_session()` generator issue. These are pre-existing and not caused by environment setup.
