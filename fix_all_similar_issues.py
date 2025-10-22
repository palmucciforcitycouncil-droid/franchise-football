#!/usr/bin/env python3
"""
Fix all similar indentation issues in the file
"""

def fix_all_similar_issues():
    with open('app/routers/sim.py', 'r') as f:
        lines = f.readlines()
    
    fixes = 0
    
    for i, line in enumerate(lines):
        # Fix lines that should be at 16 spaces (4 levels) but are at 20 spaces (5 levels)
        if line.startswith('                    emit("possession_change"'):
            lines[i] = '                emit("possession_change", {"team": other})\n'
            fixes += 1
        elif line.startswith('                    offense = other'):
            lines[i] = '                offense = other\n'
            fixes += 1
        elif line.startswith('                    yardline = _enforce_bounds'):
            lines[i] = '                yardline = _enforce_bounds(100 - yardline)  # simple flip for change of sides\n'
            fixes += 1
        elif line.startswith('                    forced_to_needed = max'):
            lines[i] = '                forced_to_needed = max(0, forced_to_needed - 1)\n'
            fixes += 1
        elif line.startswith('                    tick(int(r.uniform(10, 20)))'):
            lines[i] = '                tick(int(r.uniform(10, 20)))\n'
            fixes += 1
    
    with open('app/routers/sim.py', 'w') as f:
        f.writelines(lines)
    
    print(f'Applied {fixes} fixes')

if __name__ == "__main__":
    fix_all_similar_issues()
