"""Diagnostic copy of ConnectFour.py; imports the current assignment AI unchanged.

Run from starter_code:
    PYTHONPATH=. python ../debug_tools/ConnectFour_debug.py ai random connect4/initial_states/case4.txt --time 2
Add --headless to diagnose one AI turn without opening the game window.
"""
# system libs
import faulthandler
import os
from pathlib import Path
import signal
import traceback
import argparse
import json
import multiprocessing as mp
import random
import sys
import tkinter as tk
from datetime import datetime

# 3rd party libs
from threading import Thread
from time import sleep, monotonic
from typing import Tuple, Callable, Dict

import numpy as np

from connect4.utils import get_pts, get_valid_actions, Integer

# Local libs
from connect4.players.ai import AIPlayer
from connect4.players.random import RandomPlayer
from connect4.players.human import HumanPlayer


TimeLimitExceedAction = (1000, True)

def create_debug_dir():
    folder = Path(os.environ.get("CONNECT4_DEBUG_DIR", "debug_traces"))
    folder = folder / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True, exist_ok=True)
    return folder.resolve()


def turn_worker(state, send_end, p_func, trace_path, progress):
    # Keep the descriptor open through multiprocessing shutdown as well.
    trace_file = open(trace_path, "a", buffering=1)
    mp.current_process()._debug_trace_file = trace_file
    faulthandler.enable(file=trace_file, all_threads=True)
    # terminate() sends SIGTERM on macOS/Linux. Dump the live stack, then
    # chain to normal termination; no Python-level exception handler is needed.
    faulthandler.register(signal.SIGTERM, file=trace_file, all_threads=True, chain=True)
    ai_file = sys.modules[p_func.__self__.__class__.__module__].__file__
    timeout_recorded = False

    def trace_ai(frame, event, arg):
        nonlocal timeout_recorded
        if frame.f_code.co_filename != ai_file:
            return None
        # Capture exception events without emitting every executed line.
        frame.f_trace_lines = False
        if event == "exception" and issubclass(arg[0], TimeoutError) and not timeout_recorded:
            timeout_recorded = True
            print("SEARCH_TIMEOUT_RAISED (the AI may catch this and return normally)", file=trace_file)
            traceback.print_stack(frame, file=trace_file)
            traceback.print_exception(*arg, file=trace_file)
            trace_file.flush()
        return trace_ai

    progress[1] = monotonic()
    progress[0] = 1
    print(f"WORKER_ENTERED pid={os.getpid()} at={progress[1]:.6f}", file=trace_file)
    try:
        sys.settrace(trace_ai)
        action = p_func(state)
        sys.settrace(None)
        progress[2] = monotonic()
        progress[0] = 2
        print(f"AI_RETURNED action={action!r} at={progress[2]:.6f}", file=trace_file)
        send_end.send(action)
        progress[3] = monotonic()
        progress[0] = 3
        print(f"ACTION_SENT at={progress[3]:.6f}", file=trace_file)
    except BaseException:
        print("UNHANDLED_EXCEPTION", file=trace_file)
        traceback.print_exc(file=trace_file)
        trace_file.flush()
        raise
    finally:
        sys.settrace(None)
        print("WORKER_FUNCTION_EXITING", file=trace_file)
        trace_file.flush()
        send_end.close()


def run_debug_turn(state, p_func, time_limit, trace_path):
    trace_path = Path(trace_path).resolve()
    ai_path = Path(sys.modules[p_func.__self__.__class__.__module__].__file__).resolve()
    snapshot_path = trace_path.with_suffix(".ai.py")
    snapshot_path.write_text(ai_path.read_text())
    progress = mp.Array("d", 4, lock=False)
    receiver, sender = mp.Pipe(False)
    process = mp.Process(target=turn_worker, args=(state, sender, p_func, str(trace_path), progress))
    started = monotonic()
    trace_path.write_text(
        f"TURN_START at={started:.6f} limit={time_limit}s\n"
        f"AI_FILE={ai_path}\nAI_SNAPSHOT={snapshot_path}\n"
        "If no WORKER_ENTERED follows, startup ended before the worker installed its stack handler.\n"
    )
    failed = False
    try:
        process.start()
        sender.close()
        process.join(time_limit)
        if process.is_alive():
            # The child writes its stack on receipt of SIGTERM, before exiting.
            process.terminate()
            process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            raise TimeoutError("Player Exceeded time limit; see debug traceback")
        if process.exitcode != 0:
            raise RuntimeError(f"Worker exited with code {process.exitcode}; see debug traceback")
        if not receiver.poll(0.1):
            raise RuntimeError("Worker exited without sending an action")
        return receiver.recv()
    except BaseException:
        failed = True
        raise
    finally:
        sender.close()
        receiver.close()
        if process.pid is not None and process.is_alive():
            process.terminate()
            process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
        ended = monotonic()
        phase = ("STARTUP", "INSIDE_AI", "AI_RETURNED", "ACTION_SENT")[int(progress[0])]
        with trace_path.open("a") as output:
            print(f"PARENT_RESULT phase={phase} exitcode={process.exitcode} elapsed={ended - started:.6f}s", file=output)
            if progress[1]:
                print(f"STARTUP_SECONDS={progress[1] - started:.6f}", file=output)
            if progress[2]:
                print(f"AI_SECONDS={progress[2] - progress[1]:.6f}", file=output)
            if progress[3]:
                print(f"SEND_SECONDS={progress[3] - progress[2]:.6f}", file=output)
        print(f"[debug] {phase}: {trace_path}", flush=True)
        if failed:
            print(trace_path.read_text(), flush=True)


class Game:
    def __init__(self, player1, player2, time: int, board_init: np.array, m: int, n: int, popout_moves: int):
        """
        :param player1:
        :param player2:
        :param time: Time in milliseconds
        :param m:
        :param n:
        :param popout_moves:
        """
        self.debug_dir = create_debug_dir()
        self.debug_turn = 0
        self.players = [player1, player2]
        self.colors = ['white', 'yellow', 'red']  # Extra white color added
        self.current_turn = 0
        self.m = m
        self.n = n
        # Giving both of the players same number of popout moves.
        self.state = board_init, {1: Integer(popout_moves), 2: Integer(popout_moves)}
        self.gui_board = []
        self.game_over = False
        self.ai_turn_limit = time

        board = self.state[0]
        # Log: Writing initial state of the board to log file
        # Explain the log file
        with open(self.debug_dir / 'game.log', 'w') as log_file:
            s = f'{m} {n}\n'
            for i in range(m):
                for j in range(n):
                    s += str(board[i][j]) + ' '
                s += '\n'
            s += f'{popout_moves}\n'
            log_file.write(s)
            #print(s)

        # https://stackoverflow.com/a/38159672
        root = tk.Tk()
        root.title('Extended Connect 4')

        self.current = tk.Label(root, text="Current:")
        self.current.pack()

        self.player1_string = tk.Label(root, text=player1.player_string)
        self.player1_string.pack()

        self.player2_string = tk.Label(root, text=player2.player_string)
        self.player2_string.pack()

        height = m * 100
        width = n * 100
        self.c = tk.Canvas(root, height=height, width=width)
        self.c.pack()
        for j in range(n):
            column = []
            row = j * 100
            for i in range(m):
                col = i * 100
                c = board[i][j]
                column.append(self.c.create_oval(row, col, row + 100, col + 100, fill=self.colors[c]))
            self.gui_board.append(column)

        thread = Thread(target=self.threaded_function, args=(100000,))
        thread.start()
        root.mainloop()

    # def get_random_board(self):
    #     m = self.m
    #     n = self.n
    #     board = np.zeros([m, n]).astype(np.uint8)
    #     # for j in range(n):
    #     #     x = random.randrange(m)
    #     #     for i in range(x, m):
    #     #         p = random.randrange(2) + 1
    #     #         board[i][j] = p
    #     return board

    def threaded_function(self, arg):
        sleep(1)  # Wait for tkinter to setup
        for i in range(arg):
            self.make_move()
            # wait 0.01 sec in between
            sleep(0.01)
            if self.game_over:
                with open(self.debug_dir / 'game.log', 'w') as log_file:
                    s = 'Game Over\n'
                    s += f'Player 1 Score: {get_pts(1, self.state[0])}\n'
                    s += f'Player 2 Score: {get_pts(2, self.state[0])}\n'
                    margin_diff = 0
                    pt1 = get_pts(1,self.state[0])
                    pt2 = get_pts(2,self.state[0])
                    if pt1 > pt2:
                        margin_diff = ((pt1-pt2)/pt2)*100
                    else:
                        margin_diff = ((pt2-pt1)/pt1)*100
                    s += 'Margin difference: ' + str(margin_diff) + '\n'
                    log_file.write(s)
                    print(s)
                break

    def make_move(self):
        current_player = self.players[self.current_turn]
        valid_actions = get_valid_actions(current_player.player_number, self.state)

        if len(valid_actions) == 0:
            self.game_over = True

        if not self.game_over:
            if current_player.type == 'ai':
                if self.players[int(not self.current_turn)].type == 'random':
                    p_func = current_player.get_expectimax_move
                else:
                    p_func = current_player.get_intelligent_move
                try:
                    self.debug_turn += 1
                    trace_path = self.debug_dir / f"turn-{self.debug_turn:04d}-player-{current_player.player_number}.txt"
                    action = run_debug_turn(self.state, p_func, self.ai_turn_limit, trace_path)
                except Exception as e:
                    uh_oh = 'Uh oh.... something is wrong with Player {}'
                    print(uh_oh.format(current_player.player_number))
                    print(e)
                    action = TimeLimitExceedAction
            else:
                action = current_player.get_move(self.state)

            if action == TimeLimitExceedAction:
                log_action = {'player': current_player.player_number, 'move': 'TLE', 'is_pop': 'TLE'}
            elif action not in valid_actions:
                # Invalid move by the player. Don't do anything
                log_action = {'player': current_player.player_number, 'move': 'invalid', 'is_pop': 'invalid'}
            else:
                move, is_popout = action
                self.update_board(int(move), current_player.player_number, is_popout=is_popout)
                log_action = {'player': current_player.player_number, 'move': int(move), 'is_pop': is_popout}

            # Log: Writing action to log file
            with open(self.debug_dir / 'game.log', 'a') as log_file:
                log_file.write(json.dumps(log_action) + '\n')

            self.current_turn = int(not self.current_turn)

            self.current.configure(text=f'cur: {self.players[self.current_turn].player_string}, ')
            self.player1_string.configure(text=f'player1: {get_pts(1, self.state[0])}, '
                                               f'popout left: {self.state[1][1].get_int()}')
            self.player2_string.configure(text=f' player2: {get_pts(2, self.state[0])}, '
                                               f'popout left: {self.state[1][2].get_int()}')

    def update_board(self, column: int, player_num: int, is_popout: bool = False):
        board, num_popouts = self.state
        if not is_popout:
            if 0 in board[:, column]:
                for row in range(1, board.shape[0]):
                    update_row = -1
                    if board[row, column] > 0 and board[row - 1, column] == 0:
                        update_row = row - 1
                    elif row == board.shape[0] - 1 and board[row, column] == 0:
                        update_row = row
                    if update_row >= 0:
                        board[update_row, column] = player_num
                        self.c.itemconfig(self.gui_board[column][update_row], fill=self.colors[self.current_turn + 1])
                        break
            else:
                err = 'Invalid move by player {}. Column {}'.format(player_num, column, is_popout)
                raise Exception(err)
        else:
            if 1 in board[:, column] or 2 in board[:, column]:
                for r in range(board.shape[0] - 1, 0, -1):
                    board[r, column] = board[r - 1, column]
                    self.c.itemconfig(self.gui_board[column][r], fill=self.colors[
                        board[r, column]])  # this needs to be tweaked
                board[0, column] = 0
                self.c.itemconfig(self.gui_board[column][0], fill=self.colors[0])
            else:
                err = 'Invalid move by player {}. Column {}'.format(player_num, column)
                raise Exception(err)
            num_popouts[player_num].decrement()


def get_start_board(file_pth: str) -> Tuple[int, np.array]:
    num_pop_outs = -1
    b = []
    with open(file_pth) as f:
        for line in f:
            line = line.strip()
            if num_pop_outs == -1:
                num_pop_outs = int(line)
            else:
                row = [int(ch) for ch in line.split(' ')]
                b.append(row)
    board = np.array(b, dtype=int)
    return num_pop_outs, board


def main(player1: str, player2: str, init_fine_name: str, time: int):
    def make_player(name, num):
        if name == 'ai':
            return AIPlayer(num, time)
        elif name == 'random':
            return RandomPlayer(num)
        elif name == 'human':
            return HumanPlayer(num)

    # Python 3.11 does not accept a datetime object as a random seed.
    random.seed(datetime.now().timestamp())
    # Both players should have the same number of columns for pop out movements, thus number of columns should be even
    num_pop_outs, board = get_start_board(init_fine_name)
    m, n = board.shape
    Game(make_player(player1, 1), make_player(player2, 2), time, board, m, n, num_pop_outs)


if __name__ == '__main__':
    player_types = ['ai', 'random', 'human']
    parser = argparse.ArgumentParser()
    parser.add_argument('player1', choices=player_types)
    parser.add_argument('player2', choices=player_types)
    parser.add_argument("start_file", help="Initial state of the game (Num popout moves, Board)")
    # Giving Max of 60 seconds to AI agent in each step
    parser.add_argument('--time',
                        type=int,
                        default=20,
                        help='Time to wait for a move in seconds (int)')
    parser.add_argument('--debug-dir', default='debug_traces', help='Folder for timestamped traceback files')
    parser.add_argument('--headless', action='store_true', help='Diagnose one AI turn without opening a window')
    args = parser.parse_args()
    os.environ['CONNECT4_DEBUG_DIR'] = args.debug_dir
    if args.headless:
        if 'ai' not in (args.player1, args.player2):
            parser.error('--headless requires an AI player')
        player = 1 if args.player1 == 'ai' else 2
        popouts, board = get_start_board(args.start_file)
        state = board, {1: Integer(popouts), 2: Integer(popouts)}
        ai = AIPlayer(player, args.time)
        opponent_type = args.player2 if player == 1 else args.player1
        choose = ai.get_expectimax_move if opponent_type == 'random' else ai.get_intelligent_move
        trace_path = create_debug_dir() / f'turn-0001-player-{player}.txt'
        action = run_debug_turn(state, choose, args.time, trace_path)
        print(f'Action: {action}')
    else:
        main(args.player1, args.player2, args.start_file, args.time)
