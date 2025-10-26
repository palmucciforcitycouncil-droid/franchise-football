# Trade evaluation calibration constants

PICK_ROUND_BASE = {1: 42, 2: 26, 3: 16, 4: 10, 5: 6, 6: 4, 7: 2}
PICK_ROUND_SPREAD = {1: 8, 2: 6, 3: 4, 4: 3, 5: 2, 6: 1, 7: 1}

AGE_DECAY_START = 27  # start decaying non-QB a bit earlier
QB_AGE_DECAY_START = 30

POS_BUCKETS = {
    "OL": {"LT","LG","C","RG","RT"},
    "DB": {"CB","S"},
    "FRONT7": {"EDGE","IDL","LB"},
}

CRITICAL_POS = {"QB","K","P"}
