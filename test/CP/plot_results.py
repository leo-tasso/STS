import os
import json
import matplotlib.pyplot as plt 
import re
from collections import defaultdict

PARENT_DIR = "../../res/CP/archive/"
RESULTS_DIR_ARM = "ARM M2"
RESULTS_DIR_RIZEN = "Ryzen 5 5600X"
GROUP_COLORS = {
    "symm": "green",
    "implied": "blue",
    "search": "orange"
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

def get_group(name: str) -> str:
    """
    Determines the constraint group for a given combination name.

    Args:
        name: The name of the constraint combination.

    Returns:
        The group name: 'symm', 'implied' or 'search'.
    """
    if "symm" in name:
        return "symm"
    if "implied" in name:
        return "implied"
    if "search" in name:
        return "search"
    return "other"

def get_group_index(name: str, group: str) -> int:
    """
    Extracts the index of the combination within a group for shade selection.

    Args:
        name: The name of the constraint combination.
        group: The group name.

    Returns:
        The index (int) for shade selection within the group.
    """
    parts = name.split("_")
    if group in parts:
        idx = parts.index(group) + 1
        return len(parts[idx:-1])  # -1 to skip solver name
    return 0

def load_results(results_dir: str) -> tuple[
    dict[str, dict[str, dict[int, float]]], list[int], list[str]
]:
    """
    Loads and parses result JSON files from a directory.

    Args:
        results_dir: Path to the directory containing result JSON files.

    Returns:
        data: Nested dictionary of results [solver][combo][n] = time.
        n_values: Sorted list of team sizes (n).
        combo_names: Sorted list of combination names.
    """
    data = defaultdict(lambda: defaultdict(dict))  # data[solver][combo][n] = time
    n_values = set()
    combo_names = set()
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

def plot_solver(
    data: dict[str, dict[str, dict[int, float]]],
    n_values: list[int],
    combo_names: list[str],
    solver: str,
    save_path: str = None
) -> None:
    """
    Plots the solving time for each constraint combination for a given solver.

    Args:
        data: Nested dictionary of results [solver][combo][n] = time.
        n_values: List of team sizes (n).
        combo_names: List of combination names.
        solver: Solver name ('chuffed' or 'gecode').
        save_path: Optional path to save the plot image.
    """
    plt.figure(figsize=(12, 8))
    group_lines = defaultdict(list)
    group_labels = defaultdict(list)
    group_combo_map = defaultdict(list)
    for combo in combo_names:
        if not combo.endswith(f"_{solver}"):
            continue
        group = get_group(combo)
        group_combo_map[group].append(combo)
    for group, combos in group_combo_map.items():
        shades = GROUP_SHADES.get(group, ["gray"])
        for i, combo in enumerate(combos):
            color = shades[i % len(shades)]
            times = [data[solver][combo].get(n, None) for n in n_values]
            if all(t is None for t in times):
                continue
            label = combo.replace(f"_{solver}", "")
            group_lines[group].append(plt.plot(n_values, times, marker="o", color=color, label=label, linewidth=2, alpha=0.8)[0])
            group_labels[group].append(label)
    plt.xlabel("Number of teams (n)")
    plt.ylabel("Time (s)")
    plt.title(f"{solver.capitalize()} Solving Time vs Number of Teams")
    plt.xticks(n_values)
    handles = []
    labels = []
    for group in group_lines:
        for i, line in enumerate(group_lines[group]):
            handles.append(line)
            label = " ".join(group_labels[group][i].split("_")[2:])
            label = re.sub(r"\b use", r", use", label)
            labels.append(label)
    plt.legend(handles, labels, title="Constraint Combination", loc="upper left", fontsize="small")
    plt.grid(True, linestyle="--", alpha=0.5)
    if save_path:
        plt.savefig(save_path)
    plt.tight_layout()
    plt.show()

def main() -> None:
    for RESULTS_DIR in [RESULTS_DIR_ARM, RESULTS_DIR_RIZEN]:
        data, n_values, combo_names = load_results(PARENT_DIR + RESULTS_DIR)
        for solver in ["chuffed"]:
            save_path = f"plots/plot_{solver}_{RESULTS_DIR}.png"
            plot_solver(data, n_values, combo_names, solver, save_path=save_path)

if __name__ == "__main__":
    main()
