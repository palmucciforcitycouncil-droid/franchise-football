#!/usr/bin/env python3
"""
Fix the indentation error in sim.py by rewriting the problematic function
"""

def fix_sim_file():
    # Read the current file
    with open('app/routers/sim.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the problematic function
    old_function = '''def _place_rounds_into_18_weeks(team_ids: List[int], season:int, rounds: List[List[Tuple[int,int]]]) -> Dict[int, List[Tuple[int,int]]]:
    """Place rounds into 18 weeks with proper scheduling."""
    byes = _assign_byes(team_ids, season)
    weeks: Dict[int, List[Tuple[int,int]]] = {w: [] for w in range(1, 19)}
    team_week_busy: Dict[Tuple[int,int], bool] = {}
    
    # Place each round of games
    for r_pairs in rounds:
        placed = False
        # First try to place the entire round in one week
        for wk in range(1, 19):
            if any(byes[a] == wk or byes[b] == wk for (a,b) in r_pairs): continue
            if any(team_week_busy.get((a, wk)) or team_week_busy.get((b, wk)) for (a,b) in r_pairs): continue
            if len(weeks[wk]) + len(r_pairs) > 16: continue
            weeks[wk].extend(r_pairs)
            for (a,b) in r_pairs:
                team_week_busy[(a, wk)] = True
                team_week_busy[(b, wk)] = True
            placed = True
            break
        
        # If entire round couldn't be placed, place games individually
        if not placed:
            for (a,b) in r_pairs:
                placed_game = False
                for wk in range(1, 19):
                    if byes[a] == wk or byes[b] == wk: continue
                    if team_week_busy.get((a, wk)) or team_week_busy.get((b, wk)): continue
                    if len(weeks[wk]) < 16:
                        weeks[wk].append((a,b))
                        team_week_busy[(a, wk)] = True
                        team_week_busy[(b, wk)] = True
                        placed_game = True
                        break
                if not placed_game:
                    # Force placement in first available week
                    for wk in range(1, 19):
                        if byes[a] != wk and byes[b] != wk and len(weeks[wk]) < 16:
                            weeks[wk].append((a,b))
                            team_week_busy[(a, wk)] = True
                            team_week_busy[(b, wk)] = True
                            break
    
    return weeks'''
    
    new_function = '''def _place_rounds_into_18_weeks(team_ids: List[int], season:int, rounds: List[List[Tuple[int,int]]]) -> Dict[int, List[Tuple[int,int]]]:
    """Place rounds into 18 weeks with proper scheduling."""
    byes = _assign_byes(team_ids, season)
    weeks: Dict[int, List[Tuple[int,int]]] = {w: [] for w in range(1, 19)}
    team_week_busy: Dict[Tuple[int,int], bool] = {}
    
    # Place each round of games
    for r_pairs in rounds:
        placed = False
        # First try to place the entire round in one week
        for wk in range(1, 19):
            if any(byes[a] == wk or byes[b] == wk for (a,b) in r_pairs): continue
            if any(team_week_busy.get((a, wk)) or team_week_busy.get((b, wk)) for (a,b) in r_pairs): continue
            if len(weeks[wk]) + len(r_pairs) > 16: continue
            weeks[wk].extend(r_pairs)
            for (a,b) in r_pairs:
                team_week_busy[(a, wk)] = True
                team_week_busy[(b, wk)] = True
            placed = True
            break
        
        # If entire round couldn't be placed, place games individually
        if not placed:
            for (a,b) in r_pairs:
                placed_game = False
                for wk in range(1, 19):
                    if byes[a] == wk or byes[b] == wk: continue
                    if team_week_busy.get((a, wk)) or team_week_busy.get((b, wk)): continue
                    if len(weeks[wk]) < 16:
                        weeks[wk].append((a,b))
                        team_week_busy[(a, wk)] = True
                        team_week_busy[(b, wk)] = True
                        placed_game = True
                        break
                if not placed_game:
                    # Force placement in first available week
                    for wk in range(1, 19):
                        if byes[a] != wk and byes[b] != wk and len(weeks[wk]) < 16:
                            weeks[wk].append((a,b))
                            team_week_busy[(a, wk)] = True
                            team_week_busy[(b, wk)] = True
                            break
    
    return weeks'''
    
    # Replace the function
    if old_function in content:
        content = content.replace(old_function, new_function)
        print("Function replaced successfully")
    else:
        print("Function not found, trying alternative approach")
        # Try to find and replace just the problematic section
        lines = content.split('\n')
        new_lines = []
        in_problematic_section = False
        skip_until_return = False
        
        for i, line in enumerate(lines):
            if 'if not placed_game:' in line and i > 260:
                # Fix the indentation
                new_lines.append('                if not placed_game:')
                skip_until_return = True
            elif skip_until_return and 'return weeks' in line:
                new_lines.append(line)
                skip_until_return = False
            elif skip_until_return:
                # Skip the problematic lines
                continue
            else:
                new_lines.append(line)
        
        content = '\n'.join(new_lines)
        print("Problematic section fixed")
    
    # Write the fixed content
    with open('app/routers/sim.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("File fixed successfully")

if __name__ == "__main__":
    fix_sim_file()
