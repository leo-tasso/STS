import math
import tempfile
import subprocess
import os
import json
import argparse
import statistics
import random
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optimized version paths
DZN_PATH = "../../source/CP/use_constraints.dzn"
MODEL_PATH = "../../source/CP/sts.mzn"

# Non-optimized version paths
DZN_PATH_NO_OPT = "../../source/CP/use_constraintsNoOpt.dzn"
MODEL_PATH_NO_OPT = "../../source/CP/stsNoOpt.mzn"

JSON_FOLDER = "../../res/CP"
VARIABLE_PREFIX = "use_"


def read_constraint_names_from_dzn(
    dzn_path: str = DZN_PATH, variable_prefix: str = VARIABLE_PREFIX
) -> list[str]:
    """
    Reads a MiniZinc `.dzn` data file and extracts all boolean constraint toggles
    whose names start with `variable_prefix`.

    Parameters:
        dzn_path (str): The file path to the `.dzn` file.
        variable_prefix (str): The prefix to filter constraint names.

    Returns:
        list[str]: A list of variable names (str) that are boolean flags.
    """
    constraint_names = []

    with open(dzn_path, "r") as file:
        for line in file:
            line = line.strip()
            parts = line.split("=")

            if len(parts) == 2:
                name = parts[0].strip()
                # Check if it's a boolean flag starting with the expected prefix
                if name.startswith(variable_prefix):
                    constraint_names.append(name)

    return constraint_names

ALL_CONSTRAINTS = read_constraint_names_from_dzn()
ALL_CONSTRAINTS_NO_OPT = read_constraint_names_from_dzn(DZN_PATH_NO_OPT)

def select_constraints_from_group(
    group_name: str, all_constraints: list[str] = ALL_CONSTRAINTS
) -> list[str]:
    """
    Selects constraints from a predefined group.

    Args:
        group_name (str): The name of the group to select constraints from.
        all_constraints (list[str]): List of all available constraints.

    Returns:
        list[str]: List of selected constraints from the specified group.
    """
    if group_name == "search":
        return all_constraints[-3:]
    
    return [c for c in all_constraints if group_name in c]
    
ALL_CONSTRAINTS_GROUPS = {
    "symm": select_constraints_from_group("symm"),
    "implied": select_constraints_from_group("implied"),
    "search": select_constraints_from_group("search")
}


def clean_minizinc_stdout(
    stdout: str,
    use_chuffed: bool,
    error: bool = False,
    timeout_sec: int = 300,
    optimization_version: bool = True,
    active_constraints: list[str] = None,
    error_message: str = None,
    verbose: bool = False,
) -> dict:
    """
    Cleans the MiniZinc stdout output by removing unnecessary lines and formatting.
    When intermediate solutions are present, takes the last (best) solution.

    Args:
        stdout (str): The raw output from MiniZinc.
        expired_timeout (bool): If True, indicates that the MiniZinc run timed out.
        timeout_sec (int): The timeout duration in seconds, default is 300.
        optimization_version (bool): If True, indicates that the output is from an optimization version of the STS.
        use_chuffed (bool): Whether it was used the Chuffed solver (True) or Gecode (False).
        active_constraints (list[str]): All available constraints used for the selected model version.

    Returns:
        dict: Cleaned output as a dictionary with the best (last) solution.
    """

    solver = "chuffed" if use_chuffed else "gecode"

    # Handle timeout case and errors, like for large n
    if stdout is None or stdout.strip() == "":
        return {
            "time": timeout_sec,
            "optimal": False,
            "obj": "None",
            "sol": [],
            "solver": solver,
            "constraints": active_constraints,
        }
    if error:
        return {
            "time": timeout_sec,
            "optimal": False,
            "obj": "None",
            "sol": [],
            "solver": solver,
            "constraints": active_constraints,
        }
    # Handle unsat case, like for n = 4
    unsat = "UNSATISFIABLE" in stdout
    if unsat:
        return {
            "time": 300,
            "optimal": False,
            "obj": "None",
            "sol": [],
            "solver": solver,
            "constraints": active_constraints,
        }

    # Check if MiniZinc timed out internally (produces incomplete output)
    if "=====UNKNOWN=====" in stdout or stdout.count("{") != stdout.count("}"):
        return {
            "time": timeout_sec,
            "optimal": False,
            "obj": "None",
            "sol": [],  # Return empty list for unsat/timeout
            "solver": solver,
            "constraints": active_constraints,
        }

    try:
        # Parse multiple JSON solutions and take the last (best) one
        json_solutions = []
        
        # Split by comments (%) to separate solutions from status messages
        output_lines = stdout.splitlines()
        current_json = ""
        
        for line in output_lines:
            line = line.strip()
            # Skip comment lines starting with %
            if line.startswith("%"):
                continue
            
            # Accumulate lines that could be part of JSON
            if line and (line.startswith("{") or current_json):
                current_json += line
                
                # Check if we have a complete JSON object
                if line.endswith("}") and current_json.count("{") == current_json.count("}"):
                    try:
                        parsed_json = json.loads(current_json)
                        json_solutions.append(parsed_json)
                        if verbose:
                            print(f"Found intermediate solution {len(json_solutions)}: obj={parsed_json.get('obj', 'N/A')}")
                        current_json = ""
                    except json.JSONDecodeError:
                        # Not a complete JSON yet, continue accumulating
                        current_json += "\n"
        
        # If no valid JSON solutions found, try the old method as fallback
        if not json_solutions:
            json_part = stdout.split("%")[0].strip()
            if not json_part:
                # No JSON output - likely timeout
                return {
                    "time": timeout_sec,
                    "optimal": False,
                    "obj": "None",
                    "sol": "ERROR PARSING STDOUT",
                    "solver": solver,
                    "constraints": active_constraints,
                }
            cleaned_output = json.loads(json_part)
            if verbose:
                print("Used fallback parsing method")
        else:
            # Take the last (best) solution
            cleaned_output = json_solutions[-1]
            if verbose:
                print(f"Using best solution (#{len(json_solutions)}) with obj={cleaned_output.get('obj', 'N/A')}")
            
    except (json.JSONDecodeError, ValueError):
        # JSON parsing failed - likely timeout or invalid output
        print(stdout)
        return {
            "time": timeout_sec,
            "optimal": False,
            "obj": "None",
            "sol": [],  # Return empty list for unsat/timeout
            "solver": solver,
            "constraints": active_constraints,
        }

    # Extract time elapsed from MiniZinc output
    time_elapsed = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("% time elapsed:"):
            parts = line.split()
            if len(parts) >= 5:
                time_elapsed = math.floor(float(parts[3]))

    # If no time was found but we have valid output, set time to 0
    if time_elapsed is None:
        time_elapsed = "unknown"
    
    # Cap time at timeout if it exceeds
    if isinstance(time_elapsed, (int, float)) and time_elapsed > timeout_sec:
        time_elapsed = timeout_sec

    ordered_output = {
        "time": time_elapsed,
        "optimal": True if isinstance(time_elapsed, (int, float)) and time_elapsed < timeout_sec else False,
        "obj": cleaned_output.get("obj") if optimization_version else None,
        "sol": str(cleaned_output.get("sol", "unknown")),
        "solver": solver,
        "constraints": active_constraints,
    }

    if "% Time limit exceeded!" in stdout:
        ordered_output["optimal"] = False
        ordered_output["time"] = timeout_sec

    return ordered_output


def run_minizinc_model_cli(
    n: int,
    active_constraints: list[str] = None,
    model_path: str = None,
    timeout_sec: int = 300,
    use_chuffed: bool = True,
    is_optimization: bool = True,
    all_constraints: list[str] = None,
    verbose: bool = False,
    random_seed: int = None,
) -> dict:
    """
    Runs a MiniZinc model via the CLI, setting constraint flags by a temporary `.dzn` file.

    Args:
        n (int): The number of teams.
        active_constraints (list[str]): List of constraint names to activate.
        model_path (str): Path to the `.mzn` model.
        timeout_sec (int): Timeout in seconds for the model run.
        use_chuffed (bool): Whether to use the Chuffed solver (True) or Gecode (False).
        is_optimization (bool): If True, indicates that the output is from an optimization version of the STS.
        all_constraints (list[str]): All available constraints for the selected model version.
        random_seed (int): Random seed for MiniZinc solver. If None, no seed is set.

    Returns:
        dict: The cleaned output from the MiniZinc execution.
    """
    # Set defaults based on optimization version
    if active_constraints is None:
        active_constraints = (
            ALL_CONSTRAINTS if is_optimization else ALL_CONSTRAINTS_NO_OPT
        )
    if model_path is None:
        model_path = MODEL_PATH if is_optimization else MODEL_PATH_NO_OPT
    if all_constraints is None:
        all_constraints = ALL_CONSTRAINTS if is_optimization else ALL_CONSTRAINTS_NO_OPT
    
    all_constraints = all_constraints.copy()
    all_constraints.append("chuffed")
    constraints_with_chuffed = active_constraints.copy()
    if use_chuffed:
        constraints_with_chuffed.append("chuffed")
    temp_dzn_path = generate_dzn_file(n, constraints_with_chuffed, all_constraints)

    # MiniZinc expects timeout in milliseconds
    timeout_flag = ["--time-limit", str(timeout_sec * 1000)]
    solver_flag = ["--solver", "chuffed" if use_chuffed else "gecode"]
    
    # Add random seed flag if provided
    seed_flag = []
    if random_seed is not None:
        seed_flag = ["--random-seed", str(random_seed)]

    result_params = {
        "timeout_sec": timeout_sec,
        "optimization_version": is_optimization,
        "active_constraints": active_constraints,
        "use_chuffed": use_chuffed,
        "verbose": verbose,
    }

    try:
        cmd = [
            "minizinc",
            "--output-time",
            "--intermediate-solutions",
            *timeout_flag,
            *solver_flag,
            *seed_flag,
            model_path,
            temp_dzn_path,
        ]

        # Use subprocess timeout as a backup (add 10 seconds buffer for MiniZinc to cleanup)
        process_timeout = timeout_sec + 10

        process = subprocess.run(
            cmd, capture_output=True, text=True, timeout=process_timeout
        )

        # Check if the process completed successfully
        if process.returncode != 0 and process.stderr:
            # Handle MiniZinc errors
            if (
                "time limit exceeded" in process.stderr.lower()
                or "timeout" in process.stderr.lower()
            ):
                result = clean_minizinc_stdout(None, error=True, **result_params)
            else:
                # Other MiniZinc error - still try to parse stdout
                result = clean_minizinc_stdout(process.stdout, **result_params)
        else:
            result = clean_minizinc_stdout(process.stdout, **result_params)

    except subprocess.TimeoutExpired:
        # Subprocess timed out (backup timeout triggered)
        result = clean_minizinc_stdout(
            None, error=True, **result_params, error_message="Process timeout"
        )
    except KeyboardInterrupt:
        # User interrupted
        result = clean_minizinc_stdout(
            None, error=True, **result_params, error_message="Keyboard Interrupt"
        )
    except Exception as e:
        # Other unexpected errors
        print(f"Unexpected error running MiniZinc: {e}")
        result = clean_minizinc_stdout(
            None, error=True, **result_params, error_message=" Unexpected error" + e
        )
    finally:
        # Always clean up the temporary file
        if os.path.exists(temp_dzn_path):
            os.remove(temp_dzn_path)

    return result


def generate_dzn_file(
    n: int, active_constraints: list[str], all_constraints: list[str] = ALL_CONSTRAINTS
) -> str:
    """
    Generates a temporary `.dzn` file with the specified number of teams and active constraints.

    Args:
        n (int): The number of teams.
        active_constraints (list[str]): List of active constraint names.
        all_constraints (list[str]): All available constraints for the selected model version.
    Returns:
        str: The path to the generated temporary `.dzn` file.
    """
    with tempfile.NamedTemporaryFile(
        delete=False, mode="w", suffix=".dzn", dir="."
    ) as temp_dzn:
        temp_dzn.write(f"n = {n};\n")
        for var in all_constraints:
            val = "true" if var in active_constraints else "false"
            temp_dzn.write(f"{var} = {val};\n")
        temp_dzn_path = temp_dzn.name
    return temp_dzn_path


def write_results_to_json(results: list[dict], names: list[str], n: int):
    """
    Save the given results dictionaries, i. e. the Minizinc output of multiple executions to a JSON file.

    Args:
        results (list[dict]): The dictionaries containing the results of the Minizinc executions.
        names (list[str]): Names to identify each execution that generated each result.
        n (int): Number of teams used as the json file name.
    """
    filename = f"{JSON_FOLDER}/{n}.json"
    output_data = {}
    for result, name in zip(results, names):
        output_data[name] = result

    with open(filename, "w") as f:
        json.dump(output_data, f, indent=2)

    # Post-process: remove quotes around the sol list
    with open(filename, "r") as f:
        lines = f.readlines()

    with open(filename, "w") as f:
        for line in lines:
            if '"sol": "' in line:
                # Clean line: remove surrounding quotes and unescape inner quotes
                line = line.replace('\\"', '"')  # unescape quotes inside
                line = line.replace('"sol": "', '"sol": ').rstrip()
                if line.endswith('",'):
                    line = line[:-2] + ","  # remove closing quote
                f.write(line + "\n")
            else:
                f.write(line)


def run_test_mode(
    n: int,
    selected_constraints: list[str],
    is_optimization: bool = True,
    use_chuffed: bool = True,
    timeout_sec: int = 300,
    verbose: bool = False,
    num_runs: int = 5,
    max_workers: int = None,
) -> tuple[list[dict], list[str]]:
    """
    Run the MiniZinc model with all possible combinations of the selected constraints.

    Args:
        n (int): The number of teams.
        selected_constraints (list[str]): List of constraint names to test combinations of.
        is_optimization (bool): If True, use the optimization version; otherwise use non-optimization version.
        use_chuffed (bool): Whether to use the Chuffed solver (True) or Gecode (False).
        timeout_sec (int): Timeout in seconds for each model run.
        verbose (bool): Whether to show verbose output.
        num_runs (int): Number of runs to average over for each combination.
    Returns:
        tuple[list[dict], list[str]]: Results and corresponding names for each combination.
    """
    results = []
    names = []
    # Generate all possible combinations (including empty set and full set)
    for r in range(len(selected_constraints) + 1):
        for combo in combinations(selected_constraints, r):
            combo_list = list(combo)
            combo_name = f"combo_{'_'.join(combo_list) if combo_list else 'none'}"

            print(
                f"Running combination: {combo_list if combo_list else 'No constraints'}"
            )

            try:
                result = run_minizinc_with_averaging(
                    n,
                    combo_list,
                    is_optimization=is_optimization,
                    use_chuffed=use_chuffed,
                    timeout_sec=timeout_sec,
                    verbose=verbose,
                    num_runs=num_runs,
                    max_workers=max_workers,
                )
                results.append(result)
                names.append(combo_name)
            except Exception as e:
                print(f"Error running combination {combo_list}: {e}")
                # Add error result
                error_result = {
                    "time": 300,
                    "optimal": False,
                    "obj": "None",
                    "sol": None,
                    "error": str(e),
                }
                results.append(error_result)
                names.append(f"{combo_name}_error")

    return results, names

def run_select_mode(
    n: int,
    selected_group: str,
    is_optimization: bool = True,
    use_chuffed: bool = True,
    timeout_sec: int = 300,
    verbose: bool = False,
    num_runs: int = 5,
    max_workers: int = None,
) -> tuple[list[dict], list[str]]:
    """
    For each combination of the selected group's constraints, runs the MiniZinc model
    with all other constraints set to True (active).

    Args:
        n (int): The number of teams.
        selected_group (str): Selected group constraint.
        is_optimization (bool): If True, use the optimization version; otherwise use non-optimization version.
        use_chuffed (bool): Whether to use the Chuffed solver (True) or Gecode (False).
        timeout_sec (int): Timeout in seconds for each model run.
        verbose (bool): Whether to show verbose output.
        num_runs (int): Number of runs to average over for each combination.

    Returns:
        tuple[list[dict], list[str]]: Results and corresponding names for each combination.
    """
    results = []
    names = []
    all_constraints = ALL_CONSTRAINTS if is_optimization else ALL_CONSTRAINTS_NO_OPT
    if selected_group == "all":
        for group in ALL_CONSTRAINTS_GROUPS:
            group_results, group_names = run_selected_group(
                n, group, is_optimization, use_chuffed, timeout_sec, verbose, num_runs, all_constraints, max_workers
            )
            results += group_results
            names += group_names
    else:
        results, names = run_selected_group(
            n, selected_group, is_optimization, use_chuffed, timeout_sec, verbose, num_runs, all_constraints, max_workers
        )
    return results, names

def run_selected_group(
    n: int,
    selected_group: str,
    is_optimization: bool,
    use_chuffed: bool,
    timeout_sec: int,
    verbose: bool,
    num_runs: int,
    all_constraints: list[str],
    max_workers: int = None,
) -> tuple[list[dict], list[str]]:
    """
    For each combination of the selected group's constraints, runs the MiniZinc model
    with all other constraints set to True (active).

    Args:
        n (int): The number of teams.
        selected_group (str): The group name whose constraints will be varied.
        is_optimization (bool): If True, use the optimization version; otherwise use non-optimization version.
        use_chuffed (bool): Whether to use the Chuffed solver (True) or Gecode (False).
        timeout_sec (int): Timeout in seconds for each model run.
        verbose (bool): Whether to show verbose output.
        num_runs (int): Number of runs to average over for each combination.
        all_constraints (list[str]): All available constraints for the selected model version.

    Returns:
        tuple[list[dict], list[str]]: Results and corresponding names for each combination.
    """
    results = []
    names = []
    selected_constraints = ALL_CONSTRAINTS_GROUPS[selected_group]

    # Generate all possible combinations of the selected constraints
    for r in range(len(selected_constraints) + 1):
        for combo in combinations(selected_constraints, r):
            # Constraints in this combo are set to True, others in selected_constraints to False, all others to True
            combo_set = set(combo)
            active_constraints = [
                c for c in all_constraints
                if c not in selected_constraints or c in combo_set
            ]
            combo_name = f"select_group_{selected_group}_{'_'.join(combo) if combo else 'none'}"
            try:
                result = run_minizinc_with_averaging(
                    n,
                    active_constraints,
                    is_optimization=is_optimization,
                    use_chuffed=use_chuffed,
                    timeout_sec=timeout_sec,
                    verbose=verbose,
                    num_runs=num_runs,
                    max_workers=max_workers,
                )
                results.append(result)
                names.append(combo_name)
            except Exception as e:
                print(f"Error running combination {combo}: {e}")
                error_result = {
                    "time": None,
                    "optimal": False,
                    "obj": "None",
                    "sol": None,
                    "error": str(e),
                }
                results.append(error_result)
                names.append(f"{combo_name}_error")

    return results, names

def _run_single_minizinc_instance(args_tuple):
    """
    Helper function to run a single MiniZinc instance with the given parameters.
    Used for parallel execution.
    
    Args:
        args_tuple: Tuple containing (run_num, n, active_constraints, model_path, 
                   timeout_sec, use_chuffed, is_optimization, all_constraints, run_seed)
    
    Returns:
        tuple: (run_num, result) where result is the output from run_minizinc_model_cli
    """
    (run_num, n, active_constraints, model_path, timeout_sec, 
     use_chuffed, is_optimization, all_constraints, run_seed) = args_tuple
    
    result = run_minizinc_model_cli(
        n=n,
        active_constraints=active_constraints,
        model_path=model_path,
        timeout_sec=timeout_sec,
        use_chuffed=use_chuffed,
        is_optimization=is_optimization,
        all_constraints=all_constraints,
        verbose=False,  # Disable verbose for individual runs to reduce noise
        random_seed=run_seed,
    )
    
    return run_num, result


def run_minizinc_with_averaging(
    n: int,
    active_constraints: list[str] = None,
    model_path: str = None,
    timeout_sec: int = 300,
    use_chuffed: bool = True,
    is_optimization: bool = True,
    all_constraints: list[str] = None,
    verbose: bool = False,
    num_runs: int = 5,
    max_workers: int = None,
) -> dict:
    """
    Runs a MiniZinc model multiple times in parallel and computes averaged statistics for reliable measurements.

    Args:
        n (int): The number of teams.
        active_constraints (list[str]): List of constraint names to activate.
        model_path (str): Path to the `.mzn` model.
        timeout_sec (int): Timeout in seconds for each model run.
        use_chuffed (bool): Whether to use the Chuffed solver (True) or Gecode (False).
        is_optimization (bool): If True, indicates that the output is from an optimization version of the STS.
        all_constraints (list[str]): All available constraints for the selected model version.
        verbose (bool): Whether to show verbose output.
        num_runs (int): Number of runs to average over.
        max_workers (int): Maximum number of parallel workers. If None, uses min(32, num_runs, os.cpu_count() + 4).

    Returns:
        dict: Averaged results with additional statistics.
    """
    if verbose:
        print(f"Running {num_runs} times for averaging (in parallel)...")
    
    # Determine number of workers
    if max_workers is None:
        max_workers = min(32, num_runs, (os.cpu_count() or 1) + 4)
    
    if verbose:
        print(f"Using {max_workers} parallel workers...")
    
    # Prepare arguments for each run
    run_args = []
    for run_num in range(num_runs):
        # Generate a unique random seed for each run
        run_seed = random.randint(1, 2**31 - 1)
        run_args.append((
            run_num, n, active_constraints, model_path, timeout_sec,
            use_chuffed, is_optimization, all_constraints, run_seed
        ))
    
    # Execute runs in parallel
    results = [None] * num_runs  # Pre-allocate list to maintain order
    completed_runs = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        future_to_run = {executor.submit(_run_single_minizinc_instance, args): args[0] 
                        for args in run_args}
        
        # Collect results as they complete
        for future in as_completed(future_to_run):
            run_num = future_to_run[future]
            try:
                run_num, result = future.result()
                results[run_num] = result
                completed_runs += 1
                
                if verbose:
                    print(f"  Completed run {completed_runs}/{num_runs} (run #{run_num + 1})")
                    
            except Exception as exc:
                if verbose:
                    print(f"  Run {run_num + 1} generated an exception: {exc}")
                # Create error result
                results[run_num] = {
                    "time": timeout_sec,
                    "optimal": False,
                    "obj": "None",
                    "sol": f'"Exception: {str(exc)}"',
                    "solver": "chuffed" if use_chuffed else "gecode",
                    "constraints": active_constraints,
                }
      # Process results (same as before)
    valid_times = []
    valid_objs = []
    successful_runs = 0
    errors = []
    
    for result in results:
        # Cap time at timeout if it exceeds
        if isinstance(result.get("time"), (int, float)) and result["time"] > timeout_sec:
            result["time"] = timeout_sec
            
        # Check if this run was successful (not error, timeout, or unsat)
        if (result.get("sol") != []):
            
            successful_runs += 1
            
            # Collect valid timing data
            time_val = result.get("time")
            if time_val is not None and time_val != "unknown" and isinstance(time_val, (int, float)):
                valid_times.append(time_val)
            
            # Collect valid objective values for optimization problems
            if is_optimization:
                obj_val = result.get("obj")
                if obj_val is not None and isinstance(obj_val, (int, float)):
                    valid_objs.append(obj_val)
        else:
            # Track errors
            error_msg = result.get("sol", "unknown error")
            errors.append(error_msg)
    
    # If no successful runs, return the last result as is
    if successful_runs == 0:
        last_result = results[-1].copy()
        last_result["runs_info"] = {
            "total_runs": num_runs,
            "successful_runs": 0,
            "errors": errors,
        }
        return last_result
    
    # Compute statistics from successful runs
    avg_result = results[0].copy()  # Use first result as template
    
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
    
    # Compute objective statistics for optimization problems
    obj_stats = None
    if is_optimization and valid_objs:
        avg_result["obj"] = round(statistics.mean(valid_objs), 2)
        obj_stats = {
            "mean": round(statistics.mean(valid_objs), 2),
            "median": round(statistics.median(valid_objs), 2),
            "min": min(valid_objs),
            "max": max(valid_objs),
        }
        if len(valid_objs) > 1:
            obj_stats["stdev"] = round(statistics.stdev(valid_objs), 2)
        else:
            obj_stats["stdev"] = 0
    
    # Determine if solution is optimal (majority of runs were optimal and within time limit)
    optimal_runs = sum(1 for r in results if r.get("optimal") == True or r.get("optimal") is True)
    avg_result["optimal"] = True if optimal_runs > num_runs / 2 else False
    
    # Use the best solution found across all runs
    best_obj = None
    best_sol = None
    for result in results:
        if result.get("sol") != []:
            if is_optimization:
                obj_val = result.get("obj")
                if obj_val is not None and (best_obj is None or obj_val < best_obj):  # Assuming minimization
                    best_obj = obj_val
                    best_sol = result.get("sol")
            else:
                best_sol = result.get("sol")
                break
    
    if best_sol is not None:
        avg_result["sol"] = best_sol
    if best_obj is not None:
        avg_result["obj"] = best_obj
    
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


def main():
    """Main function to handle command-line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Run MiniZinc model with configurable constraints"
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
        help="Try with a combination of one of the following groups: symm, implied, search. "
             "If used without a value, all grouped constraints will be used.",
    )

    # List of constraint strings
    parser.add_argument(
        "-c",
        "--constraints",
        nargs="*",
        default=ALL_CONSTRAINTS,
        help="List of constraint names to activate (default: all constraints)",    )
    
    # Optimization flag
    parser.add_argument(
        "--no-opt",
        action="store_true",
        help="Use non-optimized version (stsNoOpt.mzn) instead of optimized version (sts.mzn)",
    )
    
    # Solver flags
    solver_group = parser.add_mutually_exclusive_group()
    solver_group.add_argument(
        "--chuffed",
        action="store_true",
        help="Use Chuffed solver only",
    )
    solver_group.add_argument(
        "--gecode",
        action="store_true",
        help="Use Gecode solver only",
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
    )    # Runs flag for averaging
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

    args = parser.parse_args()
    
    # Determine which version to use
    is_optimization = not args.no_opt
      # Determine which solver(s) to use
    if args.chuffed:
        solvers_to_use = ["chuffed"]
    elif args.gecode:
        solvers_to_use = ["gecode"]
    else:
        # Neither specified - run with both
        solvers_to_use = ["chuffed", "gecode"]
    
    available_constraints = (
        ALL_CONSTRAINTS if is_optimization else ALL_CONSTRAINTS_NO_OPT
    )

    # Set default constraints if none provided
    if args.constraints == ALL_CONSTRAINTS and not is_optimization:
        args.constraints = ALL_CONSTRAINTS_NO_OPT
    # Validate constraint names
    invalid_constraints = [
        c for c in args.constraints if c not in available_constraints
    ]
    if invalid_constraints:
        print(f"Error: Invalid constraint names: {invalid_constraints}")
        print(f"Available constraints: {available_constraints}")
        return 1    
    # Run the model based on mode
    print(f"Running MiniZinc model with {args.teams} teams")
    print(
        f"Mode: {'Generate' if args.generate else 'Test' if args.test else 'Default'}"
    )
    print(f"Version: {'Optimized' if is_optimization else 'Non-optimized'}")
    print(f"Solver(s): {', '.join(solvers_to_use)}")
    print(f"Timeout: {args.timeout} seconds")
    print(f"Runs per measurement: {args.runs}")
    if args.select:
        print(f"Selected constraint group: {args.select}")
    else:
        print(f"Selected constraints: {args.constraints}")

    results = []
    names = []

    # Run for each solver
    for solver_name in solvers_to_use:
        use_chuffed = (solver_name == "chuffed")
        print(f"\n--- Running with {solver_name.upper()} solver ---")
        
        if args.test:
            # Test mode: try all possible combinations of the selected constraints
            print("Test mode: Running all possible combinations of selected constraints...")
            print(f"Each combination will be run {args.runs} times for reliable measurements.")
            solver_results, solver_names_list = run_test_mode(
                args.teams, args.constraints, is_optimization, use_chuffed, args.timeout, args.verbose, args.runs, args.max_workers
            )
            # Add solver suffix to names
            solver_results_named = solver_results
            solver_names_with_solver = [f"{name}_{solver_name}" for name in solver_names_list]
            results.extend(solver_results_named)
            names.extend(solver_names_with_solver)
        elif args.select:
            # Select group mode: run with all possible combinations of the selected constraint group
            print("Select group mode: Running all possible combinations of selected group constraint...")
            print(f"Each combination will be run {args.runs} times for reliable measurements.")
            solver_results, solver_names_list = run_select_mode(
                args.teams, args.select, is_optimization, use_chuffed, args.timeout, args.verbose, args.runs, args.max_workers
            )
            # Add solver suffix to names
            solver_results_named = solver_results
            solver_names_with_solver = [f"{name}_{solver_name}" for name in solver_names_list]
            results.extend(solver_results_named)
            names.extend(solver_names_with_solver)
        else:
            # Generate mode: run once with all selected constraints active
            print("Generate mode: Running with all selected constraints active...")
            print(f"Will run {args.runs} times for reliable measurements.")
            result = run_minizinc_with_averaging(
                args.teams,
                args.constraints,
                is_optimization=is_optimization,
                use_chuffed=use_chuffed,
                timeout_sec=args.timeout,
                verbose=args.verbose,
                num_runs=args.runs,
                max_workers=args.max_workers,
            )
            results.append(result)
            names.append(f"generate_all_constraints_{solver_name}")
    # Save results
    write_results_to_json(results, names, args.teams)
    print(f"Results saved to {JSON_FOLDER}/{args.teams}.json")
    print(f"Total executions: {len(results)}")
    if args.runs > 1:
        print(f"Each execution was averaged over {args.runs} runs for reliable measurements.")

    return 0


if __name__ == "__main__":
    exit(main())
