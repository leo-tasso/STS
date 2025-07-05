# Re-import necessary libraries after kernel reset
import matplotlib.pyplot as plt

# Manually re-enter the data extracted from the two tables
data = {
    'n': [6, 8, 10, 12, 14],
    'CBC (all)':      [0, 0, 1, 15, 29],
    'CBC w/o SB':     [0, 0, 2, 17, None],
    'CBC w/o IC':     [0, 0, 2, 3, 27],
    'GLPK (all)':    [0, 2, 1, 40, None],
    'GLPK w/o SB':   [0, 0, 38, 74, None],
    'GLPK w/o IC':   [0, 1, 59, 218, None],
}

# Plotting
plt.figure(figsize=(12, 6))

# Define colors by solver for visual grouping
colors = {
    'CBC (all)': '#1f77b4', 'CBC w/o SB': '#1f77b4AA', 'CBC w/o IC': '#1f77b455',
    'GLPK (all)': '#ff7f0e', 'GLPK w/o SB': '#ff7f0eAA', 'GLPK w/o IC': '#ff7f0e55',
}

# Plot each line
for col in list(data.keys())[1:]:
    plt.plot(data['n'], data[col], marker='o', label=col, color=colors[col])

plt.xlabel('Number of teams (n)')
plt.ylabel('Time (s)')
plt.title('MIP solvers: solving time for different constraint configurations. ')
plt.legend()
plt.xticks(data['n'])
plt.grid(True)
plt.tight_layout()
plt.show()
