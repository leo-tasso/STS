# Sports Tournament Scheduling (STS) - Multi-Paradigm Optimization

A comprehensive platform for solving sports tournament scheduling using four different optimization approaches: **Constraint Programming (CP)**, **Mixed Integer Programming (MIP)**, **Boolean Satisfiability (SAT)**, and **Satisfiability Modulo Theories (SMT)**.

## Quick Start

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install MiniZinc** (for CP): Download from https://www.minizinc.org/

3. **Run Examples:**
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

## Solution Approaches

| Paradigm | Best For | Optimization | Solver |
|----------|----------|--------------|---------|
| **CP** | Medium-large instances (8-16 teams) | Minimize home/away imbalance | MiniZinc (Chuffed/Gecode) |
| **MIP** | Small-medium instances (4-12 teams) | Proven optimal solutions | PuLP (CBC/Gurobi/CPLEX) |
| **SAT** | Small instances (4-10 teams) | Any valid solution | Z3 with multiple encodings |
| **SMT** | Small-medium instances (4-12 teams) | Any valid solution | Z3 |

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

## Features

- **Multi-run averaging** for statistical reliability
- **Parallel execution** for performance
- **Docker environment** with all dependencies
- **Cross-paradigm comparison** tools
- **Experimental section** for advanced features

---


