# Read the file
with open('app/routers/sim.py', 'r') as f:
    content = f.read()

# Find and replace the duplicate _VenueState class definition
# Remove everything from "class _VenueState:" to the next non-indented line
start = content.find('class _VenueState:')
if start != -1:
    # Find the end of the class (next line that doesn't start with spaces)
    lines = content[start:].split('\n')
    end_idx = 1
    for i in range(1, len(lines)):
        if lines[i] and not lines[i].startswith(' ') and not lines[i].startswith('\t'):
            end_idx = i
            break
    
    # Replace with a clean version
    new_class = '''class _VenueState:
    def __init__(self, team_ids, season: int):
        self.team_ids = team_ids
        self.season = season
        self.home_counts = {tid: 0 for tid in team_ids}
        self.streaks = {tid: 0 for tid in team_ids}
        self.quota = {tid: _home_quota(tid, season) for tid in team_ids}
    
    def choose(self, team_a: int, team_b: int) -> tuple:
        """Choose home/away based on quotas and streaks"""
        # Simple implementation: check quotas first
        a_quota = self.quota[team_a]
        b_quota = self.quota[team_b]
        a_used = self.home_counts.get(team_a, 0)
        b_used = self.home_counts.get(team_b, 0)
        
        # Prefer team with more quota remaining
        if (a_quota - a_used) > (b_quota - b_used):
            self.home_counts[team_a] = a_used + 1
            return team_a, team_b
        elif (b_quota - b_used) > (a_quota - a_used):
            self.home_counts[team_b] = b_used + 1
            return team_b, team_a
        else:
            # Equal quotas, alternate based on team ID
            if (team_a + team_b) % 2 == 0:
                self.home_counts[team_a] = a_used + 1
                return team_a, team_b
            else:
                self.home_counts[team_b] = b_used + 1
                return team_b, team_a

'''
    
    # Reconstruct content
    before = content[:start]
    after_lines = '\n'.join(lines[end_idx:])
    content = before + new_class + '\n' + after_lines

# Write back
with open('app/routers/sim.py', 'w') as f:
    f.write(content)

print("Fixed _VenueState class with single __init__ and proper choose method")
