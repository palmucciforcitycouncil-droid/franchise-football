# scripts/calibrate_score.py
from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

# ---------- ensure repo root is importable ----------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# ----------------------------------------------------

import pandas as pd

from app.engine.targets import CalibrationTargets
from app.engine.calibration import calibrate

DEFAULT_SEED = 2025
