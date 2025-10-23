# scripts/manage_saves.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse, json
from sqlmodel import Session
from app.db import get_engine
from app.services.save_load import list_saves, rename_save, delete_save

def main():
    ap = argparse.ArgumentParser(description="Manage save slots")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--rename", nargs=2, metavar=("OLD","NEW"))
    g.add_argument("--delete", metavar="NAME")
    args = ap.parse_args()

    with Session(get_engine()) as s:
        if args.list:
            print(json.dumps({"items": list_saves()}, indent=2))
        elif args.rename:
            old, new = args.rename
            print(json.dumps(rename_save(s, old, new), indent=2))
        elif args.delete:
            print(json.dumps(delete_save(s, args.delete), indent=2))

if __name__ == "__main__":
    main()
