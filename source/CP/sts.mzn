include "globals.mzn";

% Use this editor as a MiniZinc scratch book
int: n; % Number of teams (even)
int: weeks = n - 1;
int: periods = n div 2;

set of int: Teams = 1..n;
set of int: Weeks = 1..weeks;
set of int: Periods = 1..periods;

array[Weeks, Periods] of var Teams: home;
array[Weeks, Periods] of var Teams: away;

% Main constraints
%Only for not optimized
% constraint 
%  forall(w in Weeks, p in Periods)(
%    home[w, p] < away[w, p] % break symmetric match-ups
%  );

% Each pair plays once
constraint
  forall(i, j in Teams where i < j)(
    sum([bool2int((home[w, p] = i /\ away[w, p] = j) \/ (home[w, p] = j /\ away[w, p] = i)) |
         w in Weeks, p in Periods]) = 1
  );

% Each team plays once per week
constraint
  forall(t in Teams, w in Weeks)(
    sum([bool2int(home[w, p] = t \/ away[w, p] = t) | p in Periods]) = 1
  );

% Period limit: Each team appears in same period at most twice
array[Teams, Periods] of var int: period_count;

constraint
  forall(p in Periods)(
    global_cardinality(
      [home[w, p] | w in Weeks] ++ [away[w, p] | w in Weeks],
      Teams,
      [period_count[t, p] | t in Teams]
    )
  )
  /\
  forall(t in Teams, p in Periods)(
    period_count[t, p] <= 2
  );

% Home/away count for fairness
array[Teams] of var int: home_count;
array[Teams] of var int: away_count;

constraint
  forall(t in Teams)(
    home_count[t] = sum([bool2int(home[w, p] = t) | w in Weeks, p in Periods]) /\
    away_count[t] = sum([bool2int(away[w, p] = t) | w in Weeks, p in Periods])
  );

% Implied constraint: number of games per team
constraint
  forall(t in Teams)(
    home_count[t] + away_count[t] = n - 1
  );

% Implied constraint for total period appearances
constraint forall(t in Teams) (
  sum(p_val in Periods) (period_count[t,p_val]) = n-1
);

% Symmetry breaking

%symmetry breaking weeks
constraint forall(w in 1..weeks - 1)(
  lex_less(
    [ home[w,p] | p in Periods ] ++ [ away[w,p] | p in Periods ],
    [ home[w+1,p] | p in Periods ] ++ [ away[w+1,p] | p in Periods ]
  )
);
%symmetry breaking periods
constraint forall(w in Weeks)(
  lex_lesseq(
    [ home[w,p] | p in 1..periods-1 ] ++ [ away[w,p] | p in 1..periods-1 ],
    [ home[w,p+1] | p in 1..periods-1 ] ++ [ away[w,p+1] | p in 1..periods-1 ]
  )
);


% Enforce sorted home teams in week 1
constraint
  forall(i in Periods) (
    home[1, i] = 2*i - 1 /\ 
    away[1, i] = 2*i
  );% for not optimized version could fix the whole first week

% Objective: balance home/away games
var int: max_diff = max([abs(home_count[t] - away_count[t]) | t in Teams]);
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
  "Schedule:\n"
] ++ [
  "Week \(w): " ++
  concat([ "P\(p): \(show(home[w, p])) vs \(show(away[w, p]))  " | p in Periods ]) ++ "\n"
  | w in Weeks
] ++
["\nHome games: "] ++ [ "\(home_count[t]) " | t in Teams ] ++
["\nAway games: "] ++ [ "\(away_count[t]) " | t in Teams ] ++
["\nMax difference: \(max_diff)\n"]
;
