include "globals.mzn";

% Use this editor as a MiniZinc scratch book
int: n; % Number of teams (even)
int: weeks = n - 1;
int: periods = n div 2;

bool: use_constraint_symm_break_weeks;
bool: use_constraint_symm_break_periods;
bool: use_constraint_symm_break_teams;
bool: use_constraint_implied_matches_per_team;
bool: use_constraint_implied_period_count;

set of int: Teams = 1..n;
set of int: Weeks = 1..weeks;
set of int: Periods = 1..periods;

array[Weeks, Periods] of var Teams: home;
array[Weeks, Periods] of var Teams: away;

% Main constraints

% Each pair plays once
constraint
  forall(i, j in Teams where i < j)(
    sum([bool2int((home[w, p] = i /\ away[w, p] = j) \/ (home[w, p] = j /\ away[w, p] = i)) |
         w in Weeks, p in Periods]) = 1
  );

% Each team plays once per week
constraint
  forall(w in Weeks)(
    all_different([home[w, p] | p in Periods] ++ [away[w, p] | p in Periods])
  );

% Period limit: Each team appears in same period at most twice
array[Teams, Periods] of var 0..2: period_count;

constraint
  forall(p in Periods)(
    global_cardinality(
      [home[w, p] | w in Weeks] ++ [away[w, p] | w in Weeks],
      Teams,
      [period_count[t, p] | t in Teams]
    )
  );

% Home/away count for fairness
set of int: Count = 1..n-1;
array[Teams] of var Count: home_count;
array[Teams] of var Count: away_count;

constraint
  forall(t in Teams)(
    home_count[t] = sum([bool2int(home[w, p] = t) | w in Weeks, p in Periods]) /\
    away_count[t] = sum([bool2int(away[w, p] = t) | w in Weeks, p in Periods])
  );

% Implied constraint: number of games per team
constraint
  use_constraint_implied_matches_per_team ->
  forall(t in Teams)(
    home_count[t] + away_count[t] = n - 1
  );

% Implied constraint for total period appearances
constraint 
  use_constraint_implied_period_count ->
  forall(t in Teams) (
    sum(p_val in Periods) (period_count[t,p_val]) = n-1
  );

% Symmetry breaking

%symmetry breaking weeks
constraint 
  use_constraint_symm_break_weeks ->
  forall(w in 1..weeks - 1)(
    lex_less(
      [ home[w,p] | p in Periods ] ++ [ away[w,p] | p in Periods ],
      [ home[w+1,p] | p in Periods ] ++ [ away[w+1,p] | p in Periods ]
    )
  );
%symmetry breaking periods
constraint 
  use_constraint_symm_break_periods ->
  forall(w in Weeks)(
    lex_lesseq(
      [ home[w,p] | p in 1..periods-1 ] ++ [ away[w,p] | p in 1..periods-1 ],
      [ home[w,p+1] | p in 1..periods-1 ] ++ [ away[w,p+1] | p in 1..periods-1 ]
    )
  );


% Enforce sorted home teams in week 1
constraint
  use_constraint_symm_break_teams ->
  forall(i in Periods) (
    home[1, i] = 2*i - 1 /\ 
    away[1, i] = 2*i
  );% for not optimized version could fix the whole first week

% Objective: balance home/away games
set of int: Count_diff = 1..n-1;
var Count_diff: max_diff = max([abs(home_count[t] - away_count[t]) | t in Teams]);
solve 
:: int_search(
         [home[w, p] | w in Weeks, p in Periods] ++ [away[w, p] | w in Weeks, p in Periods],
         first_fail,
         indomain_min,
         complete
       )
%         :: restart_luby(10000)
%        :: relax_and_reconstruct([home[w, p] | w in Weeks, p in Periods] ++ [away[w, p] | w in Weeks, p in Periods], 85)
       minimize max_diff;

% Output
output [
  "{",
  "\"obj\": ", show(max_diff), "," ,
  "\"sol\": ", show([ [ [home[w,p], away[w,p]] | p in Periods ] | w in Weeks ]),
  "}"
];

