#!/usr/bin/env python3
"""
Comprehensive indentation fix for sim.py - Final attempt
"""

def fix_all_indentation_final():
    with open('app/routers/sim.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    
    # Create a mapping of problematic lines and their correct indentation
    fixes = [
        (269, '                if not placed_game:\n'),  # Line 270
        (490, '                    yardline = _enforce_bounds(100 - yardline)  # simple flip for change of sides\n'),  # Line 491
        (512, '                    emit("play", {"team": team, "play": "pass", "is_sack": True, "complete": False, "yards": y, "down": down, "to_go": to_go, "yardline": start_yl})\n'),  # Line 513
        (481, '        down, to_go = 1, 10\n'),  # Line 482
        (528, '                            down, to_go = 1, 10\n'),  # Line 529
        (572, '                    yardline = TOUCHBACK_YARDLINE if k["touchback"] else _enforce_bounds(25 + k["return_yards"])\n'),  # Line 573
    ]
    
    applied_fixes = 0
    
    for line_num, correct_line in fixes:
        if line_num < len(lines):
            original = lines[line_num]
            lines[line_num] = correct_line
            applied_fixes += 1
            print(f"Fixed line {line_num + 1}: {original.strip()[:50]}...")
    
    # Additional pattern-based fixes
    for i, line in enumerate(lines):
        original = line
        
        # Fix common patterns
        if line.strip() == 'if not placed_game:':
            lines[i] = '                if not placed_game:\n'
            applied_fixes += 1
        
        elif line.strip().startswith('yardline = _enforce_bounds(100 - yardline)'):
            lines[i] = '                    yardline = _enforce_bounds(100 - yardline)  # simple flip for change of sides\n'
            applied_fixes += 1
        
        elif line.strip().startswith('emit("play", {"team": team, "play": "pass", "is_sack": True'):
            lines[i] = '                    emit("play", {"team": team, "play": "pass", "is_sack": True, "complete": False, "yards": y, "down": down, "to_go": to_go, "yardline": start_yl})\n'
            applied_fixes += 1
        
        elif line.strip() == 'down, to_go = 1, 10' and i > 480 and i < 485:
            lines[i] = '        down, to_go = 1, 10\n'
            applied_fixes += 1
        
        elif line.strip() == 'down, to_go = 1, 10' and i > 525 and i < 535:
            lines[i] = '                            down, to_go = 1, 10\n'
            applied_fixes += 1
        
        elif line.strip().startswith('yardline = TOUCHBACK_YARDLINE if k["touchback"]'):
            lines[i] = '                    yardline = TOUCHBACK_YARDLINE if k["touchback"] else _enforce_bounds(25 + k["return_yards"])\n'
            applied_fixes += 1
    
    # Write the fixed content
    with open('app/routers/sim.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Total fixes applied: {applied_fixes}")
    print("File fixed successfully")

if __name__ == "__main__":
    fix_all_indentation_final()
