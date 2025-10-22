#!/usr/bin/env python3
"""
Fix line 631 indentation
"""

def fix_line_631():
    with open('app/routers/sim.py', 'r') as f:
        lines = f.readlines()
    
    # Fix line 631 specifically
    if len(lines) > 630:
        lines[630] = '                    emit("possession_change", {"team": other})\n'
    
    with open('app/routers/sim.py', 'w') as f:
        f.writelines(lines)
    
    print('Fixed line 631')

if __name__ == "__main__":
    fix_line_631()
