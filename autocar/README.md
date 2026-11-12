# A3 fresh starter

This is an independent working copy reconstructed from the existing unnumbered
starter files and simulator assets. The completed numbered solutions and old logs
are excluded. Your original A3 files are untouched.

## Where to code

- `estimator.py`: uses pruned inference only. `estimate(...)` returns
  `(current_belief, next_belief)`. The second grid predicts one transition step
  from the updated current belief, without another sensor reading. Parked cars
  have identical current and next distributions. `getBelief()` remains the
  current grid for simulator compatibility; `getNextBelief()` provides the
  forecast (`None` before the first observation), and `getBeliefs()` returns both.
  Earlier tracker methods remain in the file for reference but are not selected.
- `intelligentDriver.py`: plans candidate A* routes to checkpoints in order,
  compares predicted congestion, and checks for obstacles ahead.
  It currently receives current beliefs, not the estimator's new forecast output.
  Grid coordinates use (row, col); driving targets use pixel-space `Vec2d` values.
- `report.txt`: fill in your explanation and experiments.

Search for `BEGIN_YOUR_CODE` to find the two implementation areas.
The simulator imports these files, not the old numbered solutions.

## Run

Use Python 3 with Tkinter available. Check with `python3 -m tkinter`.
The original environment YAML files are included for reference; their old,
platform-specific package pins may need an appropriate Conda installation.

Run from this folder so layouts and transition data can be found:

```sh
cd /Users/aakritypandey/Documents/trying/ai_course/autocar
# Baseline simulator, no estimation
/opt/homebrew/bin/python3.13 drive.py -d -k 2 -l small -a -i none
# Part A (add -p for parked cars)
/opt/homebrew/bin/python3.13 drive.py -d -k 1 -l small -a -i estimator -t pruned_exact_inference
# Part B
/opt/homebrew/bin/python3.13 drive.py -d -k 2 -m -l small -a -i estimator -j
```

Replace `small` with `lombard` to use the other map. Press `q` to quit.
The estimator now uses pruned inference by default; `-t` can be omitted.

## Submission

The assignment requests `estimator.py`, `intelligentDriver.py`, and `report.txt`.
See the assignment PDF for report length and packaging requirements.

## Starter repairs

The copied engine imports were reset from `estimator4` and `intelligentDriver10`
to the starter modules. The planner's original tuple placeholder was replaced
with the current position vector and movement disabled, so the unfinished
planner satisfies the simulator's return-type expectations.
