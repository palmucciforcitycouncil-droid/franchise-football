#!/usr/bin/env python3
"""
Demonstration of Run & Print Stats Now functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_and_print_stats import run_from_db, run_in_memory_and_print, maybe_export_csv


def demo_run_and_print_stats():
    """Demonstrate the Run & Print Stats Now functionality."""
    print("Run & Print Stats Now - Comprehensive Demo")
    print("=" * 50)
    
    print("\n1. Memory Mode Demo (Fresh Mini Season)")
    print("-" * 40)
    try:
        run_in_memory_and_print(rows=20, weeks=2)
    except Exception as e:
        print(f"Memory mode demo failed: {e}")
    
    print("\n2. Database Mode Demo (Empty Database)")
    print("-" * 40)
    try:
        run_from_db("sqlite:///:memory:", rows=10)
    except Exception as e:
        print(f"Database mode demo failed: {e}")
    
    print("\n3. CSV Export Demo")
    print("-" * 40)
    try:
        maybe_export_csv("sqlite:///:memory:", rows=10, out_prefix="data/reports/demo_samples")
        print("CSV export completed (files may be empty due to no data)")
    except Exception as e:
        print(f"CSV export demo failed: {e}")
    
    print("\n" + "=" * 50)
    print("Demo completed!")
    print("\nUsage Examples:")
    print("  python scripts/run_and_print_stats.py --mode memory --weeks 3 --rows 200")
    print("  python scripts/run_and_print_stats.py --mode db --db sqlite:///franchise.db --rows 300")
    print("  python scripts/run_and_print_stats.py --mode db --rows 500 --csv-prefix data/reports/samples")


if __name__ == "__main__":
    demo_run_and_print_stats()
