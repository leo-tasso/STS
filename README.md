# Sports Tournament Scheduling (STS) - Multi-Paradigm Optimization

A comprehensive platform for solving sports tournament scheduling using four different optimization approaches: **Constraint Programming (CP)**, **Mixed Integer Programming (MIP)**, **Boolean Satisfiability (SAT)**, and **Satisfiability Modulo Theories (SMT)**.

## Quick Start

### Option 1: Docker (Recommended)

1. **Build and run**
   ```bash
   docker build -t sts-solver .
   docker-compose up -d
   docker-compose exec sts bash
   ```

2. **Run examples inside the container:**
   ```bash
   # Constraint Programming
   cd test/CP && python run_CP.py -n 6
   
   # Mixed Integer Programming  
   cd test/MIP && python run_MIP.py -n 6
   
   # SAT Solver
   cd test/SAT && python run_SAT.py 6
   
   # All paradigms, more info on usage below
   cd test && python run_all_models.py -n 6
   ```

### Option 2: Local Installation

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install MiniZinc** (for CP): Download from https://www.minizinc.org/

3. **Install CVC5** (for SMT): Download from https://github.com/cvc5/cvc5/releases

4. **Run Examples:**
   ```bash
   # Constraint Programming
   python test/CP/run_CP.py -n 6
   
   # Mixed Integer Programming  
   python test/MIP/run_MIP.py -n 6
   
   # SAT Solver
   python test/SAT/run_SAT.py 6
   
   # All paradigms
   python test/run_all_models.py -n 6
   ```



## Project Structure

```
source/
├── CP/          # MiniZinc constraint programming models
├── MIP/         # PuLP mixed integer programming
├── SAT/         # Z3 SAT encoding implementations  
└── SMT/         # Z3 SMT theory solver

test/
├── run_all_models.py    # Cross-paradigm comparison
├── CP/run_CP.py         # CP solver runner
├── MIP/run_MIP.py       # MIP solver runner
├── SAT/run_SAT.py       # SAT solver runner
└── SMT/run_SMT.py       # SMT solver runner
```

## Key Constraints

- **Symmetry Breaking:** Week/period/team ordering
- **Implied Constraints:** Match counts and appearances
- **Optimization:** Minimize home/away imbalances (CP/MIP)

## Results Format

All solvers output JSON with:
- Schedule matrix (team × week × period)
- Solution statistics (time, objective, solver)
- Constraint satisfaction verification

## Unified Runner: run_all_models.py

You can run all (or selected) models for multiple team sizes using the unified runner script:

```bash
python test/run_all_models.py
```

By default, this runs all models (CP, MIP, SAT, SMT) for even team numbers from 2 to 12.

### Common options:

- `--models CP MIP` &nbsp;&nbsp;&nbsp;&nbsp;Run only selected models.
- `--n-values 6 8 10` &nbsp;&nbsp;&nbsp;&nbsp;Specify exact team numbers.
- `--start 4 --end 10 --step 2` &nbsp;&nbsp;&nbsp;&nbsp;Range of team numbers.
- `--mode test` &nbsp;&nbsp;&nbsp;&nbsp;Run in test mode.
- `--timeout 600` &nbsp;&nbsp;&nbsp;&nbsp;Set timeout per run (seconds).
- `--no-parallel` &nbsp;&nbsp;&nbsp;&nbsp;Run models sequentially.
- `--no-validate` &nbsp;&nbsp;&nbsp;&nbsp;Skip solution validation.
- `--output results.json` &nbsp;&nbsp;&nbsp;&nbsp;Set output file name.

### Example usages:

```bash
# Run all models for n=6,8,10
python test/run_all_models.py --n-values 6 8 10

# Run only CP and MIP for n=4 to 10
python test/run_all_models.py --models CP MIP --start 4 --end 10 --step 2

# Run in test mode with longer timeout
python test/run_all_models.py --mode test --timeout 600
```

The script will print a summary and save results to a JSON file. It also validates solutions using the checker.

## Solution Checker

You can verify the validity of solution JSON files using the provided checker script:

```bash
python test/solution_checker.py <path_to_json_directory>
```

- `<path_to_json_directory>`: Directory containing one or more `.json` files produced by the solvers.
- The script will print the validity status and reasons for each solution in every file.

Example usage:
```bash
python test/solution_checker.py test/results/
```

## Features

- **Multi-run averaging** for statistical reliability
- **Parallel execution** for performance
- **Docker environment** with all dependencies
- **Cross-paradigm comparison** tools
- **Experimental section** for advanced features

---


