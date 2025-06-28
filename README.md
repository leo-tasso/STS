# Sports Tournament Scheduling (STS) - Constraint Programming and SAT Solver

This repository contains both Constraint Programming (MiniZinc) and SAT-based (Z3) solutions for sports tournament scheduling, along with Python scripts for running experiments with different constraint configurations.

## 🚀 Quick Start

**TL;DR: Using Docker (Recommended)**
```bash
docker-compose up -d
docker-compose exec sts bash
cd /app/test/CP && python run_CP.py -n 6 --chuffed
# Results appear in ./res folder on your host machine
```

## Quick Start with Docker

The easiest way to get started is using Docker, which provides a pre-configured environment with all dependencies:

### Docker Prerequisites
- Docker Desktop or Docker Engine installed
- Docker Compose (usually included with Docker Desktop)

### Docker Usage

#### Method 1: Docker Compose (Recommended)
This is the preferred method as it automatically handles volume mounting and environment setup:

```bash
# Build and start the container
docker-compose up -d

# Connect to the running container
docker-compose exec sts bash

# Inside the container, run experiments:
cd /app/test/CP
python run_CP.py -n 6 --chuffed
python run_CP.py -n 8 --gecode

# Results will automatically appear in your host ./res folder
```

#### Method 2: Direct Docker Run
If you prefer using `docker run` directly, you must manually specify volume mounts:

```bash
# Windows PowerShell
docker run -it --rm `
  -v "${PWD}/res:/app/res" `
  -v "${PWD}/test:/app/test" `
  -v "${PWD}/source:/app/source" `
  -w /app `
  sts-sts bash

# Linux/macOS
docker run -it --rm \
  -v "$(pwd)/res:/app/res" \
  -v "$(pwd)/test:/app/test" \
  -v "$(pwd)/source:/app/source" \
  -w /app \
  sts-sts bash
```

#### Volume Mounting
The Docker setup mounts key directories as volumes:
- `./res` - Results are persisted to your host machine
- `./test` - Test scripts can be modified on host
- `./source` - Source code can be modified on host

This allows you to edit files on your host machine and see changes immediately in the container.

#### Running Experiments in Docker
Once inside the container, you can run all the examples:

```bash
# Test MiniZinc 2.9.3 installation
minizinc --version
minizinc --solvers

# CP experiments
cd /app/test/CP
python run_CP.py -n 6 --chuffed
python run_CP.py -n 8 --gecode
python run_CP.py --teams 6 --timeout 60

# SAT experiments  
cd /app/test/SAT
python run_SAT.py 6 --generate
python run_SAT.py 8 --test --encoding bw

# SMT experiments
cd /app/test/SMT
python run_SMT.py --teams 6
```

#### Container Management
```bash
# Start the container
docker-compose up -d

# Stop the container
docker-compose down

# Rebuild after changes to Dockerfile
docker-compose up --build -d

# View container logs
docker-compose logs

# Clean up (removes container and volumes)
docker-compose down --volumes

# Clean up everything (including images)
docker-compose down --volumes --rmi all
```

#### Troubleshooting Docker
- **Files not appearing on host**: Ensure you're using `docker-compose exec sts` instead of `docker run` without volume mounts
- **Permission issues**: On Linux, you may need to run `sudo chown -R $USER:$USER res/` after running experiments
- **Container won't start**: Run `docker-compose down` then `docker-compose up --build -d` to rebuild

## Overview

The system provides two complementary approaches for generating balanced sports tournament schedules:

**Constraint Programming (CP) Approach:**
- Uses MiniZinc with Chuffed/Gecode solvers
- Supports optimization objectives (minimize home/away imbalance)
- Advanced search strategies and constraint formulations
- Best for larger instances and when solution quality matters

**SAT Solver Approach:**
- Uses Z3 SMT solver with Boolean satisfiability
- Focuses on finding any valid solution efficiently
- Multiple SAT encoding strategies available
- Best for smaller instances and constraint analysis

Both approaches ensure:
- Each pair of teams plays exactly once
- Each team plays exactly once per week
- Teams appear in the same time period at most twice
- Home/away assignments are balanced

# Constraint Programming (CP) Implementation

The CP implementation uses MiniZinc with Chuffed or Gecode solvers to find optimal tournament schedules.

## CP Prerequisites

### Required Software
1. **Python 3.7+** - For running the control script
2. **MiniZinc** - For solving the constraint programming model
   - Download from: https://www.minizinc.org/
   - Ensure `minizinc` is available in your system PATH

### Required Files
- `source/CP/sts.mzn` - MiniZinc optimized model file
- `source/CP/stsNoOpt.mzn` - MiniZinc non-optimized model file
- `source/CP/use_constraints.dzn` - Constraint configuration file (optimized)
- `source/CP/use_constraintsNoOpt.dzn` - Constraint configuration file (non-optimized)
- `test/CP/run_CP.py` - Python control script

## File Structure

```
STS/
├── source/
│   ├── CP/                        # Constraint Programming implementation
│   │   ├── sts.mzn               # MiniZinc optimized constraint model
│   │   ├── stsNoOpt.mzn         # MiniZinc non-optimized constraint model
│   │   ├── use_constraints.dzn   # Available constraints definition (optimized)
│   │   └── use_constraintsNoOpt.dzn # Available constraints definition (non-optimized)
│   └── SAT/                      # SAT solver implementation
│       ├── sts.py               # Core SAT implementation
│       └── sat_encodings.py     # SAT encoding methods
├── test/
│   ├── CP/
│   │   └── run_CP.py            # Python execution script for CP
│   └── SAT/
│       ├── run_STS.py           # Python execution script for SAT
│       └── README.md            # SAT-specific documentation
├── res/                         # Results directory (auto-created)
│   ├── CP/
│   │   └── {n}.json            # CP results for n teams
│   └── SAT/
│       └── {n}.json            # SAT results for n teams
└── README.md                    # This file
```

## CP Available Constraints

The CP implementation supports the following constraint types:

**Symmetry Breaking Constraints:**
- `use_symm_break_weeks` - Break symmetry between weeks
- `use_symm_break_periods` - Break symmetry between periods  
- `use_symm_break_teams` - Fix team ordering in first week

**Implied Constraints:**
- `use_implied_matches_per_team` - Enforce exact match count per team
- `use_implied_period_count` - Enforce period appearance limits

**Search Strategy Constraints:**
- `use_int_search` - Advanced integer search strategy
- `use_restart_luby` - Luby restart strategy for solver
- `use_relax_and_reconstruct` - Relax-and-reconstruct search method

## CP Usage

### Basic CP Command Structure

```bash
python run_CP.py -n <teams> [mode] [constraints] [options]
```

### CP Parameters

- **`-n, --teams`** (required): Number of teams (must be even)
- **`-g, --generate`** (optional): Generate mode - run once with selected constraints
- **`-t, --test`** (optional): Test mode - try all combinations of selected constraints
- **`-s, --select`** (optional): Select group mode – systematically tests all possible combinations of a group of related constraints, with every other constraint always enabled.  
- **`-c, --constraints`** (optional): List of constraints to activate (default: all)
- **`--no-opt`** (optional): Use non-optimized model version (stsNoOpt.mzn instead of sts.mzn)
- **`--chuffed`** (optional): Use Chuffed solver only
- **`--gecode`** (optional): Use Gecode solver only
- **`--timeout`** (optional): Solver timeout in seconds (default: 300)
- **`-v, --verbose`** (optional): Enable verbose output showing intermediate solutions
- **`--runs`** (optional): Number of runs to average over for reliable measurements (default: 5)
- **`--max-workers`** (optional): Maximum number of parallel workers for execution (default: auto-detect based on CPU count)

### CP Execution Modes

#### 1. Default Mode
Runs the optimized model with all available constraints enabled. If neither `--chuffed` nor `--gecode` is specified, the system will run with both solvers for comparison.

```bash
# Run with 6 teams using all constraints (both solvers)
python run_CP.py -n 6

# Run with 6 teams using Chuffed solver only
python run_CP.py -n 6 --chuffed

# Run with 6 teams using Gecode solver only
python run_CP.py -n 6 --gecode

# Run with 6 teams using non-optimized model
python run_CP.py -n 6 --no-opt

# Run with 6 teams and custom timeout of 10 minutes
python run_CP.py -n 6 --timeout 600

# Run with verbose output to see intermediate solutions
python run_CP.py -n 6 --verbose

# Run with custom number of averaged runs for reliable measurements
python run_CP.py -n 6 --runs 10

# Run with custom parallel workers for faster execution
python run_CP.py -n 6 --max-workers 8
```

#### 2. Generate Mode (`-g`)
Runs the model with only the specified constraints enabled. Multiple runs are averaged for reliable measurements.

```bash
# Run with 8 teams using only symmetry breaking constraints
python run_CP.py -n 8 -g -c use_symm_break_weeks use_symm_break_teams

# Run with specific solver
python run_CP.py -n 8 -g -c use_symm_break_weeks use_symm_break_teams --chuffed

# Run with non-optimized model and Gecode solver
python run_CP.py -n 8 -g -c use_symm_break_weeks use_symm_break_teams --no-opt --gecode

# Run with custom timeout and verbose output
python run_CP.py -n 8 -g -c use_symm_break_weeks use_symm_break_teams --timeout 600 --verbose

# Run with custom number of averaged runs
python run_CP.py -n 8 -g -c use_symm_break_weeks use_symm_break_teams --runs 10

# Run with parallel execution for faster performance
python run_CP.py -n 8 -g -c use_symm_break_weeks use_symm_break_teams --max-workers 4
```

#### 3. Test Mode (`-t`)
Systematically tests all possible combinations of the specified constraints with multiple runs averaged for each combination.

```bash
# Test all combinations of 2 constraints with 6 teams
python run_CP.py -n 6 -t -c use_symm_break_slots use_symm_break_weeks

# Test all combinations using specific solver
python run_CP.py -n 6 -t -c use_symm_break_slots use_symm_break_weeks --gecode

# Test with non-optimized model and custom averaging
python run_CP.py -n 6 -t -c use_symm_break_slots use_symm_break_weeks --no-opt --runs 3

# Test with parallel execution for faster performance
python run_CP.py -n 6 -t -c use_symm_break_slots use_symm_break_weeks --max-workers 8
```

This will run multiple experiments (each averaged over several runs):
- No constraints
- Only `use_symm_break_slots`
- Only `use_symm_break_weeks`
- Both constraints together

#### 4. Select group mode (`-s`):
For each group (or the specified group), the script generates **all possible combinations** (including the empty set) of the constraints in that group.
 
For each combination, it runs the model with:
- The constraints in the combination set to `True`
- The other constraints in the group set to `False`
- **All other constraints (not in the group) set to `True`**

Available groups for `-s`:

- `symm` – All symmetry breaking constraints
- `implied` – All implied constraints 
- `search` – All search strategy constraints 
- `all` (or just `-s` with no value) – Runs all combinations for all groups above

```bash
# Try all combinations of symmetry-breaking constraints (others always enabled)
python run_CP.py -n 8 -s symm

# Try all combinations of implied constraints (others always enabled)
python run_CP.py -n 8 -s implied

# Try all combinations of search strategy constraints (others always enabled)
python run_CP.py -n 8 -s search

# Try all combinations for all groups (symm, implied, search)
python run_CP.py -n 8 -s

# Use with solver and other options
python run_CP.py -n 8 -s symm --gecode --timeout 600 --runs 3

# Use with parallel execution for faster performance
python run_CP.py -n 8 -s symm --max-workers 6
```

### CP Examples

```bash
# Quick test with minimal constraints
python run_CP.py -n 4 -g -c use_symm_break_teams

# Same test using non-optimized model
python run_CP.py -n 4 -g -c use_symm_break_teams --no-opt

# Quick test using specific solver
python run_CP.py -n 4 -g -c use_symm_break_teams --gecode

# Comprehensive constraint analysis with verbose output
python run_CP.py -n 6 -t -c use_symm_break_weeks use_symm_break_periods use_implied_matches_per_team --verbose

# Same analysis using non-optimized model with Gecode
python run_CP.py -n 6 -t -c use_symm_break_weeks use_symm_break_periods use_implied_matches_per_team --no-opt --gecode

# Large tournament with all constraints (runs with both solvers)
python run_CP.py -n 12 -g

# Large tournament using specific solver only
python run_CP.py -n 12 -g --chuffed

# Run with extended timeout for difficult instances
python run_CP.py -n 14 -g --timeout 900  # 15 minutes

# Quick test with short timeout and reduced averaging
python run_CP.py -n 8 -g --timeout 60 --runs 3

# Run with parallel execution for faster performance
python run_CP.py -n 8 -g --max-workers 4

# Compare solver performance for same configuration
python run_CP.py -n 8 -g --chuffed  # Chuffed only
python run_CP.py -n 8 -g --gecode   # Gecode only

# Compare model versions with same solver
python run_CP.py -n 8 -g --chuffed         # Optimized + Chuffed
python run_CP.py -n 8 -g --no-opt --chuffed # Non-optimized + Chuffed

# Test with search strategy constraints
python run_CP.py -n 6 -g -c use_int_search use_restart_luby use_relax_and_reconstruct

# Help and available options
python run_CP.py --help
```

## CP Output Format

CP results are saved as JSON files in `res/CP/{n}.json` where `n` is the number of teams.

The script displays execution information during runtime:
```
Running Tournament Scheduling (Teams: 8, Version: Optimized, Solver: Chuffed)
Using all constraints
Timeout: 300 seconds
Runs per measurement: 5
Running 5 times for averaging (in parallel)...
Using 8 parallel workers...
Running MiniZinc model...
```

### CP JSON Structure

```json
{
  "execution_name": {
    "time": 67,             // Average execution time in seconds
    "optimal": "true",      // Whether optimal solution was found
    "obj": 1,               // Average objective value (max home/away imbalance)
    "sol": [                // Best tournament schedule found
      [                     // Week 1
        [1, 4],             // Period 1: Team 1 vs Team 4 (home, away)
        [2, 5],             // Period 2: Team 2 vs Team 5
        [3, 6]              // Period 3: Team 3 vs Team 6
      ],
      // ... more weeks
    ],
    "solver": "chuffed",    // Solver used
    "constraints": [...],   // List of active constraints
    "runs_info": {          // Statistics from multiple runs
      "total_runs": 5,
      "successful_runs": 5,
      "optimal_runs": 5       // Number of runs that found optimal solutions
    },
    "time_stats": {         // Time statistics across runs
      "mean": 67,
      "median": 65,
      "min": 62,
      "max": 72,
      "stdev": 3.2
    },
    "obj_stats": {          // Objective statistics across runs
      "mean": 1.0,
      "median": 1,
      "min": 1,
      "max": 1,
      "stdev": 0
    },
    "error": "..."          // Error message (if execution failed)
  }
}
```

### Interpreting Results

- **`time`**: Average solver execution time across runs (null if error occurred)
- **`optimal`**: "true" if optimal solution found within time limit in majority of runs
- **`obj`**: Average objective value - maximum imbalance between home/away games across all teams (lower is better)
- **`sol`**: Best tournament schedule found as [week][period][home_team, away_team]
- **`solver`**: Solver used (chuffed or gecode)
- **`constraints`**: List of active constraints used
- **`runs_info`**: Statistics about the multiple runs performed
  - `total_runs`: Total number of runs attempted
  - `successful_runs`: Number of runs that completed successfully
  - `optimal_runs`: Number of runs that found optimal solutions
- **`time_stats`**: Detailed timing statistics (mean, median, min, max, standard deviation)
- **`obj_stats`**: Detailed objective value statistics (for optimization problems)
- **`error`**: Present only if execution failed

## Model Versions and Solvers

### Model Versions

The system provides two model versions:

1. **Optimized Model** (default): `sts.mzn`
   - Enhanced with advanced constraints and optimization techniques
   - Generally faster solving times
   - Uses `use_constraints.dzn` for constraint definitions

2. **Non-optimized Model** (`--no-opt`): `stsNoOpt.mzn`
   - Basic constraint formulation without advanced optimizations
   - Useful for comparing optimization effectiveness
   - Uses `use_constraintsNoOpt.dzn` for constraint definitions

### Solvers

The system supports two MiniZinc solvers and can run with both automatically for comparison:

1. **Chuffed** (default when using `--chuffed`)
   - Lazy clause generation solver
   - Generally effective for constraint satisfaction problems
   - Good balance of speed and solution quality

2. **Gecode** (when using `--gecode`)
   - Finite domain constraint solver
   - Alternative solving approach
   - May perform better on specific problem instances

3. **Both Solvers** (default when neither `--chuffed` nor `--gecode` is specified)
   - Runs experiments with both solvers for comprehensive comparison
   - Results are saved with solver-specific naming

### Comparative Analysis

Use different combinations to analyze performance:

```bash
# Compare solvers with optimized model
python run_CP.py -n 8 -g --chuffed  # Chuffed only
python run_CP.py -n 8 -g --gecode   # Gecode only
python run_CP.py -n 8 -g             # Both solvers

# Compare model versions with specific solver
python run_CP.py -n 8 -g --chuffed         # Chuffed + Optimized  
python run_CP.py -n 8 -g --no-opt --chuffed # Chuffed + Non-optimized

# Compare all combinations with a single command
python run_CP.py -n 8 -g  # Runs with both Chuffed and Gecode

# Compare averaging reliability
python run_CP.py -n 8 -g --runs 1   # Single run
python run_CP.py -n 8 -g --runs 10  # More reliable averaging

# Control parallel execution performance
python run_CP.py -n 8 -g --max-workers 1   # Sequential execution
python run_CP.py -n 8 -g --max-workers 16  # Maximum parallelism
```

You can use the `-s/--select` option to systematically compare the effect of enabling/disabling constraints within a group (symm, implied, search), while keeping all other constraints enabled. This allows for focused comparative analysis of constraint groups.

## Performance Analysis

Use test mode to compare constraint effectiveness across different configurations:

```bash
# Compare symmetry breaking strategies with different solvers
python run_CP.py -n 8 -t -c use_symm_break_weeks use_symm_break_periods use_symm_break_teams
python run_CP.py -n 8 -t -c use_symm_break_weeks use_symm_break_periods use_symm_break_teams --gecode

# Compare model optimization effectiveness
python run_CP.py -n 8 -t -c use_symm_break_weeks use_symm_break_periods  # Optimized
python run_CP.py -n 8 -t -c use_symm_break_weeks use_symm_break_periods --no-opt  # Non-optimized

# Test search strategy constraints
python run_CP.py -n 8 -t -c use_int_search use_restart_luby use_relax_and_reconstruct

# Test with different timeout values to analyze time sensitivity
python run_CP.py -n 12 -g --timeout 60   # Quick timeout
python run_CP.py -n 12 -g --timeout 600  # Extended timeout

# Compare reliability with different run counts
python run_CP.py -n 8 -g --runs 1   # Fast but less reliable
python run_CP.py -n 8 -g --runs 10  # Slower but more reliable

# Control parallel execution for performance tuning
python run_CP.py -n 8 -g --max-workers 1   # Sequential execution
python run_CP.py -n 8 -g --max-workers 16  # Maximum parallelism
```

Key metrics to analyze:
- **Solving time**: Lower average time is better for practical use
- **Optimal solutions**: More constraints may help find optimal solutions faster
- **Solution quality**: Compare average objective values across different constraint sets
- **Solver performance**: Different solvers may excel on different problem instances
- **Optimization impact**: Compare optimized vs non-optimized model performance
- **Timeout sensitivity**: Analyze how different timeout values affect solution quality and completion rates
- **Statistical reliability**: Use time_stats and obj_stats to assess measurement reliability
- **Parallel execution efficiency**: Use --max-workers to optimize performance for your system's CPU capabilities

## Parallel Execution and Performance Optimization

The system leverages parallel execution to significantly improve performance when running multiple experiments:

### How Parallel Execution Works
- **Concurrent Runs**: When averaging over multiple runs (e.g., `--runs 10`), all runs execute simultaneously in parallel
- **Thread-Based**: Uses Python's ThreadPoolExecutor for efficient I/O-bound parallel execution
- **Per-Experiment Parallelization**: Each constraint combination or test mode experiment runs its multiple averaging runs in parallel
- **Automatic Coordination**: Results are collected and synchronized automatically as parallel runs complete

### Performance Benefits
- **Dramatically Reduced Runtime**: 5 runs that might take 25 minutes sequentially can complete in ~5 minutes with parallel execution
- **Scalable**: Performance improves with more CPU cores (up to the number of parallel runs)
- **Efficient Resource Usage**: Maximizes CPU utilization during solver-intensive operations

### Configuring Parallel Execution
```bash
# Let the system auto-detect optimal worker count (recommended)
python run_CP.py -n 8 -g

# Use specific number of workers
python run_CP.py -n 8 -g --max-workers 4

# Sequential execution (disable parallelism)
python run_CP.py -n 8 -g --max-workers 1

# Maximum parallelism (useful for high-core systems)
python run_CP.py -n 8 -g --max-workers 16
```

### Worker Count Guidelines
- **Default**: `min(32, num_runs, os.cpu_count() + 4)` - balances performance and resource usage
- **High CPU Systems**: Use `--max-workers 16` or higher for systems with 12+ cores
- **Memory-Constrained Systems**: Use `--max-workers 2-4` to limit concurrent solver instances
- **Sequential Debugging**: Use `--max-workers 1` when debugging solver behavior or for deterministic execution order

### Performance Monitoring
The system provides real-time feedback on parallel execution:
```
Running 10 times for averaging (in parallel)...
Using 8 parallel workers...
  Completed run 1/10 (run #3)
  Completed run 2/10 (run #1)
  Completed run 3/10 (run #5)
  ...
```

# SAT Solver for Social Tournament Scheduling

In addition to the Constraint Programming approach using MiniZinc, this repository also includes a SAT-based implementation using the Z3 SMT solver.

## SAT Implementation Overview

The SAT solver provides an alternative approach to solving Social Tournament Scheduling problems using Boolean satisfiability. This implementation:
- Uses Z3 SMT solver for Boolean constraint solving
- Provides similar constraint options as the CP version
- Supports multiple SAT encoding strategies
- Offers comparable performance analysis capabilities

## SAT Prerequisites

### Required Software
1. **Python 3.7+** - For running the SAT solver
2. **Z3 Python bindings** - Install with `pip install z3-solver`

### Required Files
- `source/SAT/sts.py` - Core SAT implementation
- `source/SAT/sat_encodings.py` - Various SAT encoding methods (naive, sequential, bitwise, Heule)
- `test/SAT/run_STS.py` - Python control script for SAT solver

## SAT File Structure

```
STS/
├── source/SAT/
│   ├── sts.py                     # Core SAT implementation
│   └── sat_encodings.py           # SAT encoding methods
├── test/SAT/
│   ├── run_STS.py                # Python execution script for SAT
│   └── README.md                 # SAT-specific documentation
├── res/SAT/                      # SAT results directory (auto-created)
│   └── {n}.json                  # SAT results for n teams
└── README.md                     # This file
```

## SAT Available Constraints

The SAT implementation supports the following constraint types:

**Symmetry Breaking Constraints:**
- `use_symm_break_weeks` - Break symmetry between weeks using lexicographic ordering
- `use_symm_break_periods` - Break symmetry between periods using lexicographic ordering
- `use_symm_break_teams` - Fix team ordering in first week to break team symmetry

**Implied Constraints:**
- `use_implied_matches_per_team` - Enforce exact match count per team (redundant but can help solver)
- `use_implied_period_count` - Enforce period appearance limits (redundant but can help solver)

## SAT Encoding Types

The SAT implementation supports multiple encoding strategies for Boolean constraints, each with different performance characteristics:

**Available Encoding Types:**
- **`np` (Naive Pairwise)** - Simple pairwise constraints, comprehensive but can be slow for large instances
- **`seq` (Sequential)** - Sequential encoding with auxiliary variables, generally efficient
- **`bw` (Bitwise)** - Bitwise encoding using binary representation, good for exactly-one constraints (default)
- **`he` (Heule)** - Heule encoding with recursive decomposition, effective for at-most-one constraints

**Encoding Performance Characteristics:**
- **Bitwise (bw)**: Best overall performance for most instances, compact encoding
- **Sequential (seq)**: Reliable performance, good balance of size and efficiency  
- **Heule (he)**: Effective for constraint decomposition, scales well
- **Naive Pairwise (np)**: Simple but can generate many constraints, use with caution on larger instances

**Note**: For constraints requiring at-most-k or exactly-k encodings (where k > 1), bitwise and Heule encodings fall back to sequential encoding since they only provide at-most-one and exactly-one variants.

## SAT Usage

### Basic SAT Command Structure

```powershell
python run_STS.py <teams> [mode] [constraints] [options]
```

### SAT Parameters

- **`teams`** (required): Number of teams (must be even, minimum 4)
- **`--generate`** (optional): Generate mode - run with all selected constraints (default)
- **`--test`** (optional): Test mode - try all combinations of selected constraints  
- **`--select`** (optional): Select group mode - test combinations of constraint groups
- **`--constraints`** (optional): List of constraints to activate (default: all)
- **`--encoding`** (optional): SAT encoding type to use (default: bw)
  - `np`: Naive pairwise encoding
  - `seq`: Sequential encoding  
  - `bw`: Bitwise encoding (default)
  - `he`: Heule encoding
- **`--timeout`** (optional): Solver timeout in seconds (default: 300)
- **`--verbose`** (optional): Enable verbose output
- **`--runs`** (optional): Number of runs to average over (default: 5)
- **`--max-workers`** (optional): Maximum parallel workers (default: auto-detect)

### SAT Execution Modes

#### 1. Generate Mode (Default)
Runs the SAT solver with specified constraints enabled:

```powershell
# Generate solution for 6 teams with all constraints (default bitwise encoding)
python run_STS.py 6 --generate

# Generate solution with specific constraints and encoding
python run_STS.py 8 --generate --constraints use_symm_break_teams use_implied_matches_per_team --encoding seq

# Generate with sequential encoding and custom timeout
python run_STS.py 6 --generate --encoding seq --timeout 120 --runs 10

# Compare different encoding types
python run_STS.py 6 --generate --encoding np --runs 3 --verbose  # Naive pairwise
python run_STS.py 6 --generate --encoding he --runs 3 --verbose  # Heule encoding
```

#### 2. Test Mode
Systematically tests all combinations of specified constraints:

```powershell
# Test all combinations with sequential encoding
python run_STS.py 6 --test --constraints use_symm_break_weeks use_symm_break_teams --encoding seq

# Test with Heule encoding and verbose output 
python run_STS.py 6 --test --constraints use_symm_break_weeks use_symm_break_teams --encoding he --verbose

# Compare encoding performance across all constraint combinations
python run_STS.py 6 --test --constraints use_symm_break_weeks --encoding bw  # Bitwise
python run_STS.py 6 --test --constraints use_symm_break_weeks --encoding he --runs 3  # Heule
```

#### 3. Select Group Mode
Tests all combinations within constraint groups:

```powershell
# Test all combinations of symmetry breaking constraints with Heule encoding
python run_STS.py 8 --select symm --encoding he --timeout 300

# Test all combinations of implied constraints with sequential encoding
python run_STS.py 6 --select implied --encoding seq --runs 3

# Test all constraint groups with bitwise encoding
python run_STS.py 8 --select all --encoding bw --runs 5
```

### SAT Examples

```powershell
# Quick test with 6 teams using default bitwise encoding
python run_STS.py 6 --generate --runs 1 --timeout 30

# Test different encoding types with 6 teams
python run_STS.py 6 --generate --encoding np --runs 1  # Naive pairwise
python run_STS.py 6 --generate --encoding seq --runs 1 # Sequential  
python run_STS.py 6 --generate --encoding bw --runs 1  # Bitwise (default)
python run_STS.py 6 --generate --encoding he --runs 1  # Heule

# Comprehensive encoding comparison with constraint analysis
python run_STS.py 8 --select symm --encoding seq --runs 3 --timeout 120 --verbose

# Test specific constraint combinations with Heule encoding
python run_STS.py 10 --test --constraints use_symm_break_weeks use_symm_break_teams --encoding he --runs 5

# Compare encoding performance on larger instances
python run_STS.py 10 --test --constraints use_symm_break_weeks --encoding bw --runs 3  # Bitwise
python run_STS.py 10 --test --constraints use_symm_break_weeks --encoding he --runs 3  # Heule

# Batch test all encoding types (useful for performance analysis)
python run_STS.py 6 --test --constraints use_symm_break_teams --encoding np --runs 1  
python run_STS.py 6 --test --constraints use_symm_break_teams --encoding seq --runs 1
python run_STS.py 6 --test --constraints use_symm_break_teams --encoding bw --runs 1
python run_STS.py 6 --test --constraints use_symm_break_teams --encoding he --runs 1
```

## SAT Output Format

SAT results are saved as JSON files in `res/SAT/{n}.json` where `n` is the number of teams.

### SAT JSON Structure

```json
{
  "execution_name": {
    "time": 2.5,              // Average execution time in seconds
    "time_std": 0.1,          // Standard deviation of execution times
    "time_min": 2.4,          // Minimum execution time
    "time_max": 2.6,          // Maximum execution time
    "optimal": "true",        // Whether solution was found
    "obj": null,              // No optimization objective in SAT
    "sol": [                  // Tournament schedule found
      [                       // Week 1
        [1, 2],              // Period 1: Team 1 vs Team 2 (home, away)
        [3, 4],              // Period 2: Team 3 vs Team 4
        [5, 6]               // Period 3: Team 5 vs Team 6
      ],
      // ... more weeks
    ],    "solver": "z3",           // Solver used (always z3 for SAT)
    "constraints": [...],     // List of active constraints
    "encoding_type": "he",    // SAT encoding type used (np/seq/bw/he)
    "status": "sat",          // Solution status (sat/unsat/timeout/error)
    "runs": 5,                // Number of runs performed
    "sat_count": 5,           // Number of runs that found solutions
    "unsat_count": 0,         // Number of runs that proved unsatisfiable
    "timeout_count": 0,       // Number of runs that timed out
    "error_count": 0          // Number of runs that had errors
  }
}
```

### SAT Result Interpretation

- **`time`**: Average Z3 solver execution time across runs
- **`status`**: Overall result status:
  - `"sat"`: Solution found in at least one run
  - `"unsat"`: Proven unsatisfiable in all runs
  - `"timeout"`: All runs exceeded time limit
  - `"mixed"`: Some runs succeeded, others failed
  - `"error"`: Error occurred during solving
- **`sol`**: Tournament schedule as [week][period][home_team, away_team] (teams numbered 1-n)
- **`constraints`**: List of SAT constraints that were enabled
- **`encoding_type`**: SAT encoding strategy used (np, seq, bw, or he)
- **Run statistics**: Detailed counts of different outcome types across multiple runs

## SAT Encoding Performance Analysis

The choice of SAT encoding can significantly impact solving performance. Use the `--encoding` parameter to compare different approaches:

### Encoding Comparison Examples

```powershell
# Compare all encodings on the same problem
python run_STS.py 8 --generate --encoding np --runs 3  # Naive pairwise
python run_STS.py 8 --generate --encoding seq --runs 3 # Sequential
python run_STS.py 8 --generate --encoding bw --runs 3  # Bitwise (default)  
python run_STS.py 8 --generate --encoding he --runs 3  # Heule

# Test mode with different encodings
python run_STS.py 6 --test --constraints use_symm_break_weeks --encoding bw
python run_STS.py 6 --test --constraints use_symm_break_weeks --encoding he

# Systematic encoding analysis with constraint groups
python run_STS.py 8 --select symm --encoding seq --runs 5
python run_STS.py 8 --select symm --encoding he --runs 5
```

### Encoding Selection Guidelines

**For Small Instances (4-6 teams):**
- All encodings perform well
- Use default bitwise (`bw`) for consistency
- Naive pairwise (`np`) acceptable but may be slower

**For Medium Instances (8-10 teams):**
- **Bitwise (`bw`)**: Generally best performance (default)
- **Sequential (`seq`)**: Reliable alternative, good for analysis
- **Heule (`he`)**: Good for constraint decomposition
- **Avoid naive pairwise (`np`)**: Can become very slow

**For Large Instances (12+ teams):**
- **Bitwise (`bw`)**: Recommended for best performance
- **Heule (`he`)**: Good alternative, scales well
- **Sequential (`seq`)**: Fallback option if others fail
- **Avoid naive pairwise (`np`)**: Too slow for practical use

**For Performance Comparison Studies:**
- Use multiple encodings on same instance to compare
- Results include `encoding_type` field for analysis
- Consider encoding when interpreting timing results

## SAT vs CP Comparison

Both implementations solve the same problem but use different approaches:

| Aspect | CP (MiniZinc) | SAT (Z3) |
|--------|---------------|----------|
| **Solver Type** | Constraint Programming | Boolean Satisfiability |
| **Optimization** | Supports objective optimization | Pure satisfiability (find any solution) |
| **Solvers** | Chuffed, Gecode | Z3 SMT solver |
| **Encoding** | High-level constraints | Boolean variables and clauses with multiple encoding strategies |
| **Search Strategy** | Built-in CP search | SAT solver heuristics |
| **Solution Quality** | Can optimize for best solution | Finds any valid solution |
| **Performance** | Varies by problem size | Generally fast for smaller instances, depends on encoding choice |

### When to Use Each Approach

**Use CP (MiniZinc) when:**
- You need optimal solutions (minimizing home/away imbalance)
- Working with larger problem instances (12+ teams)
- You want to compare different solvers (Chuffed vs Gecode)
- You need advanced search strategies

**Use SAT (Z3) when:**
- Any valid solution is sufficient
- Working with smaller instances (4-10 teams)  
- You want to analyze Boolean constraint encoding effects
- You prefer direct Python integration without external tools
- You want to experiment with different SAT encoding strategies

### Running Comparative Analysis

You can compare both approaches on the same problem:

```powershell
# CP approach
python test/CP/run_CP.py -n 6 -g --chuffed --runs 5

# SAT approach with different encodings
python test/SAT/run_STS.py 6 --generate --encoding bw --runs 5  # Bitwise
python test/SAT/run_STS.py 6 --generate --encoding seq --runs 5 # Sequential
python test/SAT/run_STS.py 6 --generate --encoding he --runs 5  # Heule

# Compare results from res/CP/6.json and res/SAT/6.json
```

### Cross-Platform Encoding Analysis

For comprehensive performance analysis across different encodings:

```powershell
# Create batch script to test all encodings systematically
# Example: Test Heule encoding across multiple team sizes
python test/SAT/run_STS.py 2 --test --encoding he --runs 1
python test/SAT/run_STS.py 4 --test --encoding he --runs 1  
python test/SAT/run_STS.py 6 --test --encoding he --runs 1
python test/SAT/run_STS.py 8 --test --encoding he --runs 1
python test/SAT/run_STS.py 10 --test --encoding he --runs 1
```

## Troubleshooting

### Common Issues

1. **"MiniZinc not found"** (CP version)
   - Install MiniZinc from https://www.minizinc.org/
   - Ensure `minizinc` command is in your system PATH

2. **"No module named 'z3'"** (SAT version)
   - Install Z3 Python bindings: `pip install z3-solver`

3. **"FileNotFoundError: use_constraints.dzn" or similar** (CP version)
   - Run the script from the repository root directory
   - Ensure the file structure matches the expected layout
   - Check that both optimized and non-optimized files exist:
     - `source/CP/use_constraints.dzn` (for optimized model)
     - `source/CP/use_constraintsNoOpt.dzn` (for non-optimized model)  
     - `source/CP/sts.mzn` (optimized model)
     - `source/CP/stsNoOpt.mzn` (non-optimized model)

2. **"FileNotFoundError: use_constraints.dzn" or similar**
   - Run the script from the repository root directory
   - Ensure the file structure matches the expected layout
   - Check that both optimized and non-optimized files exist:
     - `source/CP/use_constraints.dzn` (for optimized model)
     - `source/CP/use_constraintsNoOpt.dzn` (for non-optimized model)  
     - `source/CP/sts.mzn` (optimized model)
     - `source/CP/stsNoOpt.mzn` (non-optimized model)

3. **"Invalid constraint names"**
   - Check available constraints in the appropriate file:
     - `source/CP/use_constraints.dzn` (optimized model)
     - `source/CP/use_constraintsNoOpt.dzn` (non-optimized model)  
   - Use exact constraint names as listed
   - Note: constraint names may differ between optimized and non-optimized versions
   - Current available constraints: `use_symm_break_weeks`, `use_symm_break_periods`, `use_symm_break_teams`, `use_implied_matches_per_team`, `use_implied_period_count`, `use_int_search`, `use_restart_luby`, `use_relax_and_reconstruct`

4. **Long execution times**
   - Reduce number of teams for testing
   - Use fewer constraints in test mode
   - Increase timeout with `--timeout <seconds>` for difficult instances
   - Default timeout is 300 seconds (5 minutes)
   - Consider using different solvers (`--gecode` vs `--chuffed`)
   - Reduce number of averaging runs with `--runs <number>` for faster results

5. **Inconsistent results across runs**
   - Increase number of averaging runs with `--runs <number>` (default: 5)
   - Check `time_stats` and `obj_stats` in results for measurement reliability
   - Use `--verbose` flag to see intermediate solutions and run details

6. **Poor performance with parallel execution**
   - Adjust `--max-workers` parameter based on your system capabilities
   - Use `--max-workers 1` for sequential execution if parallel execution causes issues
   - Monitor system resources when using high worker counts
   - Consider reducing `--runs` if parallel execution overwhelms system memory

### Getting Help

```bash
# Show all available options
python run_CP.py --help

# List available constraints (check error message when using invalid constraint)
python run_CP.py -n 4 -c invalid_constraint
```

## Model Details

The MiniZinc model (`source/CP/sts.mzn`) implements:

- **Variables**: `home[w,p]` and `away[w,p]` for week w, period p
- **Core Constraints**: Ensure valid tournament structure
- **Symmetry Breaking**: Reduce search space via lexicographic ordering
- **Objective**: Minimize maximum home/away imbalance across teams
- **Search Strategies**: Advanced search techniques including:
  - Integer search strategies (`use_int_search`)
  - Restart strategies with Luby sequences (`use_restart_luby`) 
  - Relax-and-reconstruct methods (`use_relax_and_reconstruct`)
- **Statistical Reliability**: Multiple runs with averaging for consistent measurements

For detailed constraint definitions, see the comments in `sts.mzn`.

Results saved to `res/CP/{args.teams}.json`
Total executions: {len(results)}
Each execution was averaged over {args.runs} runs for reliable measurements.
Parallel execution used {args.max_workers} workers for improved performance.
