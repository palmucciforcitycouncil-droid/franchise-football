#!/usr/bin/env python3
"""
Fix lines 631-632 indentation
"""

def fix_lines_631_632():
    with open('app/routers/sim.py', 'r') as f:
        lines = f.readlines()
    
    # Fix the indentation - should be 16 spaces (4 levels) not 20
    lines[630] = '                emit("possession_change", {"team": other})\n'
    lines[631] = '                offense = other\n'
    
    with open('app/routers/sim.py', 'w') as f:
        f.writelines(lines)
    
    print('Fixed lines 631-632 indentation')

if __name__ == "__main__":
    fix_lines_631_632()
