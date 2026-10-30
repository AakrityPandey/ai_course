# Connect Four timeout diagnostics

`ConnectFour_debug.py` is a separate diagnostic copy of the simulator. It imports
your current `connect4/players/ai.py`; the original assignment files are unchanged.

From `connectfour/starter_code`, run:

```sh
PYTHONPATH=. python ../debug_tools/ConnectFour_debug.py ai random connect4/initial_states/case4.txt --time 2
```

Add `--headless` to run a single AI turn without the game window. Use
`--debug-dir PATH` to choose the output folder (default: `debug_traces`). Each run
gets a timestamped subfolder. Each AI turn gets a `.txt` trace and a `.ai.py`
snapshot so its line numbers can still be checked after subsequent edits.

## Reading the trace

- `WORKER_ENTERED`: Python startup finished and the worker installed its handlers.
- `SEARCH_TIMEOUT_RAISED`: the first `TimeoutError` inside the AI, with its stack
  and source line. The AI can catch this and return normally.
- `AI_RETURNED`: the move method returned, including the chosen action.
- `ACTION_SENT`: the worker sent the action through the pipe.
- `UNHANDLED_EXCEPTION`: an exception escaped from the worker; its traceback follows.
- `PARENT_RESULT`: the last phase observed, process exit code, and elapsed time.

When the simulator deadline expires, the debug runner sends `SIGTERM`. A native
fault handler writes the worker's live Python stack before the process terminates.
The first frame in that dump is the active Python location. If it is inside a
library, follow the stack to its caller in `ai.py`. If the phase is `ACTION_SENT`,
the action had already been delivered and the delay was afterward.

If startup is terminated before `WORKER_ENTERED`, no AI traceback exists yet.
An external `SIGKILL` cannot be intercepted. The debug runner records whatever
phase information is available; it does not invent a last AI line.

Tracing adds overhead and can change which line is active when the deadline
expires. Use this runner to locate a cutoff, then use the original runner for
performance measurements. Return to your original command to disable debugging:

```sh
python -m connect4.ConnectFour ai random connect4/initial_states/case4.txt --time 2
```
