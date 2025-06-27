% =========================
% SECTION: Instance & Sets
% =========================
include "globals.mzn";

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

int: num_matchups = (n * (n - 1)) div 2;

array[1..num_matchups, 1..2] of int: matchup_teams = 
  array2d(1..num_matchups, 1..2, 
    [if k = 1 then i else j endif | 
     i in Teams, j in Teams where i < j, k in 1..2]);

% Precompute whether a team appears in a matchup
array[1..num_matchups, Teams] of bool: team_in_matchup = 
  array2d(1..num_matchups, Teams, 
    [ (i = matchup_teams[m,1] \/ i = matchup_teams[m,2]) 
      | m in 1..num_matchups, i in Teams ]);

% =========================
% SECTION: Variables
% =========================
set of int: Slots = 1..(weeks * periods);
array[1..num_matchups] of var Slots: matchup_schedule;

function var int: get_week(var int: slot) = ((slot - 1) div periods) + 1;
function var int: get_period(var int: slot) = ((slot - 1) mod periods) + 1;

% =========================
% SECTION: Constraints
% =========================
constraint all_different(matchup_schedule);

constraint
  forall(w in Weeks)(
    let {
      array[1..num_matchups] of var 0..1: team_in_week = 
        [bool2int(get_week(matchup_schedule[m]) = w) | m in 1..num_matchups]
    } in
    forall(t in Teams)(
      sum(m in 1..num_matchups)(
        team_in_week[m] * bool2int(team_in_matchup[m, t])
      ) = 1
    )
  );

array[Teams, Periods] of var 0..2: period_count;

constraint
  forall(p in Periods)(
    let {
      array[1..num_matchups] of var 0..1: matchup_in_period = 
        [bool2int(get_period(matchup_schedule[m]) = p) | m in 1..num_matchups]
    } in
    forall(t in Teams)(
      period_count[t,p] = sum(m in 1..num_matchups)(
        matchup_in_period[m] * bool2int(team_in_matchup[m, t])
      )
    )
  );

array[1..num_matchups] of var bool: team1_home;

set of int: Count = 0..n-1;
array[Teams] of var Count: home_count;
array[Teams] of var Count: away_count;

array[1..num_matchups] of var Teams: home_teams;
array[1..num_matchups] of var Teams: away_teams;

constraint
  forall(m in 1..num_matchups)(
    if team1_home[m] then
      home_teams[m] = matchup_teams[m,1] /\ away_teams[m] = matchup_teams[m,2]
    else
      home_teams[m] = matchup_teams[m,2] /\ away_teams[m] = matchup_teams[m,1]
    endif
  );

constraint
  global_cardinality(home_teams, Teams, [home_count[t] | t in Teams]);

constraint
  global_cardinality(away_teams, Teams, [away_count[t] | t in Teams]);

constraint
  use_implied_matches_per_team ->
  forall(t in Teams)(
    home_count[t] + away_count[t] = n - 1
  );

constraint 
  use_implied_period_count ->
  forall(t in Teams)(
    sum(p in Periods) (period_count[t,p]) = n - 1
  );

% =========================
% SECTION: Objective
% =========================
set of int: Count_diff = 0..n-1;
var Count_diff: max_diff = max([abs(home_count[t] - away_count[t]) | t in Teams]);

solve 
:: if use_int_search then
    if chuffed then
      int_search(
        matchup_schedule ++ [bool2int(team1_home[m]) | m in 1..num_matchups],
        first_fail,
        indomain_min,
        complete
      )
    else
      int_search(
        matchup_schedule ++ [bool2int(team1_home[m]) | m in 1..num_matchups],
        first_fail,
        indomain_random,
        complete
      )
    endif
  endif
:: if use_restart_luby then restart_luby(10000) endif
:: if use_relax_and_reconstruct then 
     relax_and_reconstruct(matchup_schedule ++ [bool2int(team1_home[m]) | m in 1..num_matchups], 85)
   endif
   minimize max_diff;

% =========================
% SECTION: Output
% =========================
output [
  "{",
  "\"obj\": ", show(max_diff), "," ,
  "\"sol\": [",
  join(", ", [
    "[" ++ join(", ", [
      let {
        var 1..num_matchups: m = min([idx | idx in 1..num_matchups 
                                     where get_week(matchup_schedule[idx]) = w /\ 
                                           get_period(matchup_schedule[idx]) = p]),
        var Teams: home_team = if team1_home[m] then matchup_teams[m,1] else matchup_teams[m,2] endif,
        var Teams: away_team = if team1_home[m] then matchup_teams[m,2] else matchup_teams[m,1] endif
      } in
      "[" ++ show(home_team) ++ ", " ++ show(away_team) ++ "]"
    | w in Weeks]) ++ "]"
  | p in Periods]),
  "]",
  "}"
];
