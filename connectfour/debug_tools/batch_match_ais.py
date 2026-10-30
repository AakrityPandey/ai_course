"""Play every starter board headlessly with configurable AI files."""

import argparse
import importlib
import multiprocessing as mp
from pathlib import Path
from time import monotonic

import numpy as np

from connect4.utils import Integer, get_pts, get_valid_actions


def _worker(player, state, sender):
    try:
        sender.send(("ok", player.get_intelligent_move(state)))
    except BaseException as exc:
        sender.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        sender.close()


def _choose(player, state, seconds):
    receiver, sender = mp.Pipe(False)
    process = mp.Process(target=_worker, args=(player, state, sender))
    try:
        process.start()
        sender.close()
        process.join(seconds)
        if process.is_alive():
            return None, "time limit exceeded"
        if process.exitcode != 0:
            return None, f"worker exited with code {process.exitcode}"
        if not receiver.poll(0.1):
            return None, "worker returned no action"
        status, payload = receiver.recv()
        return (payload, None) if status == "ok" else (None, payload)
    finally:
        if process.pid is not None and process.is_alive():
            process.terminate()
            process.join(0.5)
            if process.is_alive():
                process.kill()
                process.join()
        sender.close()
        receiver.close()


def _read_case(path):
    lines = path.read_text().splitlines()
    popouts = int(lines[0])
    board = np.array([[int(cell) for cell in line.split()] for line in lines[1:]], dtype=int)
    return board, {1: Integer(popouts), 2: Integer(popouts)}


def _load_ai(filename):
    path = Path(__file__).resolve().parents[1] / "starter_code/connect4/players" / filename
    if path.name != filename or path.suffix != ".py" or not path.is_file():
        raise ValueError(f"AI file must be an existing .py file in {path.parent}: {filename}")
    module = importlib.import_module(f"connect4.players.{path.stem}")
    return module.AIPlayer


def play_case(path, seconds, return_scores=False,
              player1_file="ai.py", player2_file="ai_tanmay_noob.py"):
    state = _read_case(path)
    board, popouts = state
    players = {1: _load_ai(player1_file)(1, seconds),
               2: _load_ai(player2_file)(2, seconds)}
    max_turns = 4 * (board.size + 2 * sum(counter.get_int() for counter in popouts.values())) + 20
    started = monotonic()
    wasted = {1: 0, 2: 0}
    consecutive_wasted = 0

    def waste_turn(player_number, reason):
        nonlocal consecutive_wasted
        wasted[player_number] += 1
        consecutive_wasted += 1
        if consecutive_wasted >= 12:
            return result(f"stalled after 12 consecutive wasted moves; last issue: player {player_number}: {reason}; wasted={wasted}; seconds={monotonic() - started:.1f}")
        return None

    def result(description):
        if return_scores:
            return description, get_pts(1, board), get_pts(2, board)
        return description

    for turn in range(max_turns):
        player_number = turn % 2 + 1
        legal = get_valid_actions(player_number, state)
        if not legal:
            scores = (get_pts(1, board), get_pts(2, board))
            winner = player1_file if scores[0] > scores[1] else player2_file if scores[1] > scores[0] else "tie"
            return result(f"finished, moves={turn}, scores={scores}, winner={winner}, wasted={wasted}, seconds={monotonic() - started:.1f}")

        action, error = _choose(players[player_number], state, seconds)
        if error:
            stopped = waste_turn(player_number, error)
            if stopped:
                return stopped
            continue
        if action not in legal:
            stopped = waste_turn(player_number, f"invalid action {action}")
            if stopped:
                return stopped
            continue

        consecutive_wasted = 0
        column, is_popout = action
        if is_popout:
            board[1:, column] = board[:-1, column]
            board[0, column] = 0
            popouts[player_number].decrement()
        else:
            empty = np.flatnonzero(board[:, column] == 0)
            board[empty[-1], column] = player_number
    return result(f"stopped at {max_turns}-turn safety cap; scores=({get_pts(1, board)}, {get_pts(2, board)}), wasted={wasted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--time", type=int, default=2, help="Seconds allowed per move")
    parser.add_argument("--player1", default="ai.py", help="Player 1 AI filename")
    parser.add_argument("--player2", default="ai_tanmay_noob.py", help="Player 2 AI filename")
    options = parser.parse_args()
    folder = Path(__file__).resolve().parents[1] / "starter_code/connect4/initial_states"
    for path in sorted(folder.glob("case*.txt")):
        print(f"{path.name}: {play_case(path, options.time, player1_file=options.player1, player2_file=options.player2)}", flush=True)
