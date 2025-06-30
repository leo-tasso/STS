from z3 import *
import time
import subprocess

def create_smt_solver(n: int, constraints: dict[str, bool] = None, optimize: bool = False) -> tuple[Solver, dict]:
    """
    Creates a Z3 SMT solver instance for the STS problem.
    
    Args:
        n (int): Number of teams (must be even)
        constraints (dict): Dictionary of constraint flags
        optimize (bool): Whether to solve optimization version
    
    Returns:
        tuple: (solver, variables_dict) where solver is Z3 solver and variables_dict contains all variables
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
    Teams = range(1, n + 1)  
    Weeks = range(1, weeks + 1)  
    Periods = range(1, periods + 1)  
    
    # Decision variables: home[w][p] and away[w][p]
    home = {}
    away = {}
    for w in Weeks:
        home[w] = {}
        away[w] = {}
        for p in Periods:
            home[w][p] = Int(f"home_{w}_{p}")
            away[w][p] = Int(f"away_{w}_{p}")
    
    # Optimization or satisfaction version
    if optimize:
        s = Optimize()
    else:
        s = Solver()
    
    # Domain constraints: teams are in valid range
    for w in Weeks:
        for p in Periods:
            s.add(And(home[w][p] >= 1, home[w][p] <= n))
            s.add(And(away[w][p] >= 1, away[w][p] <= n))
            # Home and away teams must be different
            s.add(home[w][p] != away[w][p])
    

    # Helper: pseudo-Boolean equality as sum of 0/1
    def pb_eq_bool_sum(bool_exprs, rhs):
        return Sum([If(b, 1, 0) for b in bool_exprs]) == rhs

    # Helper: pseudo-Boolean less-or-equal as sum of 0/1
    def pb_le_bool_sum(bool_exprs, rhs):
        return Sum([If(b, 1, 0) for b in bool_exprs]) <= rhs

    # Each slot has exactly one home and one away team
    for i in Teams:
        for j in Teams:
            if i < j:
                pair_games = []
                for w in Weeks:
                    for p in Periods:
                        # i plays at home against j
                        game1 = And(home[w][p] == i, away[w][p] == j)
                        pair_games.append(game1)
                        # j plays at home against i
                        game2 = And(home[w][p] == j, away[w][p] == i)
                        pair_games.append(game2)
                # Exactly one of these games occurs
                s.add(pb_eq_bool_sum(pair_games, 1))

    # Each team plays once per week
    for w in Weeks:
        for t in Teams:
            occ = []
            for p in Periods:
                occ.append(home[w][p] == t)
                occ.append(away[w][p] == t)
            s.add(pb_eq_bool_sum(occ, 1))

    # Period limit: Each team appears in same period at most twice
    for t in Teams:
        for p in Periods:
            occ = []
            for w in Weeks:
                occ.append(home[w][p] == t)
                occ.append(away[w][p] == t)
            s.add(pb_le_bool_sum(occ, 2))

    # All teams must be different in each week (no team plays twice in same week)
    for w in Weeks:
        all_teams_week = []
        for p in Periods:
            all_teams_week.extend([home[w][p], away[w][p]])
        s.add(Distinct(all_teams_week))
    
    # Implied constraint: number of games per team
    if use_implied_matches_per_team:
        for t in Teams:
            total_games = []
            for w in Weeks:
                for p in Periods:
                    total_games.append(home[w][p] == t)
                    total_games.append(away[w][p] == t) 
            s.add(pb_eq_bool_sum(total_games, n - 1))

    # Implied constraint: total period appearances
    if use_implied_period_count:
        for t in Teams:
            total_period_appearances = []
            for p in Periods:
                for w in Weeks:
                    total_period_appearances.append(home[w][p] == t)
                    total_period_appearances.append(away[w][p] == t)
            s.add(pb_eq_bool_sum(total_period_appearances, n - 1))
    
    # Helper function for lexicographic ordering
    def lex_less_int(curr, next):
        # curr, next: lists of Ints
        conditions = []
        for i in range(len(curr)):
            if i == 0:
                # At position 0: curr[0] < next[0]
                condition = curr[i] < next[i]
            else:
                # At position i: all previous positions equal, curr[i] < next[i]
                prefix_equal = And([curr[j] == next[j] for j in range(i)])
                condition = And(prefix_equal, curr[i] < next[i])
            conditions.append(condition)
        return Or(conditions)
    
    # Symmetry breaking: weeks
    if use_symm_break_weeks:
        for w in range(1, weeks):
            curr = [home[w][p] for p in Periods] + [away[w][p] for p in Periods]
            next = [home[w+1][p] for p in Periods] + [away[w+1][p] for p in Periods]
            s.add(lex_less_int(curr, next))

    # Symmetry breaking: periods
    if use_symm_break_periods:
        for p in range(1, periods):
            curr = [home[w][p] for w in Weeks] + [away[w][p] for w in Weeks]
            next = [home[w][p+1] for w in Weeks] + [away[w][p+1] for w in Weeks]
            s.add(lex_less_int(curr, next))

    # Symmetry breaking: teams (fix first week)
    if use_symm_break_teams:
        for p in Periods:
            s.add(home[1][p] == 2 * p - 1)  
            s.add(away[1][p] == 2 * p)     
    
    variables = {
        'home': home,
        'away': away,
        'weeks': weeks,
        'periods': periods,
        'Teams': Teams,
        'Weeks': Weeks,
        'Periods': Periods,
        'n': n
    }
    
    return s, variables

def solve_sts_smt(n: int, constraints: dict[str, bool] = None, optimize: bool = False, timeout: int = 300) -> dict[str, ]:
    """
    Solve the STS problem using SMT.
    
    Args:
        n (int): Number of teams (must be even)
        constraints (dict): Dictionary of constraint flags
        optimize (bool): Whether to solve optimization version (balance home/away games)
        timeout (int): Timeout in seconds
    
    Returns:
        dict: Solution dictionary with 'solution', 'time', 'satisfiable', and optionally 'objective' keys
    """
    if n % 2 != 0:
        raise ValueError("Number of teams must be even")
    
    s, vars_dict = create_smt_solver(n, constraints, optimize)
    
    home = vars_dict['home']
    away = vars_dict['away']
    Teams = vars_dict['Teams']
    Weeks = vars_dict['Weeks']
    Periods = vars_dict['Periods']
    
    s.set("timeout", timeout * 1000) 
    
    objective_value = None
    
    if optimize:
        home_count = {}
        away_count = {}
        
        for t in Teams:
            home_count[t] = Int(f"home_count_{t}")
            away_count[t] = Int(f"away_count_{t}")
            
            # Count home games for team t
            home_games = []
            away_games = []
            for w in Weeks:
                for p in Periods:
                    home_games.append(If(home[w][p] == t, 1, 0))
                    away_games.append(If(away[w][p] == t, 1, 0))
            
            s.add(home_count[t] == Sum(home_games))
            s.add(away_count[t] == Sum(away_games))
        
        # Minimize maximum difference
        max_diff = Int("max_diff")
        # Add range constraint: max_diff should be between 0 and n-1
        s.add(And(max_diff >= 0, max_diff <= n - 1))
        
        for t in Teams:
            diff = Abs(home_count[t] - away_count[t])
            s.add(max_diff >= diff)
        
        s.minimize(max_diff)
    
    # Solve
    start_time = time.time()
    result = s.check()
    solve_time = time.time() - start_time
    
    if result == sat:
        m = s.model()
        
        # Extract solution
        sol = []
        for p in Periods:
            period_games = []
            for w in Weeks:
                home_team = m.evaluate(home[w][p]).as_long()
                away_team = m.evaluate(away[w][p]).as_long()
                period_games.append([home_team, away_team])
            sol.append(period_games)
        
        result_dict = {
            'sol': sol,
            'time': solve_time,
            'satisfiable': True
        }
        
        if optimize:
            objective_value = m.evaluate(max_diff).as_long()
            result_dict['obj'] = objective_value
            result_dict['optimal'] = True
        else:
            result_dict['optimal'] = False

        return result_dict
    else:
        return {
            'sol': None,
            'time': solve_time,
            'optimal': False,
            'obj': None
        }
    
def solve_sts_smt_smtlib(n: int, constraints: dict[str, bool] = None, optimize: bool = False, timeout: int = 300) -> dict[str, ]:
    """
    Solve the STS problem using SMT-LIB2 export and cvc5 solver.
    Args:
        n (int): Number of teams (must be even)
        constraints (dict): Dictionary of constraint flags
        optimize (bool): Whether to solve optimization version (not supported for SMT-LIB2 export)
        timeout (int): Timeout in seconds
    Returns:
        dict: Solution dictionary with 'solution', 'time', and 'satisfiable' keys
    """
    if optimize:
        raise NotImplementedError("SMT-LIB2 export does not support optimization for SMT version.")

    s, vars_dict = create_smt_solver(n, constraints, optimize=False)
    Weeks = vars_dict['Weeks']
    Periods = vars_dict['Periods']

    # Export to SMT-LIB2 string and insert logic QF_LIA declaration
    start_time = time.time()
    smt2_string = s.to_smt2()
    smt2_lines = smt2_string.splitlines()
    smt2_lines[0] = "(set-logic QF_LIA)"
    smt2_lines.append("(get-model)")
    smt2_string = "\n".join(smt2_lines)

    # Write SMT-LIB2 to file
    smt2_path = "./sts_smt.smt2"
    with open(smt2_path, 'w') as f:
        f.write(smt2_string)
    
    cmd = ["./cvc5-Linux/bin/cvc5", "--lang", "smt2", "--produce-models", smt2_path]

    # Run cvc5 with timeout
    timeout_result = {
            'sol': None,
            'time': timeout,
            'optimal': False,
            'obj': None,
            'error': 'timeout'
        }
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return timeout_result
    
    solve_time = time.time() - start_time
    if solve_time > timeout:
        return timeout_result

    stdout = result.stdout.strip()

    if "unsat" in stdout:
        return {
            'sol': None,
            'time': solve_time,
            'optimal': False,
            'obj': None
        }
    if "sat" not in stdout:
        return {
            'sol': None,
            'time': solve_time,
            'optimal': False,
            'obj': None,
            'error': f"Unknown cvc5 output: {stdout}"
        }

    # Parse model from cvc5 output
    model = {}
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("(define-fun"):
            # Remove trailing ')'
            line = line[:-1] 
            parts = line.split()
            if len(parts) >= 5:
                var = parts[1]
                value = int(parts[-1])
                model[var] = value

    sol = []
    for p in Periods:
        period = []
        for w in Weeks:
            home_team = model.get(f"home_{w}_{p}", None)
            away_team = model.get(f"away_{w}_{p}", None)
            period.append([home_team, away_team])
        sol.append(period)

    return {
        'sol': sol,
        'time': solve_time,
        'satisfiable': True,
        'optimal': False,
        'obj': None
    }
    

def main():
    """
    Main function for standalone execution with default parameters.
    This preserves the original behavior when sts.py is run directly.
    """
    n = 6
    constraints = {
        'use_symm_break_weeks': False,
        'use_symm_break_periods': True,
        'use_symm_break_teams': True,
        'use_implied_matches_per_team': True,
        'use_implied_period_count': True
    }
    optimize = False  # Default to sat version
    solver = "z3"  
    if solver == "cvc5":
        result = solve_sts_smt(n, constraints, optimize=optimize)
    else:
        result = solve_sts_smt_smtlib(n, constraints, optimize=False)

    print(result)
    if result['sol']:
        print(result['sol'])
    else:
        print("unsat")

if __name__ == "__main__":
    main()