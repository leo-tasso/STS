include "globals.mzn";

% Use this editor as a MiniZinc scratch book
int: n; % Number of teams (even)
int: weeks = n - 1;
int: periods = n div 2;

bool: use_symm_break_weeks;
bool: use_symm_break_periods;
bool: use_symm_break_teams;
bool: use_implied_matches_per_team;
bool: use_implied_period_count;

bool: use_int_search;
bool: use_restart_luby;
bool: use_relax_and_reconstruct;

bool: chuffed;

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
set of int: Count = 0..n-1;
array[Teams] of var Count: home_count;
array[Teams] of var Count: away_count;

constraint
  global_cardinality(
    [home[w,p] | w in Weeks, p in Periods],
    Teams,
    [home_count[t] | t in Teams]
  );

constraint
  global_cardinality(
    [away[w,p] | w in Weeks, p in Periods], 
    Teams,
    [away_count[t] | t in Teams]
  );

% Implied constraint: number of games per team
constraint
  use_implied_matches_per_team ->
  forall(t in Teams)(
    home_count[t] + away_count[t] = n - 1
  );

% Implied constraint for total period appearances
constraint 
  use_implied_period_count ->
  forall(t in Teams) (
    sum(p_val in Periods) (period_count[t,p_val]) = n-1
  );

% Symmetry breaking

%symmetry breaking weeks
constraint 
  use_symm_break_weeks ->
  forall(w in 1..weeks-1)(
    lex_less(
      [ home[w,p] | p in Periods ] ++ [ away[w,p] | p in Periods ],
      [ home[w+1,p] | p in Periods ] ++ [ away[w+1,p] | p in Periods ]
    )
  );
%symmetry breaking periods
constraint 
  use_symm_break_periods ->
  forall(p in 1..periods-1)(
    lex_less(
      [ home[w,p] | w in Weeks ] ++ [ away[w,p] | w in Weeks ],
      [ home[w,p+1] | w in Weeks ] ++ [ away[w,p+1] | w in Weeks ]
    )
  );


% Enforce sorted home teams in week 1
constraint
  use_symm_break_teams ->
  forall(i in Periods) (
    home[1, i] = 2*i - 1 /\ 
    away[1, i] = 2*i
  );% for not optimized version could fix the whole first week



% Objective: just find a solution
solve 
:: if use_int_search then
    if chuffed then
     int_search(
       [home[w, p] | w in Weeks, p in Periods] ++ [away[w, p] | w in Weeks, p in Periods],
       first_fail,
       indomain_min,
       complete
     )
     else
      int_search(
       [home[w, p] | w in Weeks, p in Periods] ++ [away[w, p] | w in Weeks, p in Periods],
       first_fail,
       indomain_random,
       complete
     )
     endif
   endif
:: if (use_restart_luby /\ chuffed) then restart_luby(10000) endif
:: if use_relax_and_reconstruct then 
     relax_and_reconstruct([home[w, p] | w in Weeks, p in Periods] ++ [away[w, p] | w in Weeks, p in Periods], 85)
   endif
satisfy;

% Output
output [
  "{",
  "\"sol\": ", show([ [ [home[w,p], away[w,p]] | w in Weeks ] | p in Periods ]),
  "}"
];

