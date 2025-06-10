from z3 import *
import sat_encodings
import time


def solve_sts(n, constraints=None, encoding_type="bw"):
    """
    Solve the Social Tennis Schedule (STS) problem using SAT encoding.
    
    Args:
        n (int): Number of teams (must be even)
        constraints (dict): Dictionary of constraint flags, with keys:
            - use_symm_break_weeks (bool): Apply week symmetry breaking
            - use_symm_break_periods (bool): Apply period symmetry breaking  
            - use_symm_break_teams (bool): Apply team symmetry breaking
            - use_implied_matches_per_team (bool): Add implied constraint for matches per team
            - use_implied_period_count (bool): Add implied constraint for period appearances
        encoding_type (str): Type of SAT encoding to use ('np', 'seq', 'bw', 'he')
    
    Returns:
        dict: Solution dictionary with 'solution', 'time', and 'satisfiable' keys
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

    # Validate encoding type
    valid_encodings = ['np', 'seq', 'bw', 'he']
    if encoding_type not in valid_encodings:
        raise ValueError(f"Invalid encoding type '{encoding_type}'. Must be one of: {valid_encodings}")

    # Select encoding functions based on type
    if encoding_type == 'np':
        exactly_one = sat_encodings.exactly_one_np
        at_most_k = sat_encodings.at_most_k_np
        exactly_k = sat_encodings.exactly_k_np
    elif encoding_type == 'seq':
        exactly_one = sat_encodings.exactly_one_seq
        at_most_k = sat_encodings.at_most_k_seq
        exactly_k = sat_encodings.exactly_k_seq
    elif encoding_type == 'bw':
        exactly_one = sat_encodings.exactly_one_bw
        # Note: bitwise encoding doesn't have at_most_k/exactly_k, use sequential as fallback
        at_most_k = sat_encodings.at_most_k_seq
        exactly_k = sat_encodings.exactly_k_seq
    elif encoding_type == 'he':
        exactly_one = sat_encodings.exactly_one_he
        # Note: heule encoding doesn't have at_most_k/exactly_k, use sequential as fallback
        at_most_k = sat_encodings.at_most_k_seq
        exactly_k = sat_encodings.exactly_k_seq

    weeks = n - 1
    periods = n // 2
    Teams = range(n)
    Weeks = range(weeks)
    Periods = range(periods)    # Boolean variables: home[w][p][t] == True iff team t is home in (w,p)
    home = [[[Bool(f"home_{w}_{p}_{t}") for t in Teams] for p in Periods] for w in Weeks]
    away = [[[Bool(f"away_{w}_{p}_{t}") for t in Teams] for p in Periods] for w in Weeks]

    s = Solver()

    # Note: encoding functions are selected based on encoding_type parameter

    # Each slot has exactly one home and one away team, and they are different
    for w in Weeks:
        for p in Periods:
            s.add(exactly_one([home[w][p][t] for t in Teams], name=f"home_{w}_{p}"))
            s.add(exactly_one([away[w][p][t] for t in Teams], name=f"away_{w}_{p}"))
            for t in Teams:
                s.add(Implies(home[w][p][t], Not(away[w][p][t])))
                s.add(Implies(away[w][p][t], Not(home[w][p][t])))

    # Each pair plays once
    for i in Teams:
        for j in Teams:
            if i < j:
                pair_games = []
                for w in Weeks:
                    for p in Periods:
                        pair_games.append(And(home[w][p][i], away[w][p][j]))
                        pair_games.append(And(home[w][p][j], away[w][p][i]))
                s.add(exactly_one(pair_games, name=f"pair_{i}_{j}"))

    # Each team plays once per week
    for w in Weeks:
        for t in Teams:
            occ = []
            for p in Periods:
                occ.append(home[w][p][t])
                occ.append(away[w][p][t])
            s.add(exactly_one(occ, name=f"team_{t}_week_{w}"))

    # Period limit: Each team appears in same period at most twice
    for t in Teams:
        for p in Periods:
            occ = []
            for w in Weeks:
                occ.append(home[w][p][t])
                occ.append(away[w][p][t])
            s.add(at_most_k(occ, 2, name=f"team_{t}_period_{p}"))

    # Implied constraint: number of games per team
    if use_implied_matches_per_team:
        for t in Teams:
            occ = []
            for w in Weeks:
                for p in Periods:
                    occ.append(home[w][p][t])
                    occ.append(away[w][p][t])
            s.add(exactly_k(occ, weeks, name=f"team_{t}_matches"))

    # Implied constraint for total period appearances
    if use_implied_period_count:
        for t in Teams:
            occ = []
            for p in Periods:
                for w in Weeks:
                    occ.append(home[w][p][t])
                    occ.append(away[w][p][t])
            s.add(exactly_k(occ, n - 1, name=f"team_{t}_period_total"))

    # Symmetry breaking: weeks (lex order on home+away vectors)
    def lex_less_bool(curr, next):
        # curr, next: lists of Bools
        conditions = []
        for i in range(len(curr)):
            if i == 0:
                # At position 0: curr[0] = True and next[0] = False
                condition = And(curr[i], Not(next[i]))
            else:
                # At position i: all previous positions equal, curr[i] = True, next[i] = False
                prefix_equal = [curr[j] == next[j] for j in range(i)]
                condition = And(prefix_equal + [curr[i], Not(next[i])])
            conditions.append(condition)
        return Or(conditions)

    if use_symm_break_weeks:
        for w in range(weeks - 1):
            curr = [home[w][p][t] for p in Periods for t in Teams] + [
                away[w][p][t] for p in Periods for t in Teams
            ]
            nxt = [home[w + 1][p][t] for p in Periods for t in Teams] + [
                away[w + 1][p][t] for p in Periods for t in Teams
            ]
            s.add(lex_less_bool(curr, nxt))

    if use_symm_break_periods:
        for p in range(periods-1):
            curr = [home[w][p][t] for w in Weeks for t in Teams] + [away[w][p][t] for w in Weeks for t in Teams]
            nxt = [home[w][p+1][t] for w in Weeks for t in Teams] + [away[w][p+1][t] for w in Weeks for t in Teams]
            s.add(lex_less_bool(curr, nxt))

    # Symmetry breaking: teams (fix first week)
    if use_symm_break_teams:
        for i in Periods:
            for t in Teams:
                s.add(home[0][i][t] if t == 2 * i else Not(home[0][i][t]))
                s.add(away[0][i][t] if t == 2 * i + 1 else Not(away[0][i][t]))

    # Solve
    start_time = time.time()
    result = s.check()
    solve_time = time.time() - start_time
    
    if result == sat:
        m = s.model()
        sol = []
        for p in Periods:
            period = []
            for w in Weeks:
                home_team = None
                for t in Teams:
                    if m.evaluate(home[w][p][t], model_completion=True):
                        home_team = t + 1
                        break

                away_team = None
                for t in Teams:
                    if m.evaluate(away[w][p][t], model_completion=True):
                        away_team = t + 1
                        break

                period.append([home_team, away_team])
            sol.append(period)
        
        return {
            'solution': sol,
            'time': solve_time,
            'satisfiable': True
        }
    else:
        return {
            'solution': None,
            'time': solve_time,
            'satisfiable': False
        }


def main():
    """
    Main function for standalone execution with default parameters.
    This preserves the original behavior when sts.py is run directly.
    """
    n = 6
    constraints = {
        'use_symm_break_weeks': True,
        'use_symm_break_periods': True,
        'use_symm_break_teams': True,
        'use_implied_matches_per_team': True,
        'use_implied_period_count': True
    }
    encoding_type = "bw"  # Default to bitwise encoding
    
    result = solve_sts(n, constraints, encoding_type)
    
    if result['satisfiable']:
        print(result['solution'])
    else:
        print("unsat")


if __name__ == "__main__":
    main()
