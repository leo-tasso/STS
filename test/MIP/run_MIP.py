"""
MIP-based STS solver testing script.

This script provides functionality to run and benchmark the MIP implementation
following the same structure and interface as the CP solver.
"""

import math
import os
import json
import argparse
import statistics
import sys
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the source directory to Python path to import sts
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'source', 'MIP'))

# Import the sts module
import sts

JSON_FOLDER = "../../res/MIP"

# Available constraint categories for MIP (matching CP structure)
ALL_CONSTRAINTS = [
    "use_symm_break_weeks",
    "use_symm_break_periods", 
    "use_symm_break_teams",
    "use_implied_matches_per_team"
]

def select_constraints_from_group(group_name: str, all_constraints: list[str] = ALL_CONSTRAINTS) -> list[str]:
    """
    Selects constraints from a predefined group.

    Args:
        group_name (str): The name of the group to select constraints from.
        all_constraints (list[str]): List of all available constraints.

    Returns:
        list[str]: List of selected constraints from the specified group.
    """
    if group_name == "symm":
        return [c for c in all_constraints if "symm" in c]
    elif group_name == "implied":
        return [c for c in all_constraints if "implied" in c]
    else:
        return all_constraints

ALL_CONSTRAINTS_GROUPS = {
    "symm": select_constraints_from_group("symm"),
    "implied": select_constraints_from_group("implied"),
}

def run_mip_with_averaging(
    n: int,
    active_constraints: list[str] = None,
    solver_name: str = "PULP_CBC_CMD",
    timeout_sec: int = 300,
    verbose: bool = False,
    num_runs: int = 5,
    max_workers: int = None,
    optimize: bool = False,
) -> dict:
    """
    Runs the MIP solver multiple times and averages the results for reliable measurements.
    
    Args:
        n (int): Number of teams
        active_constraints (list[str]): List of active constraint names
        solver_name (str): MIP solver to use
        timeout_sec (int): Timeout in seconds
        verbose (bool): Whether to print verbose output
        num_runs (int): Number of runs to average
        max_workers (int): Maximum number of parallel workers
        optimize (bool): Whether to optimize for home/away balance
        
    Returns:
        dict: Averaged results
    """
    if active_constraints is None:
        active_constraints = ALL_CONSTRAINTS
    
    if verbose:
        print(f"Running {num_runs} iterations with {solver_name} solver")
        print(f"Active constraints: {active_constraints}")
    
    results = []
    
    # Set up constraints dict for MIP solver
    constraints = {
        'use_symm_break_weeks': "use_symm_break_weeks" in active_constraints,
        'use_symm_break_periods': "use_symm_break_periods" in active_constraints,
        'use_symm_break_teams': "use_symm_break_teams" in active_constraints,
        'use_implied_matches_per_team': "use_implied_matches_per_team" in active_constraints,
        'use_implied_period_count': "use_implied_period_count" in active_constraints
    }
    
    # Run multiple times
    def single_run(run_id):
        if verbose:
            print(f"  Run {run_id + 1}/{num_runs}")
        result = sts.solve_sts_mip(n, constraints, solver_name, timeout_sec, verbose, optimize)
        # Cap time at timeout if it exceeds
        if isinstance(result.get("time"), (int, float)) and result["time"] > timeout_sec:
            result["time"] = timeout_sec
        return result
    
    # Execute runs in parallel if max_workers allows
    if max_workers != 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(single_run, i) for i in range(num_runs)]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    if verbose:
                        print(f"Run failed with error: {e}")
                    # Add error result
                    results.append({
                        "time": timeout_sec,
                        "optimal": False,
                        "obj": "None",
                        "sol": [],
                        "solver": solver_name,
                        "constraints": active_constraints,
                        "error": str(e)
                    })
    else:
        # Sequential execution
        for i in range(num_runs):
            try:
                result = single_run(i)
                results.append(result)
            except Exception as e:
                if verbose:
                    print(f"Run {i+1} failed with error: {e}")
                results.append({
                    "time": timeout_sec,
                    "optimal": False,
                    "obj": "None",
                    "sol": [],
                    "solver": solver_name,
                    "constraints": active_constraints,
                    "error": str(e)
                })
    
    # Compute averaged result
    successful_runs = 0
    valid_times = []
    valid_objs = []
    errors = []
    
    # Process results
    for result in results:
        # Cap time at timeout if it exceeds
        if isinstance(result.get("time"), (int, float)) and result["time"] > timeout_sec:
            result["time"] = timeout_sec
            
        if result.get("sol") != [] and result.get("sol") not in ["unsat", "=====UNKNOWN===== (likely timeout)", "ERROR PARSING STDOUT"]:
            successful_runs += 1
            if isinstance(result.get("time"), (int, float)):
                valid_times.append(result["time"])
            if result.get("obj") is not None:
                # Convert objective to integer if it's a numeric value
                obj_val = result["obj"]
                if isinstance(obj_val, (int, float)):
                    valid_objs.append(int(obj_val))
                else:
                    valid_objs.append(obj_val)
        else:
            error_msg = result.get("error", result.get("sol", "Unknown error"))
            errors.append(error_msg)
            # Set sol to [] for unsat/timeout
            result["sol"] = []
    
    # Create averaged result
    avg_result = {
        "solver": solver_name,
        "constraints": active_constraints,
    }
    
    # Compute time statistics
    if valid_times:
        # Ensure all times are capped at timeout
        capped_times = [min(t, timeout_sec) for t in valid_times]
        avg_result["time"] = round(statistics.mean(capped_times), 0)
        time_stats = {
            "mean": round(statistics.mean(capped_times), 2),
            "median": round(statistics.median(capped_times), 2),
            "min": min(capped_times),
            "max": min(max(capped_times), timeout_sec),
        }
        if len(capped_times) > 1:
            time_stats["stdev"] = round(statistics.stdev(capped_times), 2)
        else:
            time_stats["stdev"] = 0
    else:
        time_stats = None
        avg_result["time"] = timeout_sec
    
    # Compute objective statistics
    obj_stats = None
    if valid_objs:
        avg_result["obj"] = int(round(statistics.mean(valid_objs)))
        obj_stats = {
            "mean": int(round(statistics.mean(valid_objs))),
            "median": int(round(statistics.median(valid_objs))),
            "min": int(min(valid_objs)),
            "max": int(max(valid_objs)),
        }
        if len(valid_objs) > 1:
            obj_stats["stdev"] = round(statistics.stdev(valid_objs), 2)
        else:
            obj_stats["stdev"] = 0.0
    else:
        avg_result["obj"] = "None"  # No objective when not optimizing
    
    # Determine if solution is optimal (majority of runs were optimal and within time limit)
    optimal_runs = sum(1 for r in results if r.get("optimal") == True)
    avg_result["optimal"] = True if optimal_runs > num_runs / 2 else False
    
    # Use the best solution found across all runs
    best_obj = None
    best_sol = None
    for result in results:
        if result.get("sol") != [] and result.get("sol") not in ["unsat", "=====UNKNOWN===== (likely timeout)", "ERROR PARSING STDOUT"]:
            obj_val = result.get("obj")
            if obj_val is not None and (best_obj is None or obj_val < best_obj):  # Assuming minimization
                best_obj = obj_val
                best_sol = result.get("sol")
            elif best_sol is None:
                best_sol = result.get("sol")
    
    if best_sol is not None:
        avg_result["sol"] = str(best_sol)
    else:
        avg_result["sol"] = []  # Return empty list for unsat/timeout

    # If sol is empty, obj must be None
    if avg_result["sol"] == []:
        avg_result["obj"] = "None"

    # Add run information and statistics
    avg_result["runs_info"] = {
        "total_runs": num_runs,
        "successful_runs": successful_runs,
        "optimal_runs": optimal_runs,
        "time_stats": time_stats,
        "obj_stats": obj_stats,
        "errors": errors if errors else None,
    }
    
    if verbose:
        print(f"  Completed {successful_runs}/{num_runs} successful runs")
        if time_stats:
            print(f"  Average time: {time_stats['mean']}s (±{time_stats.get('stdev', 0)}s)")
        if obj_stats:
            print(f"  Average objective: {obj_stats['mean']} (±{obj_stats.get('stdev', 0)})")
    
    return avg_result

def run_test_mode(
    n: int,
    active_constraints: list[str],
    solver_name: str = "PULP_CBC_CMD",
    timeout_sec: int = 300,
    verbose: bool = False,
    num_runs: int = 5,
    max_workers: int = None,
    optimize: bool = False,
) -> tuple[list[dict], list[str]]:
    """
    Runs all possible combinations of the selected constraints.
    
    Returns:
        tuple: (results_list, names_list)
    """
    results = []
    names = []
    
    # Generate all possible constraint combinations
    all_combinations = []
    for r in range(len(active_constraints) + 1):
        for combo in combinations(active_constraints, r):
            all_combinations.append(list(combo))
    
    print(f"Testing {len(all_combinations)} constraint combinations...")
    
    for i, combo in enumerate(all_combinations):
        if verbose:
            print(f"\nCombination {i+1}/{len(all_combinations)}: {combo}")
        
        result = run_mip_with_averaging(
            n, combo, solver_name, timeout_sec, verbose, num_runs, max_workers, optimize
        )
        results.append(result)
        
        # Create name following CP convention
        if not combo:
            name = "combo_none"
        else:
            name = "combo_" + "_".join(combo)
        names.append(name)
        
        if not verbose:
            status = "optimal" if result.get("optimal") == True else False
            print(f"  {name}: {status} (avg: {result.get('time', 'N/A')}s)")
    
    return results, names

def run_select_mode(
    n: int,
    group_name: str,
    solver_name: str = "PULP_CBC_CMD",
    timeout_sec: int = 300,
    verbose: bool = False,
    num_runs: int = 5,
    max_workers: int = None,
    optimize: bool = False,
) -> tuple[list[dict], list[str]]:
    """
    Runs all possible combinations of constraints in the selected group.
    
    Returns:
        tuple: (results_list, names_list)
    """
    if group_name == "all":
        selected_constraints = ALL_CONSTRAINTS
    else:
        selected_constraints = ALL_CONSTRAINTS_GROUPS.get(group_name, [])
    
    print(f"Selected group '{group_name}' contains: {selected_constraints}")
    
    return run_test_mode(n, selected_constraints, solver_name, timeout_sec, verbose, num_runs, max_workers, optimize)

def write_results_to_json(results: list[dict], names: list[str], n: int) -> None:
    """
    Writes results to JSON file following CP format.
    """
    os.makedirs(JSON_FOLDER, exist_ok=True)
    
    output_data = {}
    for result, name in zip(results, names):
        output_data[name] = result
    
    filename = os.path.join(JSON_FOLDER, f"{n}.json")
    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2)

    # Post-process: remove quotes around the sol list
    with open(filename, "r") as f:
        lines = f.readlines()

    with open(filename, "w") as f:
        for line in lines:
            if '"sol": "' in line and "unsat" not in line and "timeout" not in line:
                # Clean line: remove surrounding quotes and unescape inner quotes
                line = line.replace('\\"', '"')  # unescape quotes inside
                line = line.replace('"sol": "', '"sol": ').rstrip()
                if line.endswith('",'):
                    line = line[:-2] + ","  # remove closing quote
                f.write(line + "\n")
            else:
                f.write(line)

def main():
    """Main function to handle command-line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Run MIP model with configurable constraints (compatible with CP interface)"
    )

    # Required parameter: number of teams
    parser.add_argument(
        "-n", "--teams", type=int, required=True, help="Number of teams (required)"
    )

    # Mutually exclusive group for -g, -t or -s
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-g",
        "--generate",
        action="store_true",
        help="Generate mode with the selected constraints",
    )
    group.add_argument(
        "-t",
        "--test",
        action="store_true",
        help="Test mode, tries all possible combinations of the selected constraints",
    )
    group.add_argument(
        "-s",
        "--select",
        nargs="?",
        const="all",
        choices=list(ALL_CONSTRAINTS_GROUPS.keys())+["all"],
        help="Try with a combination of one of the following groups: symm, implied. "
             "If used without a value, all grouped constraints will be used.",
    )

    # List of constraint strings
    parser.add_argument(
        "-c",
        "--constraints",
        nargs="*",
        default=ALL_CONSTRAINTS,
        help="List of constraint names to activate (default: all constraints)",
    )
    
    # Solver flag
    parser.add_argument(
        "--solver",
        type=str,
        default="PULP_CBC_CMD",
        help="MIP solver to use (default: PULP_CBC_CMD)",
    )

    # Timeout flag
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Solver timeout in seconds (default: 300)",
    )
    
    # Verbose flag
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output showing intermediate solutions",
    )
    
    # Runs flag for averaging
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs to average over for reliable measurements (default: 5)",
    )

    # Max workers flag for parallel execution
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of parallel workers (default: auto-detect based on CPU count)",
    )

    # Optimize flag for home/away balance
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Enable optimization for home/away balance",
    )

    args = parser.parse_args()
    
    # Validate constraint names
    invalid_constraints = [
        c for c in args.constraints if c not in ALL_CONSTRAINTS
    ]
    if invalid_constraints:
        print(f"Error: Invalid constraint names: {invalid_constraints}")
        print(f"Available constraints: {ALL_CONSTRAINTS}")
        return 1
    
    # Check if solver is available
    available_solvers = sts.get_available_solvers()
    if args.solver not in available_solvers:
        print(f"Error: Solver '{args.solver}' not available")
        print(f"Available solvers: {available_solvers}")
        return 1
    
    # Run the model based on mode
    print(f"Running MIP model with {args.teams} teams")
    print(
        f"Mode: {'Generate' if args.generate else 'Test' if args.test else 'Select' if args.select else 'Default'}"
    )
    print(f"Solver: {args.solver}")
    print(f"Timeout: {args.timeout} seconds")
    print(f"Runs per measurement: {args.runs}")
    print(f"Optimize for home/away balance: {args.optimize}")
    if args.select:
        print(f"Selected constraint group: {args.select}")
    else:
        print(f"Selected constraints: {args.constraints}")

    results = []
    names = []

    if args.test:
        # Test mode: try all possible combinations of the selected constraints
        print("Test mode: Running all possible combinations of selected constraints...")
        print(f"Each combination will be run {args.runs} times for reliable measurements.")
        results, names = run_test_mode(
            args.teams, args.constraints, args.solver, args.timeout, args.verbose, args.runs, args.max_workers, args.optimize
        )
    elif args.select:
        # Select group mode: run with all possible combinations of the selected constraint group
        print("Select group mode: Running all possible combinations of selected group constraint...")
        print(f"Each combination will be run {args.runs} times for reliable measurements.")
        results, names = run_select_mode(
            args.teams, args.select, args.solver, args.timeout, args.verbose, args.runs, args.max_workers, args.optimize
        )
    else:
        # Generate mode: run once with all selected constraints active
        print("Generate mode: Running with all selected constraints active...")
        print(f"Will run {args.runs} times for reliable measurements.")
        result = run_mip_with_averaging(
            args.teams,
            args.constraints,
            solver_name=args.solver,
            timeout_sec=args.timeout,
            verbose=args.verbose,
            num_runs=args.runs,
            max_workers=args.max_workers,
            optimize=args.optimize,
        )
        results.append(result)
        names.append("generate_all_constraints")
    
    # Save results
    write_results_to_json(results, names, args.teams)
    print(f"Total executions: {len(results)}")
    if args.runs > 1:
        print(f"Each execution was averaged over {args.runs} runs for reliable measurements.")

    return 0

if __name__ == "__main__":
    exit(main())
