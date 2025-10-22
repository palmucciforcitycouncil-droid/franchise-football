#!/usr/bin/env python3
"""
Comprehensive indentation fix for sim.py - Final comprehensive fix
"""

def fix_all_indentation_comprehensive():
    with open('app/routers/sim.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    
    # Find the _simulate_pbp_for_game_v2 function and fix its indentation
    in_function = False
    function_start = -1
    fixes = 0
    
    for i, line in enumerate(lines):
        # Detect start of function
        if 'def _simulate_pbp_for_game_v2(' in line:
            in_function = True
            function_start = i
            print(f"Found function at line {i+1}")
            continue
        
        # If we're in the function, fix indentation
        if in_function:
            # Check if we've reached the end of the function
            if line.strip() and not line.startswith('    ') and not line.startswith('\t') and not line.startswith('#'):
                if i > function_start + 10:  # Make sure we're not at the start
                    # This might be the end of the function
                    if 'def ' in line and len(line) - len(line.lstrip()) <= 4:
                        in_function = False
                        print(f"End of function at line {i+1}")
                        continue
            
            # Fix common indentation patterns within the function
            original = line
            
            # Fix specific problematic lines
            if 'if not placed_game:' in line:
                lines[i] = '                if not placed_game:\n'
                fixes += 1
            elif 'yardline = _enforce_bounds(100 - yardline)' in line:
                lines[i] = '                    yardline = _enforce_bounds(100 - yardline)  # simple flip for change of sides\n'
                fixes += 1
            elif 'emit("play", {"team": team, "play": "pass", "is_sack": True' in line:
                lines[i] = '                    emit("play", {"team": team, "play": "pass", "is_sack": True, "complete": False, "yards": y, "down": down, "to_go": to_go, "yardline": start_yl})\n'
                fixes += 1
            elif 'down, to_go = 1, 10' in line and i > 480 and i < 485:
                lines[i] = '        down, to_go = 1, 10\n'
                fixes += 1
            elif 'down, to_go = 1, 10' in line and i > 525 and i < 535:
                lines[i] = '                            down, to_go = 1, 10\n'
                fixes += 1
            elif 'yardline = TOUCHBACK_YARDLINE if k["touchback"]' in line:
                lines[i] = '                    yardline = TOUCHBACK_YARDLINE if k["touchback"] else _enforce_bounds(25 + k["return_yards"])\n'
                fixes += 1
            elif 'to_go = min(20, to_go - y)' in line:
                lines[i] = '                    to_go = min(20, to_go - y)  # y is negative → to_go increases\n'
                fixes += 1
            elif 'tick(CLOCK_TICK_SACK)' in line:
                lines[i] = '                    tick(CLOCK_TICK_SACK)\n'
                fixes += 1
            elif 'else:' in line and i > 485 and i < 500:
                lines[i] = '                else:\n'
                fixes += 1
            elif 'yardline = _enforce_bounds(yardline + pen["yards"])' in line:
                lines[i] = '                    yardline = _enforce_bounds(yardline + pen["yards"])\n'
                fixes += 1
            elif 'if pen["auto_first"]:' in line:
                lines[i] = '                    if pen["auto_first"]:\n'
                fixes += 1
            elif 'down, to_go = 1, 10' in line and i > 495 and i < 500:
                lines[i] = '                        down, to_go = 1, 10\n'
                fixes += 1
    
    # Write the fixed content
    with open('app/routers/sim.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Total fixes applied: {fixes}")
    print("File fixed successfully")

if __name__ == "__main__":
    fix_all_indentation_comprehensive()
