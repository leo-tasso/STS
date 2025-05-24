import tempfile
import subprocess
import os
import json

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

def clean_minizinc_stdout(stdout: str) -> str:
    """
    Cleans the MiniZinc stdout output by removing unnecessary lines and formatting.
    
    Args:
        stdout (str): The raw output from MiniZinc.
        
    Returns:
        str: Cleaned output string.
    """

    cleaned_output = json.loads(stdout.split("%")[0].strip())
    time_elapsed = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("% time elapsed:"):
            parts = line.split()
            if len(parts) >= 5:
                time_elapsed = float(parts[3])

    ordered_output = {
        "time": time_elapsed,
        "optimal": "true" if time_elapsed < 300 else "false",
        "obj": cleaned_output["obj"],
        "sol": str(cleaned_output["sol"])
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


def write_result_to_json(result: dict, name: str, n: int, append_result: bool = False):
    """
    Save the given result dictionary, i. e. the Minizinc output to a JSON file.
    
    Args:
        result (dict): The dictionary containing the result of the Minizinc execution.
        name (str): Name to identify the execution that generated this result.
        n (int): Number of teams used as the json file name.
        append_result (bool) : If True, append the result to the existing file, otherwise overwrite it.
    """

    result = {
        name: result
    }
    filename = f"{JSON_FOLDER}/{n}.json"
    with open(filename, "a" if append_result else "w") as f:
        json.dump(result, f, indent=2)

n = 6
result = run_minizinc_model_cli(n)
write_result_to_json(result, "test", n)