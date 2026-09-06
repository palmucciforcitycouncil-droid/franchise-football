import pytest
import os
import tempfile
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.meta import LeagueMeta
from app.services.save_service import (
    export_league, import_league, list_saves, get_save_info,
    snapshot_league, _clear_all, _dump_table, _insert_rows
)
from app.services.save_models import SaveBundle, SCHEMA_VERSION

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def temp_save_dir():
    """Create a temporary directory for save files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_dir = os.environ.get("FF_SAVE_DIR")
        os.environ["FF_SAVE_DIR"] = temp_dir
        yield temp_dir
        if original_dir:
            os.environ["FF_SAVE_DIR"] = original_dir
        else:
            os.environ.pop("FF_SAVE_DIR", None)

def test_export_and_import_roundtrip(tmp_save_dir, session):
    """
    Test complete round-trip: export -> clear -> import -> verify
    """
    # Seed a tiny league
    meta = LeagueMeta(
        current_season=2034, 
        current_week=8, 
        primary_rng_seed=111, 
        trade_rng_seed=222, 
        injury_rng_seed=333
    )
    session.add(meta)
    session.commit()

    # Export
    path = export_league("unit_test_save", gzip_enabled=True)
    assert path.endswith(".json.gz")
    assert os.path.exists(path)

    # Verify file was created
    files = list_saves()
    assert any("unit_test_save.json.gz" in f["name"] for f in files)

    # Clear database
    _clear_all(session)

    # Verify cleared
    meta_after_clear = session.exec(select(LeagueMeta)).first()
    assert meta_after_clear is None

    # Import
    res = import_league("unit_test_save")
    assert res["ok"]
    assert res["schema_version"] == SCHEMA_VERSION
    assert res["meta"]["current_season"] == 2034

    # Verify restored
    meta_after_import = session.exec(select(LeagueMeta)).first()
    assert meta_after_import is not None
    assert meta_after_import.current_season == 2034
    assert meta_after_import.current_week == 8
    assert meta_after_import.primary_rng_seed == 111

def test_export_and_import_uncompressed(tmp_save_dir, session):
    """Test export/import without gzip compression."""
    # Seed data
    meta = LeagueMeta(current_season=2035, current_week=5)
    session.add(meta)
    session.commit()

    # Export uncompressed
    path = export_league("uncompressed_test", gzip_enabled=False)
    assert path.endswith(".json")
    assert not path.endswith(".gz")
    assert os.path.exists(path)

    # Clear and import
    _clear_all(session)
    res = import_league("uncompressed_test")
    
    assert res["ok"]
    assert res["meta"]["current_season"] == 2035

def test_snapshot_league(session):
    """Test snapshot creation."""
    # Add some test data
    meta = LeagueMeta(current_season=2036, current_week=3)
    session.add(meta)
    session.commit()

    # Create snapshot
    bundle = snapshot_league(session)
    
    assert bundle.schema_version == SCHEMA_VERSION
    assert bundle.meta["current_season"] == 2036
    assert bundle.meta["current_week"] == 3

def test_list_saves(tmp_save_dir):
    """Test listing save files."""
    # Initially empty
    saves = list_saves()
    assert len(saves) == 0

    # Create some test files
    with Session(create_engine("sqlite:///:memory:")) as sess:
        meta = LeagueMeta(current_season=2037, current_week=1)
        sess.add(meta)
        sess.commit()
        
        export_league("test1", gzip_enabled=True)
        export_league("test2", gzip_enabled=False)

    # Check listing
    saves = list_saves()
    assert len(saves) == 2
    
    names = [s["name"] for s in saves]
    assert "test1.json.gz" in names
    assert "test2.json" in names

def test_get_save_info(tmp_save_dir):
    """Test getting save file information."""
    # Create a save file
    with Session(create_engine("sqlite:///:memory:")) as sess:
        meta = LeagueMeta(current_season=2038, current_week=2)
        sess.add(meta)
        sess.commit()
        
        export_league("info_test", gzip_enabled=True)

    # Get info
    info = get_save_info("info_test")
    
    assert info["schema_version"] == SCHEMA_VERSION
    assert info["compressed"] is True
    assert info["file_size"] > 0
    assert info["meta"]["current_season"] == 2038

def test_clear_all(session):
    """Test clearing all tables."""
    # Add some data
    meta1 = LeagueMeta(current_season=2039, current_week=1)
    meta2 = LeagueMeta(current_season=2040, current_week=2)
    session.add(meta1)
    session.add(meta2)
    session.commit()

    # Verify data exists
    metas = list(session.exec(select(LeagueMeta)))
    assert len(metas) == 2

    # Clear all
    _clear_all(session)

    # Verify cleared
    metas_after = list(session.exec(select(LeagueMeta)))
    assert len(metas_after) == 0

def test_dump_table(session):
    """Test dumping table data."""
    # Add test data
    meta1 = LeagueMeta(current_season=2041, current_week=1)
    meta2 = LeagueMeta(current_season=2042, current_week=2)
    session.add(meta1)
    session.add(meta2)
    session.commit()

    # Dump table
    data = _dump_table(session, LeagueMeta)
    
    assert len(data) == 2
    assert any(d["current_season"] == 2041 for d in data)
    assert any(d["current_season"] == 2042 for d in data)

def test_insert_rows(session):
    """Test inserting rows."""
    # Clear first
    _clear_all(session)

    # Prepare data
    data = [
        {"current_season": 2043, "current_week": 1, "primary_rng_seed": 100},
        {"current_season": 2044, "current_week": 2, "primary_rng_seed": 200}
    ]

    # Insert rows
    _insert_rows(session, LeagueMeta, data)

    # Verify inserted
    metas = list(session.exec(select(LeagueMeta)))
    assert len(metas) == 2
    assert any(m.current_season == 2043 for m in metas)
    assert any(m.current_season == 2044 for m in metas)

def test_save_bundle_creation():
    """Test SaveBundle model creation."""
    bundle = SaveBundle(
        schema_version="1.0",
        meta={"current_season": 2045, "current_week": 1},
        teams=[],
        players=[],
        coaches=[]
    )
    
    assert bundle.schema_version == "1.0"
    assert bundle.meta["current_season"] == 2045
    assert len(bundle.teams) == 0

def test_api_endpoints(client, seeded_db, tmp_save_dir):
    """Test API endpoints for save operations."""
    # Test export
    r = client.post("/api/v1/save/export?name=e2e_test&gzip=true")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert "path" in data
    assert "message" in data

    # Test list
    r = client.get("/api/v1/save/list")
    assert r.status_code == 200
    saves = r.json()
    assert isinstance(saves, list)
    assert len(saves) >= 1

    # Test info
    r = client.get("/api/v1/save/info/e2e_test")
    assert r.status_code == 200
    info = r.json()
    assert info["schema_version"] == SCHEMA_VERSION
    assert info["compressed"] is True

    # Test import
    r = client.post("/api/v1/save/import?name=e2e_test")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert data["schema_version"] == SCHEMA_VERSION

def test_api_backup(client, seeded_db, tmp_save_dir):
    """Test backup creation API."""
    r = client.post("/api/v1/save/backup?gzip=true")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert "backup_" in data["path"]

def test_api_validate(client, seeded_db, tmp_save_dir):
    """Test save validation API."""
    # First create a save
    client.post("/api/v1/save/export?name=validate_test&gzip=true")
    
    # Validate it
    r = client.post("/api/v1/save/validate/validate_test")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert data["valid"]
    assert data["schema_version"] == SCHEMA_VERSION
    assert len(data["issues"]) == 0

def test_api_stats(client, seeded_db, tmp_save_dir):
    """Test save statistics API."""
    # Create some saves
    client.post("/api/v1/save/export?name=stats1&gzip=true")
    client.post("/api/v1/save/export?name=stats2&gzip=false")
    
    # Get stats
    r = client.get("/api/v1/save/stats")
    assert r.status_code == 200
    stats = r.json()
    assert stats["total_saves"] >= 2
    assert stats["compressed_saves"] >= 1
    assert stats["uncompressed_saves"] >= 1
    assert stats["total_size"] > 0

def test_api_delete(client, seeded_db, tmp_save_dir):
    """Test save deletion API."""
    # Create a save
    client.post("/api/v1/save/export?name=delete_test&gzip=true")
    
    # Verify it exists
    r = client.get("/api/v1/save/list")
    saves = r.json()
    assert any("delete_test" in s["name"] for s in saves)
    
    # Delete it
    r = client.delete("/api/v1/save/delete/delete_test")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    
    # Verify it's gone
    r = client.get("/api/v1/save/list")
    saves = r.json()
    assert not any("delete_test" in s["name"] for s in saves)

def test_api_error_handling(client, seeded_db, tmp_save_dir):
    """Test API error handling."""
    # Test import non-existent file
    r = client.post("/api/v1/save/import?name=nonexistent")
    assert r.status_code == 404
    
    # Test info for non-existent file
    r = client.get("/api/v1/save/info/nonexistent")
    assert r.status_code == 404
    
    # Test validate non-existent file
    r = client.post("/api/v1/save/validate/nonexistent")
    assert r.status_code == 404
    
    # Test delete non-existent file
    r = client.delete("/api/v1/save/delete/nonexistent")
    assert r.status_code == 404

def test_schema_version_handling(tmp_save_dir, session):
    """Test schema version handling."""
    # Create save with current schema
    meta = LeagueMeta(current_season=2046, current_week=1)
    session.add(meta)
    session.commit()
    
    export_league("schema_test", gzip_enabled=True)
    
    # Import should work
    res = import_league("schema_test")
    assert res["ok"]
    assert res["schema_version"] == SCHEMA_VERSION

def test_meta_defaults(session):
    """Test meta defaults when no meta exists."""
    # Clear any existing meta
    _clear_all(session)
    
    # Create snapshot without meta
    bundle = snapshot_league(session)
    
    assert bundle.meta["current_season"] == 2031
    assert bundle.meta["current_week"] == 1
    assert bundle.meta["primary_rng_seed"] == 123456

def test_file_size_and_compression(tmp_save_dir):
    """Test file size differences between compressed and uncompressed."""
    with Session(create_engine("sqlite:///:memory:")) as sess:
        meta = LeagueMeta(current_season=2047, current_week=1)
        sess.add(meta)
        sess.commit()
        
        # Export compressed
        compressed_path = export_league("size_test_compressed", gzip_enabled=True)
        
        # Export uncompressed
        uncompressed_path = export_league("size_test_uncompressed", gzip_enabled=False)
    
    # Check file sizes
    compressed_size = os.path.getsize(compressed_path)
    uncompressed_size = os.path.getsize(uncompressed_path)
    
    assert compressed_size < uncompressed_size
    assert compressed_path.endswith(".gz")
    assert uncompressed_path.endswith(".json")

def test_multiple_meta_rows(session):
    """Test handling multiple meta rows (should use highest id)."""
    # Add multiple meta rows
    meta1 = LeagueMeta(id=1, current_season=2048, current_week=1)
    meta2 = LeagueMeta(id=2, current_season=2049, current_week=2)
    meta3 = LeagueMeta(id=3, current_season=2050, current_week=3)
    
    session.add(meta1)
    session.add(meta2)
    session.add(meta3)
    session.commit()
    
    # Snapshot should use the highest id (meta3)
    bundle = snapshot_league(session)
    assert bundle.meta["current_season"] == 2050
    assert bundle.meta["current_week"] == 3

