"""Smoke-check Windows spawn, move delivery, and cancellation without a window."""
import time

from chess_engine import BoardState, Player
from chess_engine.rules import all_legal_moves
from pygame_ui import PygameChessUI


class Clock:
    @staticmethod
    def get_ticks():
        return 1000


class PygameStub:
    time = Clock()


def check():
    state = BoardState.initial()
    ui = PygameChessUI(state, {1: ("AI", Player("minimax", depth=1)),
                              -1: ("Human", Player("manual"))})
    legal = all_legal_moves(state)
    try:
        ui._play_automatic_turn(PygameStub)
        assert ui._ai_process is not None
        deadline = time.monotonic() + 20
        while ui._ai_process is not None and time.monotonic() < deadline:
            ui._play_automatic_turn(PygameStub)
            time.sleep(0.01)
        assert ui._ai_error is None, ui._ai_error
        assert ui.last_ui_move in legal
        assert state.turn == -1
    finally:
        ui._stop_ai()

    ui = PygameChessUI(BoardState.initial(),
                      {1: ("AI", Player("minimax", depth=10))})
    try:
        ui._play_automatic_turn(PygameStub)
        process = ui._ai_process
        assert process.is_alive()
        ui._stop_ai()
        assert ui._ai_process is None and ui._ai_connection is None
    finally:
        ui._stop_ai()
    print("PASS: spawned AI returns a legal move; deep search cancels cleanly.")


if __name__ == "__main__":
    check()
