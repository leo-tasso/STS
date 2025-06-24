import math
import subprocess
import os
import json
import argparse
import statistics
import time
import sys
from pathlib import Path

# Add the source directory to Python path to import sts
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'source', 'SAT'))

# Import the sts module
import sts

JSON_FOLDER = "../../res/SAT"

# Available constraint categories
ALL_CONSTRAINTS = [
    "use_symm_break_weeks",
    "use_symm_break_periods", 
    "use_symm_break_teams",
    "use_implied_matches_per_team",
    "use_implied_period_count"
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

def run_sts_solver(n: int, active_constraints: list[str], encoding_type: str = "bw", timeout_sec: int = 300, verbose: bool = False, solver: str = "z3") -> dict:
    """
    Runs the STS SAT solver with the specified configuration and solver.
    
    Args:
        n (int): Number of teams
        active_constraints (list[str]): List of active constraint names
        encoding_type (str): Type of SAT encoding to use ('np', 'seq', 'bw', 'he')
        timeout_sec (int): Timeout in seconds
        verbose (bool): Whether to print verbose output
        solver (str): Which solver to use: 'z3', 'minisat', 'glucose'
        
    Returns:
        dict: Results dictionary with timing, solution status, and solution
    """
    
    constraints = {
        'use_symm_break_weeks': "use_symm_break_weeks" in active_constraints,
        'use_symm_break_periods': "use_symm_break_periods" in active_constraints,
        'use_symm_break_teams': "use_symm_break_teams" in active_constraints,
        'use_implied_matches_per_team': "use_implied_matches_per_team" in active_constraints,
        'use_implied_period_count': "use_implied_period_count" in active_constraints
    }
    
    if verbose:
        print(f"Running SAT solver with n={n}")
        print(f"Active constraints: {active_constraints}")
        print(f"Encoding type: {encoding_type}")
        print(f"Solver: {solver}")

    try:
        if solver == "z3":
            result = sts.solve_sts(n, constraints, encoding_type)
        elif solver in ("minisat", "glucose"):
            result = sts.solve_sts_dimacs(n, constraints, encoding_type, solver)
        else:
            raise ValueError(f"Unknown solver: {solver}")

        if result['satisfiable']:
            return {
                "time": int(round(result['time'])),
                "optimal": "true",
                "obj": None,
                "sol": result['solution'],
                "solver": solver,
                "constraints": active_constraints,
                "encoding_type": encoding_type,
                "status": "sat"
            }
        else:
            return {
                "time": int(round(result['time'])),
                "optimal": "false",
                "obj": None,
                "sol": "unsat",
                "solver": solver,
                "constraints": active_constraints,
                "encoding_type": encoding_type,
                "status": "unsat"
            }
            
    except Exception as e:
        return {
            "time": int(round(timeout_sec)),
            "optimal": "false", 
            "obj": None,
            "sol": f"error: {str(e)}",
            "solver": solver,
            "constraints": active_constraints,
            "encoding_type": encoding_type,
            "status": "error"
        }

def run_sts_with_averaging(n: int, active_constraints: list[str], encoding_type: str = "bw", timeout_sec: int = 300,
                          verbose: bool = False, num_runs: int = 5, max_workers: int = None, solver: str = "z3") -> dict:
    """
    Runs the STS solver multiple times and averages the timing results.
    
    Args:
        n (int): Number of teams
        active_constraints (list[str]): List of active constraint names
        encoding_type (str): Type of SAT encoding to use ('np', 'seq', 'bw', 'he')
        timeout_sec (int): Timeout in seconds for each run
        verbose (bool): Whether to print verbose output
        num_runs (int): Number of runs to average over
        max_workers (int): Maximum number of parallel workers (ignored - runs sequentially for Z3 stability)
        solver (str): Which solver to use: 'z3', 'minisat', 'glucose'
        
    Returns:
        dict: Averaged results dictionary
    """
    if verbose:
        print(f"Running {num_runs} iterations with constraints: {active_constraints} and solver: {solver}")
    
    results = []
    
    # Run sequentially to avoid Z3 thread safety issues
    for i in range(num_runs):
        try:
            result = run_sts_solver(n, active_constraints, encoding_type, timeout_sec, verbose=False, solver=solver)
            results.append(result)
            if verbose:
                print(f"  Run {i+1}/{num_runs}: {result['status']} in {result['time']}s")
        except Exception as e:
            if verbose:
                print(f"  Run {i+1}/{num_runs}: Error - {str(e)}")
            results.append({
                "time": int(round(timeout_sec)),
                "optimal": "false",
                "obj": None,
                "sol": f"error: {str(e)}",
                "solver": solver,
                "constraints": active_constraints,
                "encoding_type": encoding_type,
                "status": "error"
            })
    
    # Calculate statistics
    times = [r["time"] for r in results if r["status"] != "error"]
    sat_count = sum(1 for r in results if r["status"] == "sat")
    unsat_count = sum(1 for r in results if r["status"] == "unsat")
    timeout_count = sum(1 for r in results if r["status"] == "unknown")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    # Take the first SAT solution if any
    solution = next((r["sol"] for r in results if r["status"] == "sat"), "no_solution")
    
    if times:
        avg_time = statistics.mean(times)
        std_time = statistics.stdev(times) if len(times) > 1 else 0.0
        min_time = min(times) 
        max_time = max(times)
    else:
        avg_time = timeout_sec
        std_time = 0.0
        min_time = timeout_sec
        max_time = timeout_sec
    
    # Determine overall status
    if sat_count > 0:
        overall_status = "sat"
        optimal = "true"
    elif unsat_count == num_runs:
        overall_status = "unsat"
        optimal = "false"
    else:
        overall_status = "mixed" if sat_count > 0 else "timeout"
        optimal = "false"
    
    return {
        "time": avg_time,
        "time_std": std_time,
        "time_min": min_time,
        "time_max": max_time,
        "optimal": optimal,
        "obj": None,
        "sol": solution,
        "solver": solver,
        "constraints": active_constraints,
        "encoding_type": encoding_type,
        "status": overall_status,
        "runs": num_runs,
        "sat_count": sat_count,
        "unsat_count": unsat_count, 
        "timeout_count": timeout_count,
        "error_count": error_count
    }

def run_sts_with_averaging_all_solvers(n, active_constraints, encoding_type="bw", timeout_sec=300, verbose=False, num_runs=5, max_workers=None):
    """
    Run all solvers (z3, minisat, glucose) and return a dict of results keyed by solver name.
    """
    solvers = ["z3", "minisat", "glucose"]
    results = {}
    for solver in solvers:
        if verbose:
            print(f"Running with solver: {solver}")
        results[solver] = run_sts_with_averaging(
            n, active_constraints, encoding_type, timeout_sec, verbose, num_runs, max_workers, solver=solver
        )
    return results

def run_test_mode(n: int, constraints: list[str], encoding_type: str = "bw", timeout_sec: int = 300,
                 verbose: bool = False, num_runs: int = 5, max_workers: int = None, solver: str = "z3"):
    """
    Test mode: try all possible combinations of the selected constraints.
    
    Args:
        n (int): Number of teams
        constraints (list[str]): List of constraints to test
        encoding_type (str): Type of SAT encoding to use ('np', 'seq', 'bw', 'he')
        timeout_sec (int): Timeout in seconds for each run
        verbose (bool): Whether to print verbose output
        num_runs (int): Number of runs to average over
        max_workers (int): Maximum number of parallel workers
        solver (str): Which solver to use: 'z3', 'minisat', 'glucose', 'all'
        
    Returns:
        tuple: (results, names) where results is list of result dicts and names is list of result names
    """
    from itertools import combinations

    results = []
    names = []

    # Test all possible combinations of constraints (power set)
    for r in range(len(constraints) + 1):
        for combo in combinations(constraints, r):
            combo_list = list(combo)
            if verbose:
                print(f"Testing combination: {combo_list}")
            
            if solver == "all":
                solver_results = run_sts_with_averaging_all_solvers(
                    n, combo_list, encoding_type, timeout_sec, verbose, num_runs, max_workers
                )
                for sname, sres in solver_results.items():
                    results.append(sres)
                    if combo_list:
                        name = f"{sname}_" + "_".join([c.replace("use_", "") for c in combo_list])
                    else:
                        name = f"{sname}_no_constraints"
                    names.append(name)
            else:
                result = run_sts_with_averaging(
                    n, combo_list, encoding_type, timeout_sec, verbose, num_runs, max_workers, solver=solver
                )
                if combo_list:
                    name = "_".join([c.replace("use_", "") for c in combo_list])
                else:
                    name = "no_constraints"
                results.append(result)
                names.append(name)

    return results, names

def run_select_mode(n: int, group_name: str, encoding_type: str = "bw", timeout_sec: int = 300, 
                   verbose: bool = False, num_runs: int = 5, max_workers: int = None, solver: str = "z3"):
    """
    Select group mode: run with all possible combinations of the selected constraint group.
    
    Args:
        n (int): Number of teams
        group_name (str): Name of constraint group to test or "all" for all groups
        encoding_type (str): Type of SAT encoding to use ('np', 'seq', 'bw', 'he')
        timeout_sec (int): Timeout in seconds for each run
        verbose (bool): Whether to print verbose output  
        num_runs (int): Number of runs to average over
        max_workers (int): Maximum number of parallel workers
        solver (str): Which solver to use: 'z3', 'minisat', 'glucose', 'all'
        
    Returns:
        tuple: (results, names) where results is list of result dicts and names is list of result names
    """
    if group_name == "all":
        all_results = []
        all_names = []
        
        for group in ALL_CONSTRAINTS_GROUPS.keys():
            if verbose:
                print(f"Testing group: {group}")
            
            group_results, group_names = run_select_group(
                n, group, encoding_type, timeout_sec, verbose, num_runs, max_workers, solver=solver
            )
            all_results.extend(group_results)
            all_names.extend(group_names)
        
        return all_results, all_names
    else:
        return run_select_group(n, group_name, encoding_type, timeout_sec, verbose, num_runs, max_workers, solver=solver)

def run_select_group(n: int, group_name: str, encoding_type: str = "bw", timeout_sec: int = 300,
                    verbose: bool = False, num_runs: int = 5, max_workers: int = None, solver: str = "z3"):
    """
    Run all possible combinations of constraints from a specific group.
    
    Args:
        n (int): Number of teams
        group_name (str): Name of constraint group to test
        encoding_type (str): Type of SAT encoding to use ('np', 'seq', 'bw', 'he')
        timeout_sec (int): Timeout in seconds for each run
        verbose (bool): Whether to print verbose output  
        num_runs (int): Number of runs to average over
        max_workers (int): Maximum number of parallel workers
        solver (str): Which solver to use: 'z3', 'minisat', 'glucose', 'all'
        
    Returns:
        tuple: (results, names) where results is list of result dicts and names is list of result names
    """
    group_constraints = select_constraints_from_group(group_name)
    if verbose:
        print(f"Testing all combinations of {group_name} constraints: {group_constraints}")
    
    results, names = run_test_mode(n, group_constraints, encoding_type, timeout_sec, verbose, num_runs, max_workers, solver=solver)
    
    # Prefix names with group identifier for clarity
    prefixed_names = [f"select_group_{group_name}_{name}" for name in names]
    
    return results, prefixed_names

def write_results_to_json(results: list[dict], names: list[str], n: int):
    """
    Save the given results dictionaries to a JSON file.
    
    Args:
        results (list[dict]): The dictionaries containing the results of the executions.
        names (list[str]): Names to identify each execution that generated each result.
        n (int): Number of teams used as the json file name.
    """
    # Create SAT results directory if it doesn't exist
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

def main():
    parser = argparse.ArgumentParser(
        description="Run the STS SAT solver with various constraint configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available constraints: {', '.join(ALL_CONSTRAINTS)}

Available constraint groups:
  symm: symmetry breaking constraints
  implied: implied constraints

Available encoding types:
  np: naive pairwise encoding
  seq: sequential encoding
  bw: bitwise encoding (default)
  he: heule encoding

Available solvers:
  z3: Z3 solver (default)
  minisat: PySAT Minisat22
  glucose: PySAT Glucose42
  all: Run all three solvers

Examples:
  python run_STS.py 6 --generate
  python run_STS.py 8 --test --constraints use_symm_break_weeks use_symm_break_teams --encoding seq --solver minisat
  python run_STS.py 10 --select symm --timeout 600 --encoding np --solver all
        """
    )
    
    # Positional argument for number of teams
    parser.add_argument(
        "teams", 
        type=int, 
        help="Number of teams (must be even)"
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--test",
        action="store_true", 
        help="Test mode: try all possible combinations of selected constraints"
    )
    mode_group.add_argument(
        "--select",
        nargs="?",
        const="all",
        choices=list(ALL_CONSTRAINTS_GROUPS.keys()) + ["all"],
        help="Select constraint group mode: test all combinations of constraints from the specified group (default: all groups)"
    )
    mode_group.add_argument(
        "--generate",
        action="store_true",
        help="Generate mode: run with all selected constraints active (default)"
    )
    
    # Constraint selection
    parser.add_argument(
        "--constraints",
        nargs="*",
        default=ALL_CONSTRAINTS,
        choices=ALL_CONSTRAINTS,
        help="List of constraints to use (default: all constraints)"
    )
    
    # Encoding type selection
    parser.add_argument(
        "--encoding",
        type=str,
        default="bw",
        choices=["np", "seq", "bw", "he"],
        help="Type of SAT encoding to use: np (naive pairwise), seq (sequential), bw (bitwise, default), he (heule)"
    )
    # Solver selection
    parser.add_argument(
        "--solver",
        type=str,
        default="z3",
        choices=["z3", "minisat", "glucose", "all"],
        help="Which SAT solver to use: z3 (default), minisat, glucose, or all"
    )
    # Timeout
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for each solver run (default: 300)"
    )
    
    # Verbose output
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Number of runs for averaging  
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs to average over for reliable measurements (default: 5)"
    )
    
    # Max workers for parallel execution
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of parallel workers (default: auto-detect based on CPU count)"
    )
    
    args = parser.parse_args()
    
    # Validate number of teams
    if args.teams % 2 != 0:
        print(f"Error: Number of teams ({args.teams}) must be even")
        return 1
    
    # Run the solver based on mode
    print(f"Running SAT solver with {args.teams} teams")
    print(f"Mode: {'Generate' if args.generate else 'Test' if args.test else 'Select Group' if args.select else 'Default'}")
    print(f"Solver: {args.solver}")
    print(f"Encoding: {args.encoding}")
    print(f"Timeout: {args.timeout} seconds")
    print(f"Runs per measurement: {args.runs}")
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
            args.teams, args.constraints, args.encoding, args.timeout, args.verbose, args.runs, args.max_workers, solver=args.solver
        )
    elif args.select:
        # Select group mode: run with all possible combinations of the selected constraint group
        print("Select group mode: Running all possible combinations of selected group constraints...")
        print(f"Each combination will be run {args.runs} times for reliable measurements.")
        results, names = run_select_mode(
            args.teams, args.select, args.encoding, args.timeout, args.verbose, args.runs, args.max_workers, solver=args.solver
        )
    else:
        # Generate mode: run once with all selected constraints active (default)
        print("Generate mode: Running with all selected constraints active...")
        print(f"Will run {args.runs} times for reliable measurements.")
        if args.solver == "all":
            all_solver_results = run_sts_with_averaging_all_solvers(
                args.teams,
                args.constraints,
                encoding_type=args.encoding,
                timeout_sec=args.timeout,
                verbose=args.verbose,
                num_runs=args.runs,
                max_workers=args.max_workers,
            )
            for solver_name, result in all_solver_results.items():
                results.append(result)
                names.append(f"{solver_name}_generate_all_constraints")
        else:
            result = run_sts_with_averaging(
                args.teams,
                args.constraints,
                encoding_type=args.encoding,
                timeout_sec=args.timeout,
                verbose=args.verbose,
                num_runs=args.runs,
                max_workers=args.max_workers,
                solver=args.solver,
            )
            results.append(result)
            names.append("generate_all_constraints")
    
    # Save results
    write_results_to_json(results, names, args.teams)
    print(f"Results saved to {JSON_FOLDER}/{args.teams}.json")
    print(f"Total executions: {len(results)}")
    if args.runs > 1:
        print(f"Each execution was averaged over {args.runs} runs for reliable measurements.")
    
    return 0

if __name__ == "__main__":
    exit(main())
