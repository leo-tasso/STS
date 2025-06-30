import pulp
import time
from typing import Dict, List, Tuple, Any

def create_mip_model(n: int, constraints: dict[str, bool] = None, solver_name: str = "PULP_CBC_CMD", optimize: bool = False) -> Tuple[pulp.LpProblem, Dict[str, Any]]:
    """
    Creates a MIP model for the STS problem using PuLP.
    
    Args:
        n (int): Number of teams (must be even)
        constraints (dict): Dictionary of constraint flags
        solver_name (str): Name of the solver to use
        optimize (bool): Whether to optimize for home/away balance
    
    Returns:
        tuple: (model, variables_dict) where model is PuLP model and variables_dict contains all variables
    """
    # Default constraints
    if constraints is None:
        constraints = {
            'use_symm_break_weeks': True,
            'use_symm_break_periods': True, 
            'use_symm_break_teams': True,
            'use_implied_matches_per_team': True,
            'use_implied_period_count': True
        }
    
    # Extract constraint flags
    use_symm_break_weeks = constraints.get('use_symm_break_weeks', True)
    use_symm_break_periods = constraints.get('use_symm_break_periods', True)
    use_symm_break_teams = constraints.get('use_symm_break_teams', True)
    use_implied_matches_per_team = constraints.get('use_implied_matches_per_team', True)
    use_implied_period_count = constraints.get('use_implied_period_count', True)
    
    weeks = n - 1
    periods = n // 2
    Teams = list(range(1, n + 1))
    Weeks = list(range(1, weeks + 1))
    Periods = list(range(1, periods + 1))
    
    # Create the model
    model = pulp.LpProblem("STS_MIP", pulp.LpMinimize)
    
    # Decision variables: x[w][p][i][j] = 1 if team i plays at home against team j in week w, period p
    x = {}
    for w in Weeks:
        x[w] = {}
        for p in Periods:
            x[w][p] = {}
            for i in Teams:
                x[w][p][i] = {}
                for j in Teams:
                    if i != j:  # A team cannot play against itself
                        x[w][p][i][j] = pulp.LpVariable(f"x_{w}_{p}_{i}_{j}", cat='Binary')
                    else:
                        x[w][p][i][j] = None
    
    # Home/away count for fairness
    home_count = {t: pulp.LpVariable(f"home_count_{t}", lowBound=0, upBound=n-1, cat='Integer') for t in Teams}
    away_count = {t: pulp.LpVariable(f"away_count_{t}", lowBound=0, upBound=n-1, cat='Integer') for t in Teams}

    for t in Teams:
        home_games = []
        away_games = []
        for w in Weeks:
            for p in Periods:
                for opp in Teams:
                    if opp != t:
                        home_games.append(x[w][p][t][opp])
                        away_games.append(x[w][p][opp][t])
        model += home_count[t] == pulp.lpSum(home_games), f"Home_Count_Team_{t}"
        model += away_count[t] == pulp.lpSum(away_games), f"Away_Count_Team_{t}"

    # Implied matches per team constraint
    if use_implied_matches_per_team:
        for t in Teams:
            model += home_count[t] + away_count[t] == n - 1, f"Implied_Matches_Per_Team_{t}"

    # Objective: maximize home/away balance if optimize, else feasibility
    if optimize:
        max_diff = pulp.LpVariable("max_diff", lowBound=0, upBound=n-1, cat='Integer')
        for t in Teams:
            model += home_count[t] - away_count[t] <= max_diff, f"MaxDiff_Pos_{t}"
            model += away_count[t] - home_count[t] <= max_diff, f"MaxDiff_Neg_{t}"
        model += max_diff, "Minimize_Max_Home_Away_Diff"
    else:
        model += 0, "Feasibility_Problem"
    
    # Constraint 1: Each slot (week, period) has exactly one match
    for w in Weeks:
        for p in Periods:
            matches_in_slot = []
            for i in Teams:
                for j in Teams:
                    if i != j:
                        matches_in_slot.append(x[w][p][i][j])
            model += pulp.lpSum(matches_in_slot) == 1, f"One_Match_Per_Slot_W{w}_P{p}"
    
    # Constraint 2: If team i plays at home against team j, then team j cannot play at home against team i in the same slot
    for w in Weeks:
        for p in Periods:
            for i in Teams:
                for j in Teams:
                    if i < j:  # Only consider each pair once
                        model += x[w][p][i][j] + x[w][p][j][i] <= 1, f"Mutual_Exclusion_W{w}_P{p}_T{i}_T{j}"
    
    # Constraint 3: Each pair of teams plays exactly once (either i at home vs j, or j at home vs i)
    for i in Teams:
        for j in Teams:
            if i < j:  # Only consider each pair once
                pair_games = []
                for w in Weeks:
                    for p in Periods:
                        pair_games.append(x[w][p][i][j])  # i at home vs j
                        pair_games.append(x[w][p][j][i])  # j at home vs i
                model += pulp.lpSum(pair_games) == 1, f"Each_Pair_Plays_Once_T{i}_T{j}"
    
    # Constraint 4: Each team plays exactly once per week
    for w in Weeks:
        for t in Teams:
            games_per_week = []
            for p in Periods:
                for opponent in Teams:
                    if opponent != t:
                        games_per_week.append(x[w][p][t][opponent])  # t at home
                        games_per_week.append(x[w][p][opponent][t])  # t away
            model += pulp.lpSum(games_per_week) == 1, f"One_Game_Per_Week_W{w}_T{t}"
    
    # Constraint 5: Each team appears in each period at most twice across all weeks (optional strengthening)
    if use_implied_period_count:
        for t in Teams:
            for p in Periods:
                period_appearances = []
                for w in Weeks:
                    for opponent in Teams:
                        if opponent != t:
                            period_appearances.append(x[w][p][t][opponent])  # t at home
                            period_appearances.append(x[w][p][opponent][t])  # t away
                model += pulp.lpSum(period_appearances) <= 2, f"Period_Limit_T{t}_P{p}"
    
    # Symmetry breaking constraints
    if use_symm_break_weeks:
        # Team 1 plays its first match in week 1, period 1
        first_week_matches = []
        for opponent in Teams[1:]:  # All teams except team 1
            first_week_matches.append(x[1][1][1][opponent])
            first_week_matches.append(x[1][1][opponent][1])
        model += pulp.lpSum(first_week_matches) == 1, "Symm_Break_Week_Team1_W1_P1"
    
    if use_symm_break_periods:
        # Team 1 plays at home in period 1 of week 1
        home_matches_team1_w1_p1 = []
        for opponent in Teams[1:]:
            home_matches_team1_w1_p1.append(x[1][1][1][opponent])
        model += pulp.lpSum(home_matches_team1_w1_p1) == 1, "Symm_Break_Period_Team1_Home_W1_P1"
    
    if use_symm_break_teams:
        # Team 1 plays against team 2 in week 1
        model += x[1][1][1][2] + x[1][1][2][1] == 1, "Symm_Break_Teams_T1_vs_T2_W1"
    
    # Store variables for later use
    variables = {
        'x': x,
        'Teams': Teams,
        'Weeks': Weeks,
        'Periods': Periods,
        'weeks': weeks,
        'periods': periods
    }
    
    return model, variables

def solve_sts_mip(n: int, constraints: dict[str, bool] = None, solver_name: str = "PULP_CBC_CMD", 
                  timeout_sec: int = 300, verbose: bool = False, optimize: bool = False) -> dict:
    """
    Solves the STS problem using MIP formulation.
    
    Args:
        n (int): Number of teams
        constraints (dict): Dictionary of constraint flags
        solver_name (str): Solver to use ('PULP_CBC_CMD', 'GUROBI_CMD', 'CPLEX_CMD', etc.)
        timeout_sec (int): Timeout in seconds
        verbose (bool): Whether to print verbose output
        optimize (bool): Whether to optimize for home/away balance
        
    Returns:
        dict: Results dictionary with timing, solution status, and solution
    """
    if n % 2 != 0:
        raise ValueError("Number of teams must be even")
    
    if verbose:
        print(f"Solving STS problem with {n} teams using MIP")
        print(f"Solver: {solver_name}")
        print(f"Active constraints: {[k for k, v in constraints.items() if v] if constraints else 'All default'}")
    
    start_time = time.time()
    
    try:
        # Create the model
        model, variables = create_mip_model(n, constraints, solver_name, optimize=optimize)
        
        # Get solver
        if solver_name == "PULP_CBC_CMD":
            solver = pulp.PULP_CBC_CMD(timeLimit=timeout_sec, msg=verbose)
        elif solver_name == "GUROBI_CMD":
            solver = pulp.GUROBI_CMD(timeLimit=timeout_sec, msg=verbose)
        elif solver_name == "CPLEX_CMD":
            solver = pulp.CPLEX_CMD(timeLimit=timeout_sec, msg=verbose)
        elif solver_name == "GLPK_CMD":
            solver = pulp.GLPK_CMD(timeLimit=timeout_sec, msg=verbose)
        else:
            solver = pulp.getSolver(solver_name, timeLimit=timeout_sec, msg=verbose)
        
        # Solve the model
        model.solve(solver)
        
        end_time = time.time()
        solve_time = end_time - start_time
        
        # Check solution status
        status = pulp.LpStatus[model.status]
        
        if model.status == pulp.LpStatusOptimal:
            # Extract solution
            x = variables['x']
            Teams = variables['Teams']
            Weeks = variables['Weeks']
            Periods = variables['Periods']
            
            # Extract solution in correct format: [periods][weeks]
            # Structure should be: periods x weeks, where each element is [home, away]
            solution = []
            for p in Periods:
                period_schedule = []
                for w in Weeks:
                    match_found = False
                    for i in Teams:
                        for j in Teams:
                            if i != j and x[w][p][i][j].varValue == 1:
                                period_schedule.append([i, j])  # [home, away]
                                match_found = True
                                break
                        if match_found:
                            break
                    if not match_found:
                        period_schedule.append([0, 0])  # Placeholder if no match found
                solution.append(period_schedule)
            
            # Extract objective value if optimize
            obj_val = None
            if optimize:
                obj_val = pulp.value(model.objective)
            else:
                obj_val = 1  # Fixed value for feasibility

            return {
                "time": int(round(solve_time)),
                "optimal": "true",
                "obj": obj_val,
                "sol": solution,
                "solver": solver_name,
                "constraints": [k for k, v in constraints.items() if v] if constraints else []
            }
        
        elif model.status == pulp.LpStatusInfeasible:
            return {
                "time": int(round(solve_time)),
                "optimal": "false", 
                "obj": None,
                "sol": "unsat",
                "solver": solver_name,
                "constraints": [k for k, v in constraints.items() if v] if constraints else []
            }
        
        else:
            return {
                "time": int(round(solve_time)),
                "optimal": "false",
                "obj": None,
                "sol": "=====UNKNOWN===== (likely timeout)",
                "solver": solver_name,
                "constraints": [k for k, v in constraints.items() if v] if constraints else []
            }
            
    except Exception as e:
        end_time = time.time()
        solve_time = end_time - start_time
        
        return {
            "time": int(round(solve_time)),
            "optimal": "false",
            "obj": None,
            "sol": "ERROR PARSING STDOUT",
            "solver": solver_name,
            "constraints": [k for k, v in constraints.items() if v] if constraints else [],
            "error": str(e)
        }

def get_available_solvers() -> List[str]:
    """
    Returns a list of available MIP solvers on the system.
    
    Returns:
        List[str]: List of available solver names
    """
    available = []
    
    # Check common solvers
    solvers_to_check = [
        "PULP_CBC_CMD",
        "GUROBI_CMD", 
        "CPLEX_CMD",
        "GLPK_CMD",
        "SCIP_CMD"
    ]
    
    for solver_name in solvers_to_check:
        try:
            solver = pulp.getSolver(solver_name)
            if solver.available():
                available.append(solver_name)
        except:
            pass
    
    return available

if __name__ == "__main__":
    # Quick test
    print("Available MIP solvers:", get_available_solvers())
    
    # Test with small instance
    result = solve_sts_mip(12, verbose=False, optimize=False)
    print(f"Test result: {result} in {result['time']}ms")
