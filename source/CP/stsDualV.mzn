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

% Dual viewpoint control flags
bool: use_team_viewpoint;
bool: use_match_viewpoint;

bool: use_int_search;
bool: use_restart_luby;
bool: use_relax_and_reconstruct;

set of int: Teams = 1..n;
set of int: Weeks = 1..weeks;
set of int: Periods = 1..periods;

array[Weeks, Periods] of var Teams: home;
array[Weeks, Periods] of var Teams: away;

% Dual Viewpoints

% Team-based viewpoint: opponent[t,w] = opponent of team t in week w
array[Teams, Weeks] of var Teams: opponent;

% Match-based viewpoint: match[i,j,w] = 1 if teams i and j play in week w
array[Teams, Teams, Weeks] of var 0..1: match;

% Period assignment for each team in each week
array[Teams, Weeks] of var Periods: team_period;

% Main constraints

% Linking Constraints between viewpoints
constraint
  use_team_viewpoint ->
  forall(t in Teams, w in Weeks)(
    % Link team viewpoint with schedule viewpoint
    sum(p in Periods)(
      bool2int((home[w,p] = t /\ away[w,p] = opponent[t,w]) \/
               (away[w,p] = t /\ home[w,p] = opponent[t,w]))
    ) = 1 /\
    
    % Link team period assignment
    sum(p in Periods)(
      bool2int((home[w,p] = t \/ away[w,p] = t) /\ team_period[t,w] = p)
    ) = 1
  );

% Link match viewpoint with other viewpoints  
constraint
  (use_team_viewpoint /\ use_match_viewpoint) ->
  forall(i, j in Teams where i != j, w in Weeks)(
    match[i,j,w] = bool2int(opponent[i,w] = j)
  );

% Match viewpoint symmetry
constraint
  use_match_viewpoint ->
  forall(i, j in Teams where i != j, w in Weeks)(
    match[i,j,w] = match[j,i,w]
  );

% Team viewpoint constraints
constraint
  use_team_viewpoint ->
  forall(t in Teams, w in Weeks)(
    opponent[t,w] != t /\  % A team cannot play against itself
    opponent[opponent[t,w], w] = t  % Symmetry: if t plays j, then j plays t
  );

% Each pair plays exactly once (match viewpoint)
constraint
  use_match_viewpoint ->
  forall(i, j in Teams where i < j)(
    sum(w in Weeks)(match[i,j,w]) = 1
  );

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

% Additional dual viewpoint constraints

% Team-based period balancing
constraint
  use_team_viewpoint ->
  forall(t in Teams, p in Periods)(
    sum(w in Weeks)(bool2int(team_period[t,w] = p)) <= 2
  );

% Consistency between match and schedule viewpoints
constraint
  use_match_viewpoint ->
  forall(w in Weeks, p in Periods)(
    match[home[w,p], away[w,p], w] = 1
  );

% Symmetry breaking

%symmetry breaking weeks
constraint 
  use_symm_break_weeks ->
  forall(w in 1..weeks - 1)(
    lex_less(
      [ home[w,p] | p in Periods ] ++ [ away[w,p] | p in Periods ],
      [ home[w+1,p] | p in Periods ] ++ [ away[w+1,p] | p in Periods ]
    )
  );
%symmetry breaking periods
constraint 
  use_symm_break_periods ->
  forall(w in Weeks)(
    lex_lesseq(
      [ home[w,p] | p in 1..periods-1 ] ++ [ away[w,p] | p in 1..periods-1 ],
      [ home[w,p+1] | p in 1..periods-1 ] ++ [ away[w,p+1] | p in 1..periods-1 ]
    )
  );


% Enforce sorted home teams in week 1
constraint
  use_symm_break_teams ->
  forall(i in Periods) (
    home[1, i] = 2*i - 1 /\ 
    away[1, i] = 2*i
  );% for not optimized version could fix the whole first week

% Objective: balance home/away games
set of int: Count_diff = 1..n-1;
var Count_diff: max_diff = max([abs(home_count[t] - away_count[t]) | t in Teams]);
solve 
:: if use_int_search then
     int_search(
       [home[w, p] | w in Weeks, p in Periods] ++ [away[w, p] | w in Weeks, p in Periods] ++
       [opponent[t, w] | t in Teams, w in Weeks] ++ [team_period[t, w] | t in Teams, w in Weeks],
       first_fail,
       indomain_min,
       complete
     )
   endif
:: if use_restart_luby then restart_luby(10000) endif
:: if use_relax_and_reconstruct then 
     relax_and_reconstruct([home[w, p] | w in Weeks, p in Periods] ++ [away[w, p] | w in Weeks, p in Periods], 85)
   endif
   minimize max_diff;

% Output
output [
  "{",
  "\"obj\": ", show(max_diff), "," ,
  "\"sol\": ", show([ [ [home[w,p], away[w,p]] | p in Periods ] | w in Weeks ]),
  "}"
];

