import os
import json
import argparse
import statistics
import sys

# Add the source directory to Python path to import sts
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'source', 'SMT'))

# Import the sts module
import sts

JSON_FOLDER = "../../res/SMT"

# Available constraint categories
ALL_CONSTRAINTS = [
    "use_symm_break_weeks",
    "use_symm_break_periods", 
    "use_symm_break_teams",
    "use_implied_matches_per_team",
    "use_implied_period_count"
]

ALL_CONSTRAINTS_GROUPS = {
    "symm": [c for c in ALL_CONSTRAINTS if "symm" in c],
    "implied": [c for c in ALL_CONSTRAINTS if "implied" in c],
    "all": ALL_CONSTRAINTS
}

def run_sts_solver(
    n: int,
    active_constraints: list[str],
    optimize: bool = False,
    timeout_sec: int = 300,
    verbose: bool = False,
    solver: str = "z3"
) -> dict:
    """
    Runs the STS SMT solver with the specified configuration and solver.

    Args:
        n (int): Number of teams (must be even)
        active_constraints (list[str]): List of active constraint names
        optimize (bool): Whether to optimize for home/away balance (only for z3)
        timeout_sec (int): Timeout in seconds
        verbose (bool): Whether to print verbose output
        solver (str): Which SMT solver to use ('z3' or 'cvc5')

    Returns:
        dict: Results dictionary with timing, solution status, and solution
    """
    constraints = {c: c in active_constraints for c in ALL_CONSTRAINTS}
    
    if verbose:
        print(f"Running SMT solver with n={n}")
        print(f"Active constraints: {active_constraints}")
        print(f"Solver: {solver}")
        print(f"Optimize: {optimize}")

    try:
        if solver == "z3":
            result = sts.solve_sts_smt(n, constraints, optimize=optimize, timeout=timeout_sec)
        else:
            result = sts.solve_sts_smt_smtlib(n, constraints, optimize=False, timeout=timeout_sec)
        
        # If result is unsat or timeout, set sol to []
        sol_val = result['sol']
        if isinstance(sol_val, str) and (sol_val == "unsat" or "timeout" in sol_val or "error" in sol_val):
            sol_val = []
        
        return {
            "time": int(result['time']),
            "optimal": result['optimal'],
            "obj": result.get('obj', None),
            "sol": sol_val,
            "solver": solver,
            "constraints": active_constraints
        }
            
    except Exception as e:
        return {
            "time": timeout_sec,
            "optimal": False,
            "obj": None,
            "sol": [],  # Return [] for unsat/timeout
            "solver": solver,
            "constraints": active_constraints
        }

def run_sts_with_averaging(
    n: int,
    active_constraints: list[str],
    optimize: bool = False,
    timeout_sec: int = 300,
    verbose: bool = False,
    num_runs: int = 5,
    solver: str = "z3"
) -> dict:
    """
    Runs the STS SMT solver multiple times and averages the timing results.

    Args:
        n (int): Number of teams (must be even)
        active_constraints (list[str]): List of active constraint names
        optimize (bool): Whether to optimize for home/away balance (only for z3)
        timeout_sec (int): Timeout in seconds
        verbose (bool): Whether to print verbose output
        num_runs (int): Number of runs to average over
        solver (str): Which SMT solver to use ('z3' or 'cvc5')

    Returns:
        dict: Averaged results dictionary
    """
    if verbose:
        print(f"Running {num_runs} iterations with constraints: {active_constraints}")
    
    results = []
    for i in range(num_runs):
        result = run_sts_solver(n, active_constraints, optimize, timeout_sec, verbose=False, solver=solver)
        results.append(result)
        if verbose:
            print(f"  Run {i+1}/{num_runs}: {'sat' if result['sol'] else 'unsat'} in {result['time']}s")
    
    # Calculate statistics
    times = [r["time"] for r in results]
    sat_count = sum(1 for r in results if r["sol"] and not isinstance(r["sol"], str))
    optimal_count = sum(1 for r in results if r["optimal"])
    
    avg_time = statistics.mean(times)
    std_time = statistics.stdev(times) if len(times) > 1 else 0
    min_time = min(times)
    max_time = max(times)
    
    # Take first solution found if any
    solution = next((r["sol"] for r in results if r["sol"]), None)
    objective = next((r["obj"] for r in results if r["optimal"]), None)
    # If no solution found, set to []
    if not solution or (isinstance(solution, str) and (solution == "unsat" or "timeout" in solution or "error" in solution)):
        solution = []
    
    return {
        "time": int(avg_time),
        "time_std": std_time,
        "time_min": min_time,
        "time_max": max_time,
        "optimal": optimal_count > 0,
        "obj": objective,
        "sol": solution,
        "solver": solver,
        "constraints": active_constraints,
        "optimize": optimize,
        "runs": num_runs,
        "sat_count": sat_count,
        "optimal_count": optimal_count
    }

def write_results_to_json(results: list[dict], names: list[str], n: int):
    """
    Save results to JSON file.

    Args:
        results (list[dict]): List of result dictionaries.
        names (list[str]): Names for each result.
        n (int): Number of teams (used for filename).
    """
    # Create SMT results directory if it doesn't exist
    os.makedirs(JSON_FOLDER, exist_ok=True)
    
    filename = f"{JSON_FOLDER}/{n}.json"
    output_data = {}
    for result, name in zip(results, names):
        output_data[name] = result
        output_data[name]["sol"] = str(result.get("sol", "unknown"))

    with open(filename, "w") as f:
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

def run_all_solver_optimize_combinations(n, constraints, timeout, verbose, runs, solver_list):
    """
    Run all solvers (z3, cvc5) with both optimize True and False.
    Returns: (results, names)
    """
    results = []
    names = []
    for solver in solver_list:
        for optimize in [False, True]:
            # cvc5 does not support optimize
            if solver == "cvc5" and optimize:
                continue
            result = run_sts_with_averaging(
                n, constraints, optimize, timeout, verbose, runs, solver
            )
            opt_str = "opt" if optimize else "sat"
            names.append(f"{solver}_{opt_str}_" + "_".join(constraints) if constraints else f"{solver}_{opt_str}_no_constraints")
            results.append(result)
    return results, names

def main():
    """
    Main entry point for running the SMT solver experiment script.

    Parses command-line arguments, runs the solver(s) according to the selected mode,
    and writes results to a JSON file.
    """
    parser = argparse.ArgumentParser(
        description="Run the STS SMT solver with various constraint configurations"
    )
    
    parser.add_argument(
        "teams", 
        type=int, 
        help="Number of teams (must be even)"
    )
    parser.add_argument(
        "--solver", 
        type=str, 
        default="z3", 
        choices=["z3", "cvc5"],
        help="Which SMT solver to use (default: z3)"
    )
    parser.add_argument(
        "--optimize", 
        action="store_true",
        help="Use optimization version to balance home/away games"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=300,
        help="Timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "--runs", 
        type=int, 
        default=5,
        help="Number of runs to average over (default: 5)"
    )
    parser.add_argument(
        "--verbose", 
        "-v", 
        action="store_true",
        help="Enable verbose output"
        )
    
    # Constraint selection modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--generate", action="store_true",
                         help="Run with all constraints (default)")
    mode_group.add_argument("--test", action="store_true",
                         help="Test all constraint combinations")
    mode_group.add_argument("--select", choices=list(ALL_CONSTRAINTS_GROUPS.keys()) + ["all"],
                         help="Test specific constraint group")
    
    parser.add_argument(
        "--constraints", 
        nargs="*", 
        choices=ALL_CONSTRAINTS,
        default=ALL_CONSTRAINTS, 
        help="Specific constraints to use"
    )
    
    args = parser.parse_args()
    
    if args.teams % 2 != 0:
        print(f"Error: Number of teams ({args.teams}) must be even")
        return 1

    results = []
    names = []
    solver_list = ["z3", "cvc5"]

    if args.test:
        from itertools import combinations
        for r in range(len(args.constraints) + 1):
            for combo in combinations(args.constraints, r):
                combo_list = list(combo)
                res, nms = run_all_solver_optimize_combinations(
                    args.teams, combo_list, args.timeout, args.verbose, args.runs, solver_list
                )
                results.extend(res)
                names.extend(nms)

    elif args.select:
        groups = [args.select] if args.select != "all" else ALL_CONSTRAINTS_GROUPS.keys()
        for group in groups:
            constraints = ALL_CONSTRAINTS_GROUPS[group]
            res, nms = run_all_solver_optimize_combinations(
                args.teams, constraints, args.timeout, args.verbose, args.runs, solver_list
            )
            results.extend(res)
            names.extend(nms)

    else:  # generate mode (default)
        res, nms = run_all_solver_optimize_combinations(
            args.teams, args.constraints, args.timeout, args.verbose, args.runs, solver_list
        )
        results.extend(res)
        names.extend(nms)

    write_results_to_json(results, names, args.teams)
    print(f"Results saved to {JSON_FOLDER}/{args.teams}.json")

    return 0

if __name__ == "__main__":
    exit(main())
