import math
import tempfile
import subprocess
import os
import json
import argparse
from itertools import combinations

# Optimized version paths
DZN_PATH = "../../source/CP/use_constraints.dzn"
MODEL_PATH = "../../source/CP/sts.mzn"

# Non-optimized version paths
DZN_PATH_NO_OPT = "../../source/CP/use_constraintsNoOpt.dzn"
MODEL_PATH_NO_OPT = "../../source/CP/stsNoOpt.mzn"

JSON_FOLDER = "../../res/CP"
VARIABLE_PREFIX = "use_constraint_"

def read_constraint_names_from_dzn(dzn_path: str = DZN_PATH, variable_prefix: str = VARIABLE_PREFIX) -> list[str]:
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

def clean_minizinc_stdout(
        stdout: str, 
        expired_timeout: bool = False, 
        timeout_sec: int = 300,
        optimization_version: bool = True,
        use_chuffed: bool = True,
        all_constraints: list[str] = None) -> dict:
    """
    Cleans the MiniZinc stdout output by removing unnecessary lines and formatting.
    
    Args:
        stdout (str): The raw output from MiniZinc.
        expired_timeout (bool): If True, indicates that the MiniZinc run timed out.
        timeout_sec (int): The timeout duration in seconds, default is 300.
        optimization_version (bool): If True, indicates that the output is from an optimization version of the STS.
        use_chuffed (bool): Whether it was used the Chuffed solver (True) or Gecode (False).
        all_constraints (list[str]): All available constraints used for the selected model version.
        
    Returns:
        dict: Cleaned output as a dictionary.
    """

    solver = "chuffed" if use_chuffed else "gecode"

    # Handle timeout case, like for large n
    if expired_timeout or stdout is None or stdout.strip() == "":
        return {
            "time": timeout_sec,
            "optimal": "false",
            "obj": None,
            "sol": "timeout",
            "solver": solver,
            "constraints": all_constraints
        }
    
    # Handle unsat case, like for n = 4
    unsat = "UNSATISFIABLE" in stdout
    if unsat:
        return {
            "time": None,
            "optimal": "false",
            "obj": None,
            "sol": "unsat",
            "solver": solver, 
            "constraints": all_constraints
        }
    
    # Check if MiniZinc timed out internally (produces incomplete output)
    if "=====UNKNOWN=====" in stdout or stdout.count("{") != stdout.count("}"):
        return {
            "time": timeout_sec,
            "optimal": "false",
            "obj": None,
            "sol": "timeout",
            "solver": solver,
            "constraints": all_constraints
        }
    
    try:
        # Try to parse JSON output
        json_part = stdout.split("%")[0].strip()
        if not json_part:
            # No JSON output - likely timeout
            return {
                "time": timeout_sec,
                "optimal": "false",
                "obj": None,
                "sol": "timeout",
                "solver": solver,
                "constraints": all_constraints
            }
        
        cleaned_output = json.loads(json_part)
    except (json.JSONDecodeError, ValueError):
        # JSON parsing failed - likely timeout or invalid output
        return {
            "time": timeout_sec,
            "optimal": "false",
            "obj": None,
            "sol": "timeout",
            "solver": solver,
            "constraints": all_constraints
        }
    
    # Extract time elapsed from MiniZinc output
    time_elapsed = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("% time elapsed:"):
            parts = line.split()
            if len(parts) >= 5:
                time_elapsed = math.floor(float(parts[3]))
                break

    # If no time was found but we have valid output, set time to 0
    if time_elapsed is None:
        time_elapsed = 0

    ordered_output = {
        "time": time_elapsed,
        "optimal": "true" if time_elapsed < timeout_sec else "false",
        "obj": cleaned_output.get("obj") if optimization_version else None,
        "sol": str(cleaned_output.get("sol", "unknown")),
        "solver": solver,
        "constraints": all_constraints
    }

    return ordered_output

def run_minizinc_model_cli(
        n: int, 
        active_constraints: list[str] = None, 
        model_path: str = None, 
        timeout_sec: int = 300,
        use_chuffed: bool = True,
        is_optimization: bool = True,
        all_constraints: list[str] = None
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
        
    Returns:
        dict: The cleaned output from the MiniZinc execution.
    """
    # Set defaults based on optimization version
    if active_constraints is None:
        active_constraints = ALL_CONSTRAINTS if is_optimization else ALL_CONSTRAINTS_NO_OPT
    if model_path is None:
        model_path = MODEL_PATH if is_optimization else MODEL_PATH_NO_OPT
    if all_constraints is None:
        all_constraints = ALL_CONSTRAINTS if is_optimization else ALL_CONSTRAINTS_NO_OPT

    temp_dzn_path = generate_dzn_file(n, active_constraints, all_constraints)

    # MiniZinc expects timeout in milliseconds
    timeout_flag = ["--time-limit", str(timeout_sec * 1000)]
    solver_flag = ["--solver", "chuffed" if use_chuffed else "gecode"]

    result_params = {
        "timeout_sec": timeout_sec,
        "optimization_version": is_optimization,
        "all_constraints": all_constraints
    }

    try:
        cmd = ["minizinc", "--output-time", *timeout_flag, *solver_flag, model_path, temp_dzn_path]
        
        # Use subprocess timeout as a backup (add 10 seconds buffer for MiniZinc to cleanup)
        process_timeout = timeout_sec + 10
        
        process = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=process_timeout
        )
        
        # Check if the process completed successfully
        if process.returncode != 0 and process.stderr:
            # Handle MiniZinc errors
            if "time limit exceeded" in process.stderr.lower() or "timeout" in process.stderr.lower():
                result = clean_minizinc_stdout(None, expired_timeout=True, **result_params)
            else:
                # Other MiniZinc error - still try to parse stdout
                result = clean_minizinc_stdout(process.stdout, **result_params)
        else:
            result = clean_minizinc_stdout(process.stdout, **result_params)
            
    except subprocess.TimeoutExpired:
        # Subprocess timed out (backup timeout triggered)
        result = clean_minizinc_stdout(None, expired_timeout=True, **result_params)
    except KeyboardInterrupt:
        # User interrupted
        result = clean_minizinc_stdout(None, expired_timeout=True, **result_params)
    except Exception as e:
        # Other unexpected errors
        print(f"Unexpected error running MiniZinc: {e}")
        result = clean_minizinc_stdout(None, expired_timeout=True, **result_params)
    finally:
        # Always clean up the temporary file
        if os.path.exists(temp_dzn_path):
            os.remove(temp_dzn_path)

    return result

def generate_dzn_file(n: int, active_constraints: list[str], all_constraints: list[str] = ALL_CONSTRAINTS) -> str:
    """
    Generates a temporary `.dzn` file with the specified number of teams and active constraints.

    Args:
        n (int): The number of teams.
        active_constraints (list[str]): List of active constraint names.
        all_constraints (list[str]): All available constraints for the selected model version.
    Returns:
        str: The path to the generated temporary `.dzn` file.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.dzn', dir=".") as temp_dzn:
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
            if '"sol": "' in line and "unsat"  not in line and "timeout" not in line:
                # Clean line: remove surrounding quotes and unescape inner quotes
                line = line.replace('\\"', '"')  # unescape quotes inside
                line = line.replace('"sol": "', '"sol": ').rstrip()
                if line.endswith('",'):
                    line = line[:-2] + ","  # remove closing quote
                f.write(line + "\n")
            else:
                f.write(line)



def run_test_mode(n: int, selected_constraints: list[str], is_optimization: bool = True, use_chuffed: bool = True, timeout_sec: int = 300) -> tuple[list[dict], list[str]]:
    """
    Run the MiniZinc model with all possible combinations of the selected constraints.
    
    Args:
        n (int): The number of teams.
        selected_constraints (list[str]): List of constraint names to test combinations of.
        is_optimization (bool): If True, use the optimization version; otherwise use non-optimization version.
        use_chuffed (bool): Whether to use the Chuffed solver (True) or Gecode (False).
        timeout_sec (int): Timeout in seconds for each model run.
    Returns:
        tuple[list[dict], list[str]]: Results and corresponding names for each combination.    """
    results = []
    names = []
    # Generate all possible combinations (including empty set and full set)
    for r in range(len(selected_constraints) + 1):
        for combo in combinations(selected_constraints, r):
            combo_list = list(combo)
            combo_name = f"combo_{'_'.join(combo_list) if combo_list else 'none'}"
            
            print(f"Running combination: {combo_list if combo_list else 'No constraints'}")
            
            try:
                result = run_minizinc_model_cli(n, combo_list, is_optimization=is_optimization, use_chuffed=use_chuffed, timeout_sec=timeout_sec)
                results.append(result)
                names.append(combo_name)
            except Exception as e:
                print(f"Error running combination {combo_list}: {e}")
                # Add error result
                error_result = {
                    "time": None,
                    "optimal": "false",
                    "obj": None,
                    "sol": None,
                    "error": str(e)
                }
                results.append(error_result)
                names.append(f"{combo_name}_error")
    
    return results, names

def main():
    """Main function to handle command-line arguments and execute the script."""
    parser = argparse.ArgumentParser(description="Run MiniZinc model with configurable constraints")
    
    # Required parameter: number of teams
    parser.add_argument('-n', '--teams', type=int, required=True, 
                       help='Number of teams (required)')
    
    # Mutually exclusive group for -g or -t
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-g', '--generate', action='store_true',
                      help='Generate mode with the selected constraints')
    group.add_argument('-t', '--test', action='store_true', 
                      help='Test mode, tries all possible combinations of the selected constraints')
      # List of constraint strings
    parser.add_argument('-c', '--constraints', nargs='*', default=ALL_CONSTRAINTS,
                       help='List of constraint names to activate (default: all constraints)')    # Optimization flag
    parser.add_argument('--no-opt', action='store_true',
                       help='Use non-optimized version (stsNoOpt.mzn) instead of optimized version (sts.mzn)')
      # Solver flag
    parser.add_argument('--gecode', action='store_true',
                       help='Use Gecode solver instead of Chuffed (default: Chuffed)')
    
    # Timeout flag
    parser.add_argument('--timeout', type=int, default=300,
                       help='Solver timeout in seconds (default: 300)')
    
    args = parser.parse_args()
      # Determine which version to use
    is_optimization = not args.no_opt
    use_chuffed = not args.gecode
    available_constraints = ALL_CONSTRAINTS if is_optimization else ALL_CONSTRAINTS_NO_OPT
    
    # Set default constraints if none provided
    if args.constraints == ALL_CONSTRAINTS and not is_optimization:
        args.constraints = ALL_CONSTRAINTS_NO_OPT
      # Validate constraint names
    invalid_constraints = [c for c in args.constraints if c not in available_constraints]
    if invalid_constraints:
        print(f"Error: Invalid constraint names: {invalid_constraints}")
        print(f"Available constraints: {available_constraints}")
        return 1
      # Run the model based on mode
    print(f"Running MiniZinc model with {args.teams} teams")
    print(f"Mode: {'Generate' if args.generate else 'Test' if args.test else 'Default'}")
    print(f"Version: {'Optimized' if is_optimization else 'Non-optimized'}")
    print(f"Solver: {'Chuffed' if use_chuffed else 'Gecode'}")
    print(f"Timeout: {args.timeout} seconds")
    print(f"Selected constraints: {args.constraints}")
    
    results = []
    names = []
    
    if args.test:
        # Test mode: try all possible combinations of the selected constraints
        print("Test mode: Running all possible combinations of selected constraints...")
        results, names = run_test_mode(args.teams, args.constraints, is_optimization, use_chuffed, args.timeout)
    else:
        # Generate mode: run once with all selected constraints active
        print("Generate mode: Running with all selected constraints active...")
        result = run_minizinc_model_cli(args.teams, args.constraints, is_optimization=is_optimization, use_chuffed=use_chuffed, timeout_sec=args.timeout)
        results = [result]
        names = ["generate_all_constraints"]
    
    # Save results
    write_results_to_json(results, names, args.teams)
    print(f"Results saved to {JSON_FOLDER}/{args.teams}.json")
    print(f"Total executions: {len(results)}")
    
    return 0

if __name__ == "__main__":
    exit(main())