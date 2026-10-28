from .ai import calculate_best_move, random_move
from .rules import all_legal_moves


class Player:
    """Player configured for manual, random, or minimax move selection."""

    MODES = {"manual", "random", "minimax"}

    def __init__(self, mode="manual", depth=3, manual_move_provider=None):
        if mode not in self.MODES:
            raise ValueError(f"mode must be one of {sorted(self.MODES)}")
        self.mode = mode
        self.depth = depth
        self.manual_move_provider = manual_move_provider

    def choose_move(self, state, on_branch=None):
        if self.mode == "manual":
            if self.manual_move_provider is None:
                raise ValueError("Manual mode needs a move provider from the UI.")
            move = self.manual_move_provider(state)
            if move is None:
                return None
            if move not in all_legal_moves(state):
                raise ValueError("The manual move provider returned an illegal move.")
            return move
        if self.mode == "random":
            return random_move(state)
        return calculate_best_move(state, depth=self.depth, on_branch=on_branch)
