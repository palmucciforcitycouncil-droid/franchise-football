#!/usr/bin/env python3
"""
Fix the specific indentation issue around lines 565-575
"""

def fix_specific_section():
    with open('app/routers/sim.py', 'r') as f:
        lines = f.readlines()
    
    # Fix the problematic section around lines 565-575
    lines[564] = '                    if good:\n'
    lines[565] = '                        if team == "home": sh += 3\n'
    lines[566] = '                        else: sa += 3\n'
    lines[567] = '                    # kickoff after FG\n'
    lines[568] = '                    k = _kickoff_result(r)\n'
    lines[569] = '                    emit("kickoff", {"by": team, **k})\n'
    lines[570] = '                    emit("possession_change", {"team": other})\n'
    lines[571] = '                    offense = other\n'
    lines[572] = '                    yardline = TOUCHBACK_YARDLINE if k["touchback"] else _enforce_bounds(25 + k["return_yards"])\n'
    lines[573] = '                    tick(int(r.uniform(12, 20)))\n'
    
    with open('app/routers/sim.py', 'w') as f:
        f.writelines(lines)
    
    print('Fixed lines 565-575 indentation')

if __name__ == "__main__":
    fix_specific_section()
