# Assignment II: Game Playing AI Agent

This folder is a fresh starter package based on `ass2.pdf`.

## Folder contents

```text
starter_code/
├── README.md
├── environment.yml
└── connect4/
    ├── ConnectFour.py
    ├── __init__.py
    ├── config.py
    ├── initial_states/
    │   ├── case1.txt
    │   ├── case2.txt
    │   ├── case3.txt
    │   └── case4.txt
    ├── players/
    │   ├── __init__.py
    │   ├── ai.py
    │   ├── human.py
    │   └── random.py
    ├── utils.py
    └── utils_test.py
```

## Setup

From this folder:

```bash
conda env create --file environment.yml
conda activate myenv
```

## Run the simulator

From `starter_code/`:

```bash
PYTHONPATH=. python3 -m connect4.ConnectFour ai random connect4/initial_states/case4.txt --time 20
```

Other examples:

```bash
PYTHONPATH=. python3 -m connect4.ConnectFour ai human connect4/initial_states/case4.txt --time 20
PYTHONPATH=. python3 -m connect4.ConnectFour ai ai connect4/initial_states/case4.txt --time 20
```

## Your task

Only modify `connect4/players/ai.py` for the assignment submission.

- Part A: implement `get_expectimax_move` against the random player.
- Part B: implement `get_intelligent_move` against an adversarial player.
- Use depth-limited or cutoff search because every move has a time budget.
- Keep the `AIPlayer(player_number, time)` constructor unchanged.
- Do not use global variables or threading in `ai.py`.

The state is `(board, num_popout)`, where the board uses `0`, `1`, and `2`,
and `num_popout[player].get_int()` returns the remaining PopOut moves.
