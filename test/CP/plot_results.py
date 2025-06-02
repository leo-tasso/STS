import os
import json
import matplotlib.pyplot as plt 
import re
from collections import defaultdict

# --- CONFIGURATION ---
PARENT_DIR = "../../res/CP/archive/"
RESULTS_DIR_ARM = "ARM M2"
RESULTS_DIR_RIZEN = "Ryzen 5 5600X"
GROUP_COLORS = {
    "symm": "green",
    "implied": "blue",
    "search": "orange",
    "other": "gray"
}
GROUP_SHADES = {
    "symm": [
        "#006400", "#228B22", "#32CD32", "#7CFC00",
        "#90EE90", "#2E8B57", "#66CDAA", "#98FB98"
    ],
    "search": [
        "#8B4513", "#A0522D", "#CD853F", "#D2691E",
        "#FFA500", "#FFD700", "#FFB347", "#FFE4B5"
    ],
    "implied": ["#00008B", "#1E90FF", "#4682B4", "#87CEEB"]
}

# --- GROUP DETECTION ---
def get_group(name):
    if "symm" in name:
        return "symm"
    if "implied" in name:
        return "implied"
    if "search" in name:
        return "search"
    return "other"

def get_group_index(name, group):
    # Extract which combination within the group (for shade selection)
    # e.g. select_group_symm_use_symm_break_weeks_use_symm_break_teams_chuffed
    parts = name.split("_")
    # Find all group constraint names after group name
    if group in parts:
        idx = parts.index(group) + 1
        # Count how many constraint names are present after group
        return len(parts[idx:-1])  # -1 to skip solver name
    return 0

# --- LOAD DATA ---
def load_results(results_dir):
    data = defaultdict(lambda: defaultdict(dict))  # data[solver][combo][n] = time
    n_values = set()
    combo_names = set()
    # Only consider files like 6.json, 8.json, etc.
    for fname in os.listdir(results_dir):
        if not fname.endswith(".json"):
            continue
        if not re.match(r"^\d+\.json$", fname):
            continue
        n = int(fname.split(".")[0])
        n_values.add(n)
        with open(os.path.join(results_dir, fname), "r") as f:
            results = json.load(f)
        for combo, result in results.items():
            # combo: e.g. select_group_symm_use_symm_break_weeks_chuffed
            if combo.endswith("_gecode"):
                solver = "gecode"
            elif combo.endswith("_chuffed"):
                solver = "chuffed"
            else:
                continue
            combo_names.add(combo)
            time = result.get("time")
            # If time is None or "unknown", skip
            if time is None or isinstance(time, str):
                continue
            data[solver][combo][n] = float(time)
    return data, sorted(n_values), sorted(combo_names)

# --- PLOT ---
def plot_solver(data, n_values, combo_names, solver, save_path=None):
    plt.figure(figsize=(12, 8))
    group_lines = defaultdict(list)
    group_labels = defaultdict(list)
    # Assign colors/shades
    group_combo_map = defaultdict(list)
    for combo in combo_names:
        if not combo.endswith(f"_{solver}"):
            continue
        group = get_group(combo)
        group_combo_map[group].append(combo)
    # Plot each line
    for group, combos in group_combo_map.items():
        shades = GROUP_SHADES.get(group, ["gray"])
        for i, combo in enumerate(combos):
            color = shades[i % len(shades)]
            times = [data[solver][combo].get(n, None) for n in n_values]
            # Only plot if at least one value is present
            if all(t is None for t in times):
                continue
            label = combo.replace(f"_{solver}", "")
            group_lines[group].append(plt.plot(n_values, times, marker="o", color=color, label=label, linewidth=2, alpha=0.8)[0])
            group_labels[group].append(label)
    plt.xlabel("Number of teams (n)")
    plt.ylabel("Time (s)")
    plt.title(f"MiniZinc Solving Time vs Number of Teams ({solver.capitalize()})")
    # Set x-axis ticks to only n_values
    plt.xticks(n_values)
    # Build legend: one entry per group combination
    handles = []
    labels = []
    for group in group_lines:
        for i, line in enumerate(group_lines[group]):
            handles.append(line)
            # Add a comma before each occurrence of 'use'
            label = " ".join(group_labels[group][i].split("_")[2:])
            label = re.sub(r"\b use", r", use", label)
            labels.append(label)
    plt.legend(handles, labels, title="Constraint Combination", loc="upper left", fontsize="small")
    plt.grid(True, linestyle="--", alpha=0.5)
    if save_path:
        plt.savefig(save_path)
    plt.tight_layout()
    plt.show()

def main():
    for RESULTS_DIR in [RESULTS_DIR_ARM, RESULTS_DIR_RIZEN]:
        data, n_values, combo_names = load_results(PARENT_DIR + RESULTS_DIR)
        for solver in ["chuffed"]:
            plot_solver(data, n_values, combo_names, solver, save_path=f"plots/plot_{solver}_{RESULTS_DIR}.png")

if __name__ == "__main__":
    main()
