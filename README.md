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

- `use_constraint_symm_break_slots` - Break symmetry in match-ups
- `use_constraint_symm_break_weeks` - Break symmetry between weeks
- `use_constraint_symm_break_periods` - Break symmetry between periods
- `use_constraint_symm_break_teams` - Fix team ordering in first week
- `use_constraint_implied_matches_per_team` - Enforce exact match count per team
- `use_constraint_implied_period_count` - Enforce period appearance limits

## Usage

### Basic Command Structure

```bash
python run_CP.py -n <teams> [mode] [constraints] [options]
```

### Parameters

- **`-n, --teams`** (required): Number of teams (must be even)
- **`-g, --generate`** (optional): Generate mode - run once with selected constraints
- **`-t, --test`** (optional): Test mode - try all combinations of selected constraints
- **`-c, --constraints`** (optional): List of constraints to activate (default: all)
- **`--no-opt`** (optional): Use non-optimized model version (stsNoOpt.mzn instead of sts.mzn)
- **`--gecode`** (optional): Use Gecode solver instead of Chuffed (default)
- **`--timeout`** (optional): Solver timeout in seconds (default: 300)

### Execution Modes

#### 1. Default Mode
Runs the optimized model once with all available constraints enabled using Chuffed solver.

```bash
# Run with 6 teams using all constraints (optimized, Chuffed)
python run_CP.py -n 6

# Run with 6 teams using non-optimized model
python run_CP.py -n 6 --no-opt

# Run with 6 teams using Gecode solver
python run_CP.py -n 6 --gecode

# Run with 6 teams using non-optimized model and Gecode solver
python run_CP.py -n 6 --no-opt --gecode

# Run with 6 teams and custom timeout of 10 minutes
python run_CP.py -n 6 --timeout 600

# Run with 6 teams using non-optimized model, Gecode solver, and 2-minute timeout
python run_CP.py -n 6 --no-opt --gecode --timeout 120
```

#### 2. Generate Mode (`-g`)
Runs the model once with only the specified constraints enabled.

```bash
# Run with 8 teams using only symmetry breaking constraints (optimized, Chuffed)
python run_CP.py -n 8 -g -c use_constraint_symm_break_weeks use_constraint_symm_break_teams

# Run with 8 teams using non-optimized model and Gecode solver
python run_CP.py -n 8 -g -c use_constraint_symm_break_weeks use_constraint_symm_break_teams --no-opt --gecode

# Run with custom timeout of 10 minutes
python run_CP.py -n 8 -g -c use_constraint_symm_break_weeks use_constraint_symm_break_teams --timeout 600
```

#### 3. Test Mode (`-t`)
Systematically tests all possible combinations of the specified constraints.

```bash
# Test all combinations of 2 constraints with 6 teams (optimized, Chuffed)
python run_CP.py -n 6 -t -c use_constraint_symm_break_slots use_constraint_symm_break_weeks

# Test all combinations using non-optimized model with Gecode solver
python run_CP.py -n 6 -t -c use_constraint_symm_break_slots use_constraint_symm_break_weeks --no-opt --gecode
```

This will run 4 experiments:
- No constraints
- Only `use_constraint_symm_break_slots`
- Only `use_constraint_symm_break_weeks`
- Both constraints together

### Examples

```bash
# Quick test with minimal constraints (optimized, Chuffed)
python run_CP.py -n 4 -g -c use_constraint_symm_break_teams

# Same test using non-optimized model
python run_CP.py -n 4 -g -c use_constraint_symm_break_teams --no-opt

# Quick test using Gecode solver
python run_CP.py -n 4 -g -c use_constraint_symm_break_teams --gecode

# Comprehensive constraint analysis (optimized, Chuffed)
python run_CP.py -n 6 -t -c use_constraint_symm_break_weeks use_constraint_symm_break_periods use_constraint_implied_matches_per_team

# Same analysis using non-optimized model with Gecode
python run_CP.py -n 6 -t -c use_constraint_symm_break_weeks use_constraint_symm_break_periods use_constraint_implied_matches_per_team --no-opt --gecode

# Large tournament with all constraints (optimized, Chuffed)
python run_CP.py -n 12 -g

# Large tournament using non-optimized model with Gecode
python run_CP.py -n 12 -g --no-opt --gecode

# Run with extended timeout for difficult instances
python run_CP.py -n 14 -g --timeout 900  # 15 minutes

# Quick test with short timeout
python run_CP.py -n 8 -g --timeout 60  # 1 minute

# Compare solver performance for same configuration
python run_CP.py -n 8 -g  # Chuffed (default)
python run_CP.py -n 8 -g --gecode  # Gecode

# Compare model versions with same solver
python run_CP.py -n 8 -g  # Optimized (default)
python run_CP.py -n 8 -g --no-opt  # Non-optimized

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
Running MiniZinc model...
```

### JSON Structure

```json
{
  "execution_name": {
    "time": 67,             // Execution time in seconds
    "optimal": "true",      // Whether optimal solution was found
    "obj": 1,               // Objective value (max home/away imbalance)
    "sol": [                // Tournament schedule
      [                     // Week 1
        [1, 4],             // Period 1: Team 1 vs Team 4 (home, away)
        [2, 5],             // Period 2: Team 2 vs Team 5
        [3, 6]              // Period 3: Team 3 vs Team 6
      ],
      // ... more weeks
    ],
    "error": "..."          // Error message (if execution failed)
  }
}
```

### Interpreting Results

- **`time`**: Solver execution time (null if error occurred)
- **`optimal`**: "true" if optimal solution found within time limit (configurable, default 300s)
- **`obj`**: Maximum imbalance between home/away games across all teams (lower is better)
- **`sol`**: Tournament schedule as [week][period][home_team, away_team]
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

The system supports two MiniZinc solvers:

1. **Chuffed** (default)
   - Lazy clause generation solver
   - Generally effective for constraint satisfaction problems
   - Good balance of speed and solution quality

2. **Gecode** (`--gecode`)
   - Finite domain constraint solver
   - Alternative solving approach
   - May perform better on specific problem instances

### Comparative Analysis

Use different combinations to analyze performance:

```bash
# Compare solvers with optimized model
python run_CP.py -n 8 -g  # Chuffed + Optimized
python run_CP.py -n 8 -g --gecode  # Gecode + Optimized

# Compare model versions with Chuffed
python run_CP.py -n 8 -g  # Chuffed + Optimized  
python run_CP.py -n 8 -g --no-opt  # Chuffed + Non-optimized

# Compare all combinations
python run_CP.py -n 8 -g  # Chuffed + Optimized
python run_CP.py -n 8 -g --gecode  # Gecode + Optimized
python run_CP.py -n 8 -g --no-opt  # Chuffed + Non-optimized
python run_CP.py -n 8 -g --no-opt --gecode  # Gecode + Non-optimized
```

## Performance Analysis

Use test mode to compare constraint effectiveness across different configurations:

```bash
# Compare symmetry breaking strategies with different solvers
python run_CP.py -n 8 -t -c use_constraint_symm_break_weeks use_constraint_symm_break_periods use_constraint_symm_break_teams
python run_CP.py -n 8 -t -c use_constraint_symm_break_weeks use_constraint_symm_break_periods use_constraint_symm_break_teams --gecode

# Compare model optimization effectiveness
python run_CP.py -n 8 -t -c use_constraint_symm_break_weeks use_constraint_symm_break_periods  # Optimized
python run_CP.py -n 8 -t -c use_constraint_symm_break_weeks use_constraint_symm_break_periods --no-opt  # Non-optimized

# Test with different timeout values to analyze time sensitivity
python run_CP.py -n 12 -g --timeout 60   # Quick timeout
python run_CP.py -n 12 -g --timeout 600  # Extended timeout
```

Key metrics to analyze:
- **Solving time**: Lower is better for practical use
- **Optimal solutions**: More constraints may help find optimal solutions faster
- **Solution quality**: Compare objective values across different constraint sets
- **Solver performance**: Different solvers may excel on different problem instances
- **Optimization impact**: Compare optimized vs non-optimized model performance
- **Timeout sensitivity**: Analyze how different timeout values affect solution quality and completion rates

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

4. **Long execution times**
   - Reduce number of teams for testing
   - Use fewer constraints in test mode
   - Increase timeout with `--timeout <seconds>` for difficult instances
   - Default timeout is 300 seconds (5 minutes)
   - Consider using different solvers (`--gecode` vs default Chuffed)

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
- **Search Strategy**: First-fail variable ordering with minimum domain values

For detailed constraint definitions, see the comments in `sts.mzn`.
