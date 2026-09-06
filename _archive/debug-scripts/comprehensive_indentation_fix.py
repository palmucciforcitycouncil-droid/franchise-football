#!/usr/bin/env python3
"""
Comprehensive indentation fix for sim.py
"""

def fix_all_indentation_errors():
    with open('app/routers/sim.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    
    # Fix specific problematic lines based on error messages
    fixes = 0
    
    # Fix line 270 - if not placed_game:
    if len(lines) > 269:
        if 'if not placed_game:' in lines[269]:
            lines[269] = '                if not placed_game:\n'
            fixes += 1
            print("Fixed line 270: if not placed_game:")
    
    # Fix line 491 - yardline = _enforce_bounds(100 - yardline)
    if len(lines) > 490:
        if 'yardline = _enforce_bounds(100 - yardline)' in lines[490]:
            lines[490] = '                    yardline = _enforce_bounds(100 - yardline)  # simple flip for change of sides\n'
            fixes += 1
            print("Fixed line 491: yardline assignment")
    
    # Fix line 513 - emit("play", ...)
    if len(lines) > 512:
        if 'emit("play", {"team": team, "play": "pass", "is_sack": True' in lines[512]:
            lines[512] = '                    emit("play", {"team": team, "play": "pass", "is_sack": True, "complete": False, "yards": y, "down": down, "to_go": to_go, "yardline": start_yl})\n'
            fixes += 1
            print("Fixed line 513: emit play")
    
    # Additional comprehensive fixes for common patterns
    for i, line in enumerate(lines):
        original = line
        
        # Fix common indentation issues
        if line.strip().startswith('if not placed_game:'):
            lines[i] = '                if not placed_game:\n'
            fixes += 1
        
        elif line.strip().startswith('yardline = _enforce_bounds(100 - yardline)'):
            lines[i] = '                    yardline = _enforce_bounds(100 - yardline)  # simple flip for change of sides\n'
            fixes += 1
        
        elif line.strip().startswith('emit("play", {"team": team, "play": "pass", "is_sack": True'):
            lines[i] = '                    emit("play", {"team": team, "play": "pass", "is_sack": True, "complete": False, "yards": y, "down": down, "to_go": to_go, "yardline": start_yl})\n'
            fixes += 1
        
        elif line.strip().startswith('to_go = min(20, to_go - y)'):
            lines[i] = '                    to_go = min(20, to_go - y)  # y is negative → to_go increases\n'
            fixes += 1
        
        elif line.strip().startswith('tick(CLOCK_TICK_SACK)'):
            lines[i] = '                    tick(CLOCK_TICK_SACK)\n'
            fixes += 1
        
        elif line.strip().startswith('else:'):
            # Check if this is part of the penalty section
            if i > 485 and i < 500:
                lines[i] = '                else:\n'
                fixes += 1
        
        elif line.strip().startswith('yardline = _enforce_bounds(yardline + pen["yards"])'):
            lines[i] = '                    yardline = _enforce_bounds(yardline + pen["yards"])\n'
            fixes += 1
        
        elif line.strip().startswith('if pen["auto_first"]:'):
            lines[i] = '                    if pen["auto_first"]:\n'
            fixes += 1
        
        elif line.strip().startswith('down, to_go = 1, 10'):
            lines[i] = '                        down, to_go = 1, 10\n'
            fixes += 1
    
    # Write the fixed content
    with open('app/routers/sim.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Total fixes applied: {fixes}")

if __name__ == "__main__":
    fix_all_indentation_errors()
