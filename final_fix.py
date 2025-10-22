#!/usr/bin/env python3
"""
Final comprehensive fix for all indentation errors
"""

def final_fix():
    with open('app/routers/sim.py', 'r') as f:
        lines = f.readlines()
    
    # Fix the specific problematic section around lines 615-625
    lines[614] = '                    good = _fg_success(r, yardline)\n'
    lines[615] = '                    emit("field_goal", {"team": team, "attempt": 1, "good": 1 if good else 0, "yardline": yardline})\n'
    lines[616] = '                    if good:\n'
    lines[617] = '                        if team == "home": sh += 3\n'
    lines[618] = '                        else: sa += 3\n'
    lines[619] = '                    # kickoff after FG\n'
    lines[620] = '                    k = _kickoff_result(r)\n'
    lines[621] = '                    emit("kickoff", {"by": team, **k})\n'
    lines[622] = '                    emit("possession_change", {"team": other})\n'
    lines[623] = '                    offense = other\n'
    lines[624] = '                    yardline = TOUCHBACK_YARDLINE if k["touchback"] else _enforce_bounds(25 + k["return_yards"])\n'
    lines[625] = '                    tick(int(r.uniform(12, 20)))\n'
    
    with open('app/routers/sim.py', 'w') as f:
        f.writelines(lines)
    
    print('Fixed lines 615-625')

if __name__ == "__main__":
    final_fix()
