"""
Unified runner script for all STS models (CP, MIP, SAT, SMT).

This script provides a simple interface to launch all 4 models with customizable
team numbers and test configurations. It runs each model with its respective
runner script and collects results.
"""

import os
import subprocess
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional


class STSModelRunner:
    """Unified runner for all STS models."""
    
    def __init__(self, base_dir: str = None):
        """Initialize the runner with base directory."""
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        
        # Define paths to runner scripts
        self.runners = {
            'CP': os.path.join(self.base_dir, 'CP', 'run_CP.py'),
            'MIP': os.path.join(self.base_dir, 'MIP', 'run_MIP.py'),
            'SAT': os.path.join(self.base_dir, 'SAT', 'run_SAT.py'),
            'SMT': os.path.join(self.base_dir, 'SMT', 'run_SMT.py')
        }
        
        # Verify all runners exist
        for model, path in self.runners.items():
            if not os.path.exists(path):
                print(f"Warning: Runner for {model} not found at {path}")
    
    def _get_python_executable(self) -> str:
        """Get the correct Python executable to use."""
        # Check if we're in a virtual environment
        venv_python = os.path.join(self.base_dir, '..', '.venv', 'Scripts', 'python.exe')
        if os.path.exists(venv_python):
            return venv_python
        
        # Fallback to system python
        return "python"
    
    def run_single_model(self, model: str, n: int, mode: str = "generate", 
                        timeout: int = 300, verbose: bool = False,
                        additional_args: List[str] = None) -> Tuple[str, Dict]:
        """
        Run a single model with specified parameters.
        
        Args:
            model: Model type ('CP', 'MIP', 'SAT', 'SMT')
            n: Number of teams
            mode: Running mode ('generate', 'test', 'select')
            timeout: Timeout in seconds
            verbose: Enable verbose output
            additional_args: Additional command-line arguments
            
        Returns:
            Tuple of (model_name, result_dict)
        """
        if model not in self.runners:
            return model, {"error": f"Unknown model: {model}"}
        
        runner_path = self.runners[model]
        if not os.path.exists(runner_path):
            return model, {"error": f"Runner not found: {runner_path}"}
        
        # Build command based on model type
        # Use the correct Python executable
        python_exe = self._get_python_executable()
        cmd = [python_exe, runner_path]
        
        # Add model-specific arguments
        if model in ['CP', 'MIP']:
            cmd.extend(["-n", str(n)])
        else:  # SAT, SMT
            cmd.append(str(n))
        
        # Add mode
        if mode == "generate":
            cmd.append("--generate")
        elif mode == "test":
            cmd.append("--test")
        elif mode.startswith("select"):
            if ":" in mode:
                _, group = mode.split(":", 1)
                cmd.extend(["--select", group])
            else:
                cmd.append("--select")
        
        # Add timeout
        cmd.extend(["--timeout", str(timeout)])
        
        # Add verbose flag
        if verbose:
            cmd.extend(["-v" if model in ['CP', 'MIP'] else "--verbose"])
        
        # Add additional arguments
        if additional_args:
            cmd.extend(additional_args)
        
        print(f"Running {model} with n={n}: {' '.join(cmd)}")
        
        try:
            start_time = time.time()
            
            # Set up environment to ensure Python path is correct
            env = os.environ.copy()
            runner_dir = os.path.dirname(runner_path)
            
            # Add the source directory to PYTHONPATH for the subprocess
            source_dir = os.path.abspath(os.path.join(runner_dir, '..', '..', 'source', model))
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = source_dir + os.pathsep + env['PYTHONPATH']
            else:
                env['PYTHONPATH'] = source_dir
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 60,  # Add buffer for script overhead
                cwd=runner_dir,
                env=env
            )
            end_time = time.time()
            
            # Debug output for troubleshooting
            if result.returncode != 0 and verbose:
                print(f"DEBUG {model}: Return code {result.returncode}")
                print(f"DEBUG {model}: STDERR: {result.stderr[:500]}")
                if result.stdout:
                    print(f"DEBUG {model}: STDOUT: {result.stdout[:200]}")
            
            return model, {
                "n": n,
                "model": model,
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": end_time - start_time,
                "command": ' '.join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            return model, {
                "n": n,
                "model": model,
                "success": False,
                "error": "Timeout",
                "execution_time": timeout + 60,
                "command": ' '.join(cmd)
            }
        except Exception as e:
            return model, {
                "n": n,
                "model": model,
                "success": False,
                "error": str(e),
                "execution_time": 0,
                "command": ' '.join(cmd)
            }
    
    def run_all_models(self, n_values: List[int], models: List[str] = None,
                      mode: str = "generate", timeout: int = 300,
                      verbose: bool = False, parallel: bool = True,
                      additional_args: Dict[str, List[str]] = None) -> Dict:
        """
        Run all specified models for all n values.
        
        Args:
            n_values: List of team numbers to test
            models: List of models to run (default: all)
            mode: Running mode
            timeout: Timeout per run
            verbose: Enable verbose output
            parallel: Run models in parallel
            additional_args: Model-specific additional arguments
            
        Returns:
            Dictionary with results
        """
        if models is None:
            models = list(self.runners.keys())
        
        if additional_args is None:
            additional_args = {}
        
        all_results = []
        
        # Create list of all tasks
        tasks = []
        for n in n_values:
            for model in models:
                if model in self.runners:
                    tasks.append((model, n, mode, timeout, verbose, 
                                additional_args.get(model, [])))
        
        print(f"Running {len(tasks)} total experiments...")
        
        if parallel and len(tasks) > 1:
            # Run in parallel
            with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as executor:
                future_to_task = {
                    executor.submit(self.run_single_model, *task): task 
                    for task in tasks
                }
                
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    model, result = future.result()
                    all_results.append(result)
                    
                    status = "✓" if result.get("success", False) else "✗"
                    print(f"{status} {model} n={result.get('n', '?')} "
                          f"({result.get('execution_time', 0):.2f}s)")
        else:
            # Run sequentially
            for task in tasks:
                model, result = self.run_single_model(*task)
                all_results.append(result)
                
                status = "✓" if result.get("success", False) else "✗"
                print(f"{status} {model} n={result.get('n', '?')} "
                      f"({result.get('execution_time', 0):.2f}s)")
        
        # Organize results
        results_by_model = {}
        for result in all_results:
            model = result.get("model", "unknown")
            if model not in results_by_model:
                results_by_model[model] = []
            results_by_model[model].append(result)
        
        return {
            "summary": {
                "total_runs": len(all_results),
                "successful_runs": sum(1 for r in all_results if r.get("success", False)),
                "failed_runs": sum(1 for r in all_results if not r.get("success", False)),
                "models_tested": list(results_by_model.keys()),
                "n_values": n_values,
                "mode": mode,
                "timeout": timeout
            },
            "results_by_model": results_by_model,
            "all_results": all_results
        }
    
    def save_results(self, results: Dict, output_file: str = None):
        """Save results to JSON file."""
        if output_file is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"all_models_results_{timestamp}.json"
        
        output_path = os.path.join(self.base_dir, output_file)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {output_path}")
        return output_path
    
    def validate_solutions(self, models: List[str], verbose: bool = False) -> Dict:
        """
        Validate solutions in the res folder using solution_checker.py.
        
        Args:
            models: List of models to validate
            verbose: Enable verbose output
            
        Returns:
            Dictionary with validation results
        """
        print("\n" + "="*60)
        print("SOLUTION VALIDATION")
        print("="*60)
        
        # Path to solution checker
        checker_path = os.path.join(self.base_dir, 'solution_checker.py')
        if not os.path.exists(checker_path):
            print(f"Warning: Solution checker not found at {checker_path}")
            return {"error": "Solution checker not found"}
        
        # Base results directory
        res_dir = os.path.join(self.base_dir, '..', 'res')
        if not os.path.exists(res_dir):
            print(f"Warning: Results directory not found at {res_dir}")
            return {"error": "Results directory not found"}
        
        validation_results = {}
        overall_valid = True
        python_exe = self._get_python_executable()
        
        for model in models:
            model_dir = os.path.join(res_dir, model)
            if not os.path.exists(model_dir):
                print(f"No results directory for {model}: {model_dir}")
                validation_results[model] = {"status": "no_results", "details": "Directory not found"}
                continue
            
            # Check if there are any JSON files
            json_files = [f for f in os.listdir(model_dir) if f.endswith('.json')]
            if not json_files:
                print(f"No JSON files found for {model}")
                validation_results[model] = {"status": "no_files", "details": "No JSON files found"}
                continue
            
            print(f"Validating {model} solutions...")
            
            try:
                # Run solution checker
                cmd = [python_exe, checker_path, model_dir]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,  # 1 minute timeout for validation
                    cwd=self.base_dir
                )
                
                if result.returncode != 0:
                    print(f"  ✗ {model}: Solution checker failed")
                    if verbose:
                        print(f"    STDERR: {result.stderr}")
                    validation_results[model] = {
                        "status": "checker_failed",
                        "return_code": result.returncode,
                        "stderr": result.stderr,
                        "stdout": result.stdout
                    }
                    overall_valid = False
                    continue
                
                # Parse output to check for invalid solutions
                output_lines = result.stdout.strip().split('\n')
                invalid_found = False
                details = []
                
                current_file = None
                for line in output_lines:
                    if line.startswith('File: '):
                        current_file = line.replace('File: ', '').strip()
                    elif 'Status: INVALID' in line:
                        invalid_found = True
                        if current_file:
                            details.append(f"Invalid solution in {current_file}")
                        else:
                            details.append("Invalid solution found")
                
                if invalid_found:
                    print(f"  ✗ {model}: Invalid solutions found")
                    if verbose:
                        for detail in details:
                            print(f"    {detail}")
                    validation_results[model] = {
                        "status": "invalid",
                        "details": details,
                        "full_output": result.stdout
                    }
                    overall_valid = False
                else:
                    print(f"  ✓ {model}: All solutions valid")
                    validation_results[model] = {
                        "status": "valid",
                        "files_checked": len(json_files),
                        "full_output": result.stdout if verbose else None
                    }
                
            except subprocess.TimeoutExpired:
                print(f"  ✗ {model}: Validation timeout")
                validation_results[model] = {"status": "timeout", "details": "Validation timed out"}
                overall_valid = False
            except Exception as e:
                print(f"  ✗ {model}: Validation error: {e}")
                validation_results[model] = {"status": "error", "details": str(e)}
                overall_valid = False
        
        validation_results["overall_valid"] = overall_valid
        
        print(f"\nValidation complete. Overall status: {'VALID' if overall_valid else 'INVALID'}")
        
        return validation_results

    def print_summary(self, results: Dict, validation_results: Dict = None):
        """Print a summary of results and validation."""
        summary = results["summary"]
        
        print("\n" + "="*60)
        print("EXPERIMENT SUMMARY")
        print("="*60)
        print(f"Total runs: {summary['total_runs']}")
        print(f"Successful: {summary['successful_runs']}")
        print(f"Failed: {summary['failed_runs']}")
        print(f"Models: {', '.join(summary['models_tested'])}")
        print(f"Team numbers: {summary['n_values']}")
        print(f"Mode: {summary['mode']}")
        print(f"Timeout: {summary['timeout']}s")
        
        print("\nRESULTS BY MODEL:")
        print("-"*40)
        
        for model, model_results in results["results_by_model"].items():
            successful = sum(1 for r in model_results if r.get("success", False))
            total = len(model_results)
            avg_time = sum(r.get("execution_time", 0) for r in model_results 
                          if r.get("success", False)) / max(successful, 1)
            
            print(f"{model:>4}: {successful:>2}/{total} successful "
                  f"(avg: {avg_time:.2f}s)")
            
            # Show failed runs
            failed = [r for r in model_results if not r.get("success", False)]
            if failed:
                print(f"      Failed n values: {[r.get('n') for r in failed]}")
        
        # Print validation summary if available
        if validation_results:
            print(f"\nVALIDATION SUMMARY:")
            print("-"*40)
            overall_status = "VALID" if validation_results.get("overall_valid", False) else "INVALID"
            print(f"Overall validation status: {overall_status}")
            
            for model, result in validation_results.items():
                if model == "overall_valid":
                    continue
                    
                status = result.get("status", "unknown")
                if status == "valid":
                    files_checked = result.get("files_checked", 0)
                    print(f"{model:>4}: ✓ Valid ({files_checked} files checked)")
                elif status == "invalid":
                    details_count = len(result.get("details", []))
                    print(f"{model:>4}: ✗ Invalid ({details_count} issues found)")
                elif status == "no_results":
                    print(f"{model:>4}: - No results to validate")
                elif status == "no_files":
                    print(f"{model:>4}: - No JSON files found")
                else:
                    print(f"{model:>4}: ? {status.title()}")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Run all STS models with customizable parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all models for n=2,4,6,8,10,12 in generate mode
  python run_all_models.py
  
  # Run specific models for custom range
  python run_all_models.py --models CP MIP --start 6 --end 10 --step 2
  
  # Run in test mode with longer timeout
  python run_all_models.py --mode test --timeout 600
  
  # Run specific team numbers
  python run_all_models.py --n-values 6 8 10 12
  
  # Run sequentially (not in parallel)
  python run_all_models.py --no-parallel
  
  # Skip solution validation
  python run_all_models.py --no-validate
        """
    )
    
    # Team number specification
    n_group = parser.add_mutually_exclusive_group()
    n_group.add_argument(
        "--n-values",
        nargs="+",
        type=int,
        help="Specific team numbers to test"
    )
    n_group.add_argument(
        "--start",
        type=int,
        default=2,
        help="Starting team number (default: 2)"
    )
    
    parser.add_argument(
        "--end",
        type=int,
        default=12,
        help="Ending team number (default: 12)"
    )
    
    parser.add_argument(
        "--step",
        type=int,
        default=2,
        help="Step between team numbers (default: 2)"
    )
    
    # Model selection
    parser.add_argument(
        "--models",
        nargs="+",
        choices=["CP", "MIP", "SAT", "SMT"],
        default=["CP", "MIP", "SAT", "SMT"],
        help="Models to run (default: all)"
    )
    
    # Running mode
    parser.add_argument(
        "--mode",
        choices=["generate", "test", "select", "select:symm", "select:implied", "select:all"],
        default="generate",
        help="Running mode (default: generate)"
    )
    
    # Other parameters
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per run in seconds (default: 300)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Run models sequentially instead of in parallel"
    )
    
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip solution validation at the end"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file name"
    )
    
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file"
    )
    
    # Model-specific arguments
    parser.add_argument(
        "--cp-args",
        nargs="*",
        help="Additional arguments for CP model"
    )
    
    parser.add_argument(
        "--mip-args",
        nargs="*",
        help="Additional arguments for MIP model"
    )
    
    parser.add_argument(
        "--sat-args",
        nargs="*",
        help="Additional arguments for SAT model"
    )
    
    parser.add_argument(
        "--smt-args",
        nargs="*",
        help="Additional arguments for SMT model"
    )
    
    args = parser.parse_args()
    
    # Determine n values
    if args.n_values:
        n_values = args.n_values
    else:
        n_values = list(range(args.start, args.end + 1, args.step))
    
    # Filter to even numbers only (STS requirement)
    n_values = [n for n in n_values if n % 2 == 0 and n >= 2]
    
    if not n_values:
        print("Error: No valid team numbers specified (must be even and >= 2)")
        return 1
    
    print(f"Running models {args.models} for team numbers: {n_values}")
    
    # Prepare additional arguments
    additional_args = {}
    if args.cp_args:
        additional_args["CP"] = args.cp_args
    if args.mip_args:
        additional_args["MIP"] = args.mip_args
    if args.sat_args:
        additional_args["SAT"] = args.sat_args
    if args.smt_args:
        additional_args["SMT"] = args.smt_args
    
    # Create runner and execute
    runner = STSModelRunner()
    
    results = runner.run_all_models(
        n_values=n_values,
        models=args.models,
        mode=args.mode,
        timeout=args.timeout,
        verbose=args.verbose,
        parallel=not args.no_parallel,
        additional_args=additional_args
    )
    
    # Validate solutions if not disabled
    validation_results = None
    if not args.no_validate:
        validation_results = runner.validate_solutions(args.models, args.verbose)
    
    # Print summary
    runner.print_summary(results, validation_results)
    
    # Save results
    if not args.no_save:
        # Include validation results in the saved data
        if validation_results:
            results["validation"] = validation_results
        runner.save_results(results, args.output)
    
    # Return appropriate exit code
    if validation_results and not validation_results.get("overall_valid", True):
        print("\nExiting with code 1 due to invalid solutions.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())