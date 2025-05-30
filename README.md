# Sports Tournament Scheduling (STS) - Constraint Programming

This repository contains a MiniZinc-based constraint programming solution for sports tournament scheduling, along with a Python script for running experiments with different constraint configurations.

## Overview

The system generates balanced sports tournament schedules where:
- Each pair of teams plays exactly once
- Each team plays exactly once per week
- Teams appear in the same time period at most twice
- Home/away assignments are balanced

## Prerequisites

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
├── source/CP/
│   ├── sts.mzn                     # MiniZinc optimized constraint model
│   ├── stsNoOpt.mzn               # MiniZinc non-optimized constraint model
│   ├── use_constraints.dzn         # Available constraints definition (optimized)
│   └── use_constraintsNoOpt.dzn   # Available constraints definition (non-optimized)
├── test/CP/
│   └── run_CP.py                  # Python execution script
├── res/CP/                        # Results directory (auto-created)
│   └── {n}.json                  # Results for n teams
└── README.md                      # This file
```

## Available Constraints

The system supports the following constraint types:

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

## Usage

### Basic Command Structure

```bash
python run_CP.py -n <teams> [mode] [constraints] [options]
```

### Parameters

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

### Execution Modes

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
```

### Examples

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

## Output Format

Results are saved as JSON files in `res/CP/{n}.json` where `n` is the number of teams.

The script displays execution information during runtime:
```
Running Tournament Scheduling (Teams: 8, Version: Optimized, Solver: Chuffed)
Using all constraints
Timeout: 300 seconds
Runs per measurement: 5
Running MiniZinc model...
```

### JSON Structure

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
      "optimal_runs": 5
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

# Compare groups of constraints using select mode
python run_CP.py -n 8 -s symm       # All combinations of symmetry-breaking constraints
python run_CP.py -n 8 -s implied    # All combinations of implied constraints
python run_CP.py -n 8 -s search     # All combinations of search strategy constraints
python run_CP.py -n 8 -s            # All combinations for all groups
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
```

Key metrics to analyze:
- **Solving time**: Lower average time is better for practical use
- **Optimal solutions**: More constraints may help find optimal solutions faster
- **Solution quality**: Compare average objective values across different constraint sets
- **Solver performance**: Different solvers may excel on different problem instances
- **Optimization impact**: Compare optimized vs non-optimized model performance
- **Timeout sensitivity**: Analyze how different timeout values affect solution quality and completion rates
- **Statistical reliability**: Use time_stats and obj_stats to assess measurement reliability

## Reliability and Statistical Analysis

The system now includes robust statistical analysis to ensure reliable measurements:

### Multiple Run Averaging
- Each execution automatically runs multiple times (default: 5) and averages results
- Reduces noise from solver randomness and system variability
- Provides statistical measures including mean, median, min, max, and standard deviation

### Statistical Output
Results include detailed statistics for both timing and objective values:
- **Time Statistics**: Mean execution time with confidence measures
- **Objective Statistics**: Average solution quality with variance analysis  
- **Run Success Rates**: Track successful vs failed runs for reliability assessment

### Customizing Reliability
```bash
# High reliability (more runs, slower)
python run_CP.py -n 8 -g --runs 10

# Fast testing (single run, faster but less reliable)
python run_CP.py -n 8 -g --runs 1

# Default balanced approach
python run_CP.py -n 8 -g  # Uses 5 runs by default
```

### Interpreting Statistical Data
- **Low standard deviation**: Consistent, reliable measurements
- **High standard deviation**: Results vary significantly between runs
- **Success rate**: Percentage of runs that completed successfully
- **Optimal rate**: Percentage of runs that found optimal solutions

## Troubleshooting

### Common Issues

1. **"MiniZinc not found"**
   - Install MiniZinc from https://www.minizinc.org/
   - Ensure `minizinc` command is in your system PATH

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
