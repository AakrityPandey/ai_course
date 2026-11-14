# Driver test boards

Fourteen scenarios cover the small and Lombard road networks. Each family has:

| Suffix | Checkpoints | Purpose |
| --- | ---: | --- |
| `local` | 3 | Short routes and nearby turns |
| `tour` | 6 | Long trips across the map |
| `mixed` | 5 | Different checkpoint orders and route choices |
| `mirror_x` | 4 | Horizontally reflected roads and traffic |
| `mirror_y` | 5 | Vertically reflected roads and traffic |
| `rotated` | 6 | Map and traffic rotated 180 degrees |
| `congested` | 6 | Checkpoints on traffic cells; three moving cars by default |

The transition tables, traffic graph positions/directions, intersections, and
obstacles are transformed together. Checkpoints are distinct and reachable in
order using the driver's padded grid. These static checks do not guarantee that
the moving car can negotiate every turn or avoid traffic.

Run from `autocar`:

```sh
/opt/homebrew/bin/python3.13 run_test_board.py --list
/opt/homebrew/bin/python3.13 run_test_board.py small_local
/opt/homebrew/bin/python3.13 run_test_board.py lombard_tour --cars 2 --seed 1
/opt/homebrew/bin/python3.13 run_test_board.py small_mirror_x --parked --seed 2
/opt/homebrew/bin/python3.13 run_test_board.py small_congested
/opt/homebrew/bin/python3.13 run_test_board.py lombard_congested --seed 2
```

Use `run_test_board.py` for these boards: the original `drive.py` hard-codes
checkpoint counts for the original map names. The new launcher sets the correct
count and uses pruned inference automatically. No simulator or driver files are
changed by the launcher.

For a useful comparison, try each board with one moving car, then two cars, then
parked cars. Repeat with seeds 1, 2, and 3. Record checkpoints reached, collisions,
and long periods without progress. A successful run with one seed alone does not
establish that the driver handles all traffic patterns.

`test_boards.json` records exact checkpoint coordinates and minimum grid distances
for each leg. `make_test_boards.py` rebuilds these generated assets deterministically.
