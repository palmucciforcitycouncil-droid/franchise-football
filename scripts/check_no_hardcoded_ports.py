import sys, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
BAD = [r"http://127\.0\.0\.1:8000", r"http://127\.0\.0\.1:8010",
       r"http://localhost:8000", r"http://localhost:8010"]
rx = re.compile("|".join(BAD))
bad_files = []
for p in ROOT.rglob("*.*"):
    if p.suffix in {".py",".ts",".tsx",".js",".json",".md"} and "node_modules" not in str(p) and p.name != "check_no_hardcoded_ports.py":
        try:
            s = p.read_text(encoding="utf-8", errors="ignore")
            if rx.search(s):
                bad_files.append(str(p))
        except Exception:
            pass
if bad_files:
    print("Found hardcoded localhost ports in:\n" + "\n".join(bad_files))
    sys.exit(1)
