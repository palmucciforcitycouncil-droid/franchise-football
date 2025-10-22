#!/usr/bin/env python3
"""
Fix indentation in sim.py
"""

def fix_indentation():
    with open('app/routers/sim.py', 'rb') as f:
        content = f.read()
    
    lines = content.split(b'\n')
    
    # Fix line 270 (index 269) - it should have 20 spaces, not 16
    if len(lines) > 269:
        line = lines[269]
        if line.startswith(b'                if not placed_game:'):
            # Replace with correct indentation (20 spaces)
            lines[269] = b'                if not placed_game:'
            print("Fixed line 270 indentation")
    
    # Write back
    with open('app/routers/sim.py', 'wb') as f:
        f.write(b'\n'.join(lines))
    
    print("Indentation fixed")

if __name__ == "__main__":
    fix_indentation()
