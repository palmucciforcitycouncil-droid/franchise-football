from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.save_service import export_league, import_league, list_saves, get_save_info

router = APIRouter(prefix="/api/v1/save", tags=["save"])

class SaveFileDTO(BaseModel):
    name: str
    path: str

class SaveInfoDTO(BaseModel):
    schema_version: str
    meta: Dict[str, Any]
    file_size: int
    compressed: bool

@router.get("/list", response_model=List[SaveFileDTO])
def list_files():
    """List all available save files."""
    return list_saves()

@router.get("/info/{name}", response_model=SaveInfoDTO)
def get_save_file_info(name: str):
    """Get information about a specific save file."""
    try:
        info = get_save_info(name)
        return SaveInfoDTO(**info)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

class ExportRes(BaseModel):
    ok: bool
    path: str
    message: str

@router.post("/export", response_model=ExportRes)
def export(name: str = Query(..., description="slug file name (no extension)"), gzip: bool = True):
    """Export current league state to a save file."""
    try:
        path = export_league(name, gzip_enabled=gzip)
        return ExportRes(
            ok=True, 
            path=path,
            message=f"League exported successfully to {path}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

class ImportRes(BaseModel):
    ok: bool
    schema_version: str
    meta: Dict[str, Any]
    message: str

@router.post("/import", response_model=ImportRes)
def import_(name: str = Query(..., description="slug file name (no extension)")):
    """Import a league from a save file."""
    try:
        res = import_league(name)
        return ImportRes(
            **res,
            message=f"League imported successfully from {name}"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

class BackupRes(BaseModel):
    ok: bool
    path: str
    message: str

@router.post("/backup", response_model=BackupRes)
def create_backup(gzip: bool = True):
    """Create a backup of the current league state."""
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}"
    
    try:
        path = export_league(backup_name, gzip_enabled=gzip)
        return BackupRes(
            ok=True,
            path=path,
            message=f"Backup created successfully: {backup_name}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

class DeleteRes(BaseModel):
    ok: bool
    message: str

@router.delete("/delete/{name}", response_model=DeleteRes)
def delete_save(name: str):
    """Delete a save file."""
    import os
    from app.services.save_service import DUMP_DIR
    
    # Try both .json and .json.gz extensions
    json_path = os.path.join(DUMP_DIR, f"{name}.json")
    gz_path = os.path.join(DUMP_DIR, f"{name}.json.gz")
    
    deleted = False
    if os.path.exists(json_path):
        os.remove(json_path)
        deleted = True
    if os.path.exists(gz_path):
        os.remove(gz_path)
        deleted = True
    
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Save file '{name}' not found")
    
    return DeleteRes(
        ok=True,
        message=f"Save file '{name}' deleted successfully"
    )

class ValidateRes(BaseModel):
    ok: bool
    valid: bool
    schema_version: str
    issues: List[str]

@router.post("/validate/{name}", response_model=ValidateRes)
def validate_save(name: str):
    """Validate a save file without importing it."""
    try:
        info = get_save_info(name)
        issues = []
        
        # Check schema version
        if info["schema_version"] != "1.0":
            issues.append(f"Schema version mismatch: {info['schema_version']} (expected 1.0)")
        
        # Check meta data
        meta = info.get("meta", {})
        required_meta = ["current_season", "current_week"]
        for field in required_meta:
            if field not in meta:
                issues.append(f"Missing required meta field: {field}")
        
        return ValidateRes(
            ok=True,
            valid=len(issues) == 0,
            schema_version=info["schema_version"],
            issues=issues
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return ValidateRes(
            ok=False,
            valid=False,
            schema_version="unknown",
            issues=[f"Validation error: {str(e)}"]
        )

class StatsRes(BaseModel):
    total_saves: int
    total_size: int
    compressed_saves: int
    uncompressed_saves: int

@router.get("/stats", response_model=StatsRes)
def get_save_stats():
    """Get statistics about save files."""
    saves = list_saves()
    
    total_size = 0
    compressed_saves = 0
    uncompressed_saves = 0
    
    for save in saves:
        try:
            info = get_save_info(save["name"].replace(".json", "").replace(".gz", ""))
            total_size += info["file_size"]
            if info["compressed"]:
                compressed_saves += 1
            else:
                uncompressed_saves += 1
        except Exception:
            # Skip files we can't read
            continue
    
    return StatsRes(
        total_saves=len(saves),
        total_size=total_size,
        compressed_saves=compressed_saves,
        uncompressed_saves=uncompressed_saves
    )

