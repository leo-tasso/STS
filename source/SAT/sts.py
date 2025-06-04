from z3 import *

# Parameters (set these as needed)
n = 12  # Number of teams (even)
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


def at_least_one(bool_vars):
    return Or(bool_vars)


def at_most_one(bool_vars):
    return And(
        [
            Not(And(bool_vars[i], bool_vars[j]))
            for i in range(len(bool_vars))
            for j in range(i + 1, len(bool_vars))
        ]
    )


def exactly_one(bool_vars):
    return And(at_least_one(bool_vars), at_most_one(bool_vars))


# Each slot has exactly one home and one away team, and they are different
for w in Weeks:
    for p in Periods:
        s.add(exactly_one([home[w][p][t] for t in Teams]))
        s.add(exactly_one([away[w][p][t] for t in Teams]))
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
            s.add(exactly_one(pair_games))

# Each team plays once per week
for w in Weeks:
    for t in Teams:
        occ = []
        for p in Periods:
            occ.append(home[w][p][t])
            occ.append(away[w][p][t])
        s.add(exactly_one(occ))

# Period limit: Each team appears in same period at most twice
for t in Teams:
    for p in Periods:
        occ = []
        for w in Weeks:
            occ.append(home[w][p][t])
            occ.append(away[w][p][t])
        s.add(PbLe([(x, 1) for x in occ], 2))

# Implied constraint: number of games per team
if use_implied_matches_per_team:
    for t in Teams:
        occ = []
        for w in Weeks:
            for p in Periods:
                occ.append(home[w][p][t])
                occ.append(away[w][p][t])
        s.add(PbEq([(x, 1) for x in occ], n - 1))


# TODO check with cp
# Implied constraint for total period appearances
if use_implied_period_count:
    for t in Teams:
        occ = []
        for p in Periods:
            for w in Weeks:
                occ.append(home[w][p][t])
                occ.append(away[w][p][t])
        s.add(PbEq([(x, 1) for x in occ], n - 1))


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
    for w in Weeks:
        curr = [home[w][p][t] for p in range(periods-1) for t in Teams] + [away[w][p][t] for p in range(periods-1) for t in Teams]
        nxt = [home[w][p+1][t] for p in range(periods-1) for t in Teams] + [away[w][p+1][t] for p in range(periods-1) for t in Teams]
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
    for w in Weeks:
        week = []
        for p in Periods:
            h = [
                t + 1 for t in Teams if m.evaluate(home[w][p][t], model_completion=True)
            ]
            a = [
                t + 1 for t in Teams if m.evaluate(away[w][p][t], model_completion=True)
            ]
            week.append([h[0], a[0]])
        sol.append(week)
    print("{")
    print(f'"sol": {sol}')
    print("}")
else:
    print("No solution found.")
