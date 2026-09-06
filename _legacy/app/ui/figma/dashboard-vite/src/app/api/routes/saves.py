# app/api/routes/saves.py
from fastapi import APIRouter, HTTPException
from sqlmodel import Session
from app.db import get_engine
from app.services.save_load import list_saves, rename_save, delete_save

router = APIRouter(prefix="/saves", tags=["saves"])

def _session() -> Session: 
    return Session(get_engine())

@router.get("")
def get_saves():
    return {"items": list_saves()}

@router.post("/rename")
def post_rename(old: str, new: str):
    if not old or not new: 
        raise HTTPException(400, "old and new required")
    with _session() as s:
        try: 
            return rename_save(s, old, new)
        except FileNotFoundError as e: 
            raise HTTPException(404, str(e))

@router.delete("/{save_name}")
def delete_slot(save_name: str):
    with _session() as s:
        try: 
            return delete_save(s, save_name)
        except FileNotFoundError as e: 
            raise HTTPException(404, str(e))
