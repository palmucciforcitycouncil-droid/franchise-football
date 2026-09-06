import os
import re
from pathlib import Path

# Banned identifiers outside the seed helper or docs:
BANNED = (r"\bDEFAULT_SEED\b", r"\bseason_seed\b")

# Allowlist paths (regex, normalized with forward slashes)
ALLOW = [
        r"^app/core/seed\.py$", r"^app/core/config\.py$", r"^app/core/seed\.py$",                # canonical helper is allowed to mention legacy names in fallback/comments
    r"^tests/test_seed_naming_guard\.py$", # this file
    r"^\.env(\.example)?$",                # env files
    r"(^|.*/)README(\.md)?$",              # readmes
    r"(^|.*/)GDD.*\.md$",                  # design docs
    r"(^|.*/)docs/.*",                     # docs folder if present
]

# Ignore large/noise directories & file types
IGNORE_DIRS = {"htmlcov", ".git", ".venv", "data", "db", "__pycache__", ".pytest_cache", "node_modules", "dist", "build", ".mypy_cache"}
IGNORE_EXTS = {".png",".jpg",".jpeg",".gif",".pdf",".parquet",".csv",".zip",".gz",".xz",".ico",".sqlite",".db",".bin",".pkl",".pickle",".exe",".dll",".bat",".ps1"}

def is_allowed(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    return any(re.search(pat, rel) for pat in ALLOW)

def test_no_legacy_seed_names():
    repo = Path(__file__).resolve().parents[1]
    offenders = []

    for root, dirs, files in os.walk(repo):
        # prune ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            p = Path(root, fname)
            rel = p.relative_to(repo).as_posix()

            if is_allowed(rel):
                continue

            if p.suffix.lower() in IGNORE_EXTS:
                continue

            # skip obvious backups
            base = p.name.lower()
            if base.endswith((".bak",".old",".tmp",".orig")):
                continue

            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                # If not text, skip
                continue

            # Skip pure comments-only lines check for speed? Keep simple: direct grep
            for pat in BANNED:
                if re.search(pat, text):
                    offenders.append(rel)
                    break

    assert not offenders, (
        "Legacy seed identifiers found in codebase:\n" +
        "\n".join(sorted(offenders)) +
        "\n\nUse get_league_seed()/make_rng() and the LEAGUE_SEED name only."
    )

