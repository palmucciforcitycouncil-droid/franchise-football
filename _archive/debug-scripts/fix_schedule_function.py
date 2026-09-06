# Read the file
with open('app/routers/sim.py', 'r') as f:
    lines = f.readlines()

# Find and remove the problematic lines (around line 251)
new_lines = []
skip_until_return = False
for i, line in enumerate(lines):
    if i == 250 and 'rating_diff = h_rating' in line:
        # Skip this line and the next few until we find a proper function definition
        skip_until_return = True
        # Add the correct return statement
        new_lines.append('    return weeks\n')
        new_lines.append('\n')
        continue
    elif skip_until_return:
        # Skip lines until we find a function definition
        if line.strip().startswith('def '):
            skip_until_return = False
            new_lines.append(line)
        continue
    else:
        new_lines.append(line)

# Write back
with open('app/routers/sim.py', 'w') as f:
    f.writelines(new_lines)

print("Removed problematic code from _place_rounds_into_18_weeks")
