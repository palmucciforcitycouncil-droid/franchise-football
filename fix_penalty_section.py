#!/usr/bin/env python3
"""
Fix the penalty section indentation
"""

def fix_penalty_section():
    with open('app/routers/sim.py', 'r') as f:
        lines = f.readlines()
    
    # Fix the penalty section around lines 490-495
    lines[489] = '                if pen["offense"]:\n'
    lines[490] = '                    yardline = _enforce_bounds(yardline - pen["yards"])\n'
    lines[491] = '                    to_go = min(20, to_go + pen["yards"])\n'
    lines[492] = '                else:\n'
    lines[493] = '                    yardline = _enforce_bounds(yardline + pen["yards"])\n'
    lines[494] = '                    if pen["auto_first"]:\n'
    lines[495] = '                        down, to_go = 1, 10\n'
    
    with open('app/routers/sim.py', 'w') as f:
        f.writelines(lines)
    
    print('Fixed penalty section indentation')

if __name__ == "__main__":
    fix_penalty_section()
