# Scores by difficulty

Easy: 5% corruption; medium: 10%; hard: 20%. All solvers use the same examples and time limit.

| Difficulty | Solver | Cases | Word accuracy | Exact sentences | Remaining character errors | Average model cost |
|---|---|---:|---:|---:|---:|---:|
| Easy | Spidy | 34 | 100.00% | 34/34 | 0 | 11.219 |
| Easy | Tanmay | 34 | 100.00% | 34/34 | 0 | 11.219 |
| Easy | Yours | 34 | 99.26% | 30/34 | 7 | 11.820 |
| Medium | Spidy | 33 | 98.86% | 27/33 | 21 | 15.082 |
| Medium | Tanmay | 33 | 96.96% | 23/33 | 37 | 19.542 |
| Medium | Yours | 33 | 96.77% | 16/33 | 36 | 14.656 |
| Hard | Spidy | 33 | 91.83% | 6/33 | 146 | 38.004 |
| Hard | Tanmay | 33 | 87.45% | 3/33 | 188 | 45.340 |
| Hard | Yours | 33 | 89.16% | 5/33 | 147 | 30.159 |

Higher accuracy is better; lower model cost is better. Compare model costs within each difficulty group.

Your solvers.py initially failed because removed parameters D and greedy_passes were still referenced. The run uses the minimal repair: initial depth 1, increasing each pass, and removal of obsolete parameter checks. The original failed run is preserved in solvers_failed_undefined_parameters. One logging-related timeout failure was retried successfully.
