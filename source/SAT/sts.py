from z3 import *
import sat_encodings

n = 6
use_symm_break_weeks = True
use_symm_break_periods = True
use_symm_break_teams = True
use_implied_matches_per_team = True
use_implied_period_count = True

weeks = n - 1
periods = n // 2
Teams = range(n)
Weeks = range(weeks)
Periods = range(periods)

# Boolean variables: home[w][p][t] == True iff team t is home in (w,p)
home = [[[Bool(f"home_{w}_{p}_{t}") for t in Teams] for p in Periods] for w in Weeks]
away = [[[Bool(f"away_{w}_{p}_{t}") for t in Teams] for p in Periods] for w in Weeks]

s = Solver()

exactly_one = sat_encodings.exactly_one_bw
at_most_k = sat_encodings.at_most_k_seq
exactly_k = sat_encodings.exactly_k_seq

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
if s.check() == sat:
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
    print(sol)
else:
    print("unsat")
