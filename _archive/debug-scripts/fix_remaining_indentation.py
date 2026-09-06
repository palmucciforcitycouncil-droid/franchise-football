#!/usr/bin/env python3
"""
Comprehensive fix for all remaining indentation errors
"""

def fix_all_remaining_indentation():
    with open('app/routers/sim.py', 'r') as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    
    # Find and fix all indentation issues systematically
    fixes = 0
    
    for i, line in enumerate(lines):
        original = line
        
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            continue
            
        # Fix specific patterns that are causing issues
        if 'emit("possession_change"' in line and i > 575:
            # Should be at 20 spaces (5 levels)
            lines[i] = '                    emit("possession_change", {"team": other})\n'
            fixes += 1
            
        elif 'offense = other' in line and i > 575:
            # Should be at 20 spaces (5 levels)
            lines[i] = '                    offense = other\n'
            fixes += 1
            
        elif 'yardline = TOUCHBACK_YARDLINE' in line and i > 575:
            # Should be at 20 spaces (5 levels)
            lines[i] = '                    yardline = TOUCHBACK_YARDLINE if k["touchback"] else _enforce_bounds(25 + k["return_yards"])\n'
            fixes += 1
            
        elif 'tick(int(r.uniform(12, 20)))' in line and i > 575:
            # Should be at 20 spaces (5 levels)
            lines[i] = '                    tick(int(r.uniform(12, 20)))\n'
            fixes += 1
            
        elif 'break' in line and i > 575 and len(line.strip()) == 4:
            # Should be at 20 spaces (5 levels)
            lines[i] = '                    break\n'
            fixes += 1
    
    # Write the fixed content
    with open('app/routers/sim.py', 'w') as f:
        f.writelines(lines)
    
    print(f"Applied {fixes} fixes")

if __name__ == "__main__":
    fix_all_remaining_indentation()
