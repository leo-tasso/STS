import math
import tempfile
import subprocess
import os
import json
import argparse
from itertools import combinations

DZN_PATH = "source/CP/use_constraints.dzn"
MODEL_PATH = "source/CP/sts.mzn"
JSON_FOLDER = "res/CP"
VARIABLE_PREFIX = "use_constraint_"

def read_constraint_names_from_dzn(dzn_path: str = DZN_PATH, variable_prefix: str = VARIABLE_PREFIX) -> dict[str,]:
    """
    Reads a MiniZinc `.dzn` data file and extracts all boolean constraint toggles
    whose names start with `variable_prefix`.

    Parameters:
        dzn_path (str): The file path to the `.dzn` file.

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

def clean_minizinc_stdout(stdout: str) -> dict:
    """
    Cleans the MiniZinc stdout output by removing unnecessary lines and formatting.
    
    Args:
        stdout (str): The raw output from MiniZinc.
        
    Returns:
        dict: Cleaned output as a dictionary.
    """

    # Handle unsat case, like for n = 4
    unsat = "UNSATISFIABLE" in stdout
    if unsat:
        return {
            "time": None,
            "optimal": "false",
            "obj": None,
            "sol": "unsat"
        }
    
    cleaned_output = json.loads(stdout.split("%")[0].strip())
    time_elapsed = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("% time elapsed:"):
            parts = line.split()
            if len(parts) >= 5:
                time_elapsed = int(parts[3])

    ordered_output = {
        "time": time_elapsed,
        "optimal": "true" if time_elapsed < 300 else "false",
        "obj": cleaned_output["obj"],
        "sol": cleaned_output["sol"]
    }

    return ordered_output

def run_minizinc_model_cli(n: int, active_constraints: list[str] = ALL_CONSTRAINTS, model_path: str = MODEL_PATH, timeout_sec: int = 300):
    """
    Runs a MiniZinc model via the CLI, setting constraint flags by a temporary `.dzn` file.
    
    Args:
        n (int): The number of teams.
        model_path (str): Path to the `.mzn` model.
        active_constraints (list[str]): List of constraint names to activate.
        timeout (int): Timeout in seconds for the model run.
        
    Returns:
        str: The stdout of the MiniZinc execution.
    """

    temp_dzn_path = generate_dzn_file(n, active_constraints)

    timeout_flag = ["--time-limit", str(timeout_sec * 1000)]

    try:
        cmd = ["minizinc", "--output-time", *timeout_flag, model_path, temp_dzn_path]
        process = subprocess.run(cmd, capture_output=True, text=True)
        result = clean_minizinc_stdout(process.stdout)  
        return result
    finally:
        os.remove(temp_dzn_path)

def generate_dzn_file(n: int, active_constraints: list[str]) -> str:
    """
    Generates a temporary `.dzn` file with the specified number of teams and active constraints.

    Args:
        n (int): The number of teams.
        active_constraints (list[str]): List of active constraint names.
    Returns:
        str: The path to the generated temporary `.dzn` file.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.dzn', dir=".") as temp_dzn:
        temp_dzn.write(f"n = {n};\n")
        for var in ALL_CONSTRAINTS:
            val = "true" if var in active_constraints else "false"
            temp_dzn.write(f"{var} = {val};\n")
        temp_dzn_path = temp_dzn.name
    return temp_dzn_path


# TODO: more compact way to save "sol" list in JSON
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



def run_test_mode(n: int, selected_constraints: list[str]) -> tuple[list[dict], list[str]]:
    """
    Run the MiniZinc model with all possible combinations of the selected constraints.
    
    Args:
        n (int): The number of teams.
        selected_constraints (list[str]): List of constraint names to test combinations of.
        
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
            
            print(f"Running combination: {combo_list if combo_list else 'No constraints'}")
            
            try:
                result = run_minizinc_model_cli(n, combo_list)
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
                       help='List of constraint names to activate (default: all constraints)')
    
    args = parser.parse_args()
    
    # Validate constraint names
    invalid_constraints = [c for c in args.constraints if c not in ALL_CONSTRAINTS]
    if invalid_constraints:
        print(f"Error: Invalid constraint names: {invalid_constraints}")
        print(f"Available constraints: {ALL_CONSTRAINTS}")
        return 1
      # Run the model based on mode
    print(f"Running MiniZinc model with {args.teams} teams")
    print(f"Mode: {'Generate' if args.generate else 'Test' if args.test else 'Default'}")
    print(f"Selected constraints: {args.constraints}")
    
    results = []
    names = []
    
    if args.test:
        # Test mode: try all possible combinations of the selected constraints
        print("Test mode: Running all possible combinations of selected constraints...")
        results, names = run_test_mode(args.teams, args.constraints)
    elif args.generate:
        # Generate mode: run once with all selected constraints active
        print("Generate mode: Running with all selected constraints active...")
        result = run_minizinc_model_cli(args.teams, args.constraints)
        results = [result]
        names = ["generate_all_constraints"]
    else:
        # Default mode: run with all selected constraints active
        print("Default mode: Running with all selected constraints active...")
        result = run_minizinc_model_cli(args.teams, args.constraints)
        results = [result]
        names = ["default"]
    
    # Save results
    write_results_to_json(results, names, args.teams)
    print(f"Results saved to {JSON_FOLDER}/{args.teams}.json")
    print(f"Total executions: {len(results)}")
    
    return 0

if __name__ == "__main__":
    exit(main())