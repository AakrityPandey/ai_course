"""Run the assignment simulator with two different AIPlayer implementations.

From connectfour/starter_code:
    PYTHONPATH=. python ../debug_tools/match_ais.py connect4/initial_states/case4.txt --time 2
    PYTHONPATH=. python ../debug_tools/match_ais.py connect4/initial_states/case4.txt --time 2 --player1 ai_tanmay_noob.py --player2 ai.py

Place the opposing implementation at connect4/players/ai_tanmay_noob.py.
Only this separate runner loads it; the assignment simulator stays unchanged.
"""

import argparse
import importlib
from pathlib import Path

import connect4.ConnectFour as simulator

PLAYER_1_FILE = "ai.py"
PLAYER_2_FILE = "ai_tanmay_noob.py"


def _load_ai(filename):
    path = Path(__file__).resolve().parents[1] / "starter_code/connect4/players" / filename
    if path.name != filename or path.suffix != ".py" or not path.is_file():
        raise ValueError(f"AI file must be an existing .py file in {path.parent}: {filename}")
    return importlib.import_module(f"connect4.players.{path.stem}").AIPlayer


def main(start_file, time_limit, player1_file=PLAYER_1_FILE, player2_file=PLAYER_2_FILE):
    player_classes = {1: _load_ai(player1_file), 2: _load_ai(player2_file)}

    def make_ai(player_number, move_time):
        cls = player_classes[player_number]
        player = cls(player_number, move_time)
        if not callable(getattr(player, "get_intelligent_move", None)):
            raise TypeError(f"{cls.__module__}.AIPlayer needs get_intelligent_move(state)")
        return player

    # The simulator's main() constructs players through this name. Its Game,
    # rules, time limit, and window remain the same as in the assignment.
    simulator.AIPlayer = make_ai
    simulator.main("ai", "ai", start_file, time_limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start_file", help="Initial board file")
    parser.add_argument("--time", type=int, default=20, help="Seconds per AI move")
    parser.add_argument("--player1", default=PLAYER_1_FILE, help="Player 1 AI filename")
    parser.add_argument("--player2", default=PLAYER_2_FILE, help="Player 2 AI filename")
    options = parser.parse_args()
    main(options.start_file, options.time, options.player1, options.player2)
