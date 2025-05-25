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
- `source/CP/sts.mzn` - MiniZinc model file
- `source/CP/use_constraints.dzn` - Constraint configuration file
- `test/CP/run_CP.py` - Python control script

## File Structure

```
STS/
├── source/CP/
│   ├── sts.mzn                 # MiniZinc constraint model
│   └── use_constraints.dzn     # Available constraints definition
├── test/CP/
│   └── run_CP.py              # Python execution script
├── res/CP/                    # Results directory (auto-created)
│   └── {n}.json              # Results for n teams
└── README.md                  # This file
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
python test/CP/run_CP.py -n <teams> [mode] [constraints]
```

### Parameters

- **`-n, --teams`** (required): Number of teams (must be even)
- **`-g, --generate`** (optional): Generate mode - run once with selected constraints
- **`-t, --test`** (optional): Test mode - try all combinations of selected constraints
- **`-c, --constraints`** (optional): List of constraints to activate (default: all)

### Execution Modes

#### 1. Default Mode
Runs the model once with all available constraints enabled.

```bash
# Run with 6 teams using all constraints
python test/CP/run_CP.py -n 6
```

#### 2. Generate Mode (`-g`)
Runs the model once with only the specified constraints enabled.

```bash
# Run with 8 teams using only symmetry breaking constraints
python test/CP/run_CP.py -n 8 -g -c use_constraint_symm_break_weeks use_constraint_symm_break_teams
```

#### 3. Test Mode (`-t`)
Systematically tests all possible combinations of the specified constraints.

```bash
# Test all combinations of 2 constraints with 6 teams
python test/CP/run_CP.py -n 6 -t -c use_constraint_symm_break_slots use_constraint_symm_break_weeks
```

This will run 4 experiments:
- No constraints
- Only `use_constraint_symm_break_slots`
- Only `use_constraint_symm_break_weeks`
- Both constraints together

### Examples

```bash
# Quick test with minimal constraints
python test/CP/run_CP.py -n 4 -g -c use_constraint_symm_break_teams

# Comprehensive constraint analysis
python test/CP/run_CP.py -n 6 -t -c use_constraint_symm_break_weeks use_constraint_symm_break_periods use_constraint_implied_matches_per_team

# Large tournament with all constraints
python test/CP/run_CP.py -n 12 -g

# Help and available options
python test/CP/run_CP.py --help
```

## Output Format

Results are saved as JSON files in `res/CP/{n}.json` where `n` is the number of teams.

### JSON Structure

```json
{
  "execution_name": {
    "time": 67.67,           // Execution time in seconds
    "optimal": "true",       // Whether optimal solution was found
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
- **`optimal`**: "true" if optimal solution found within time limit (300s)
- **`obj`**: Maximum imbalance between home/away games across all teams (lower is better)
- **`sol`**: Tournament schedule as [week][period][home_team, away_team]
- **`error`**: Present only if execution failed

## Performance Analysis

Use test mode to compare constraint effectiveness:

```bash
# Compare symmetry breaking strategies
python test/CP/run_CP.py -n 8 -t -c use_constraint_symm_break_weeks use_constraint_symm_break_periods use_constraint_symm_break_teams
```

Key metrics to analyze:
- **Solving time**: Lower is better for practical use
- **Optimal solutions**: More constraints may help find optimal solutions faster
- **Solution quality**: Compare objective values across different constraint sets

## Troubleshooting

### Common Issues

1. **"MiniZinc not found"**
   - Install MiniZinc from https://www.minizinc.org/
   - Ensure `minizinc` command is in your system PATH

2. **"FileNotFoundError: use_constraints.dzn"**
   - Run the script from the repository root directory
   - Ensure the file structure matches the expected layout

3. **"Invalid constraint names"**
   - Check available constraints in `source/CP/use_constraints.dzn`
   - Use exact constraint names as listed

4. **Long execution times**
   - Reduce number of teams for testing
   - Use fewer constraints in test mode
   - Default timeout is 300 seconds (5 minutes)

### Getting Help

```bash
# Show all available options
python test/CP/run_CP.py --help

# List available constraints (check error message when using invalid constraint)
python test/CP/run_CP.py -n 4 -c invalid_constraint
```

## Model Details

The MiniZinc model (`source/CP/sts.mzn`) implements:

- **Variables**: `home[w,p]` and `away[w,p]` for week w, period p
- **Core Constraints**: Ensure valid tournament structure
- **Symmetry Breaking**: Reduce search space via lexicographic ordering
- **Objective**: Minimize maximum home/away imbalance across teams
- **Search Strategy**: First-fail variable ordering with minimum domain values

For detailed constraint definitions, see the comments in `sts.mzn`.
