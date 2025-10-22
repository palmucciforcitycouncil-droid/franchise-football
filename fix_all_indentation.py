#!/usr/bin/env python3
"""
Comprehensive fix for all indentation errors in sim.py
"""

def fix_all_indentation():
    # Read the current file
    with open('app/routers/sim.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total lines in file: {len(lines)}")
    
    # Fix specific problematic lines based on the error messages
    fixes_applied = 0
    
    # Fix line 270 (if not placed_game:)
    if len(lines) > 269:
        if 'if not placed_game:' in lines[269]:
            lines[269] = '                if not placed_game:\n'
            fixes_applied += 1
            print("Fixed line 270: if not placed_game:")
    
    # Fix line 388 (x = r.random())
    if len(lines) > 387:
        if 'x = r.random()' in lines[387]:
            lines[387] = '    x = r.random()\n'
            fixes_applied += 1
            print("Fixed line 388: x = r.random()")
    
    # Fix line 569 (k = _kickoff_result(r))
    if len(lines) > 568:
        if 'k = _kickoff_result(r)' in lines[568]:
            lines[568] = '                        k = _kickoff_result(r)\n'
            fixes_applied += 1
            print("Fixed line 569: k = _kickoff_result(r)")
    
    # Additional comprehensive fixes for common indentation patterns
    for i, line in enumerate(lines):
        original_line = line
        
        # Fix common indentation issues
        if line.strip().startswith('if not placed_game:'):
            # Should be at 16 spaces (4 levels)
            lines[i] = '                if not placed_game:\n'
            fixes_applied += 1
        
        elif line.strip().startswith('x = r.random()') and i > 385:
            # Should be at 4 spaces (1 level)
            lines[i] = '    x = r.random()\n'
            fixes_applied += 1
        
        elif line.strip().startswith('k = _kickoff_result(r)') and i > 565:
            # Should be at 24 spaces (6 levels)
            lines[i] = '                        k = _kickoff_result(r)\n'
            fixes_applied += 1
        
        elif line.strip().startswith('else: sa += 3') and i > 570:
            # Should be at 20 spaces (5 levels)
            lines[i] = '                    else: sa += 3\n'
            fixes_applied += 1
        
        elif line.strip().startswith('emit("kickoff"') and i > 570:
            # Should be at 24 spaces (6 levels)
            lines[i] = '                        emit("kickoff", {"by": team, **k})\n'
            fixes_applied += 1
        
        elif line.strip().startswith('emit("possession_change"') and i > 570:
            # Should be at 24 spaces (6 levels)
            lines[i] = '                        emit("possession_change", {"team": other})\n'
            fixes_applied += 1
        
        elif line.strip().startswith('offense = other') and i > 570:
            # Should be at 24 spaces (6 levels)
            lines[i] = '                        offense = other\n'
            fixes_applied += 1
        
        elif line.strip().startswith('yardline = TOUCHBACK_YARDLINE') and i > 570:
            # Should be at 24 spaces (6 levels)
            lines[i] = '                        yardline = TOUCHBACK_YARDLINE if k["touchback"] else _enforce_bounds(25 + k["return_yards"])\n'
            fixes_applied += 1
        
        elif line.strip().startswith('tick(int(r.uniform(12, 20)))') and i > 570:
            # Should be at 24 spaces (6 levels)
            lines[i] = '                        tick(int(r.uniform(12, 20)))\n'
            fixes_applied += 1
    
    # Write the fixed content
    with open('app/routers/sim.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Total fixes applied: {fixes_applied}")
    print("File fixed successfully")

if __name__ == "__main__":
    fix_all_indentation()
