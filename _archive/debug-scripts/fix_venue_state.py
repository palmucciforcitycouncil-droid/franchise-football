# Read the file
with open('app/routers/sim.py', 'r') as f:
    content = f.read()

# Find the _VenueState class and add the missing methods
venue_state_start = content.find('class _VenueState:')
venue_state_end = content.find('\n\n', venue_state_start)

# Add the missing methods
new_methods = '''
    def __init__(self, team_ids, season: int):
        self.team_ids = team_ids
        self.season = season
        self.home_counts = {tid: 0 for tid in team_ids}
        self.streaks = {tid: 0 for tid in team_ids}  # positive = home streak, negative = away streak
        
    def choose(self, team_a: int, team_b: int) -> tuple:
        """Choose home/away based on quotas and streaks"""
        # Simple implementation: alternate based on team ID
        if (team_a + team_b) % 2 == 0:
            return team_a, team_b
        else:
            return team_b, team_a
'''

# Insert the methods after the class definition
content = content[:venue_state_end] + new_methods + content[venue_state_end:]

# Write back
with open('app/routers/sim.py', 'w') as f:
    f.write(content)

print("Added missing _VenueState methods")
