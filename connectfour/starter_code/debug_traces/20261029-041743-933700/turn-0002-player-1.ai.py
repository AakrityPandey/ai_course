"""Fresh starter file for Assignment II: Game Playing AI Agent.

Only this file is intended to be submitted.  The simulator imports the
``AIPlayer`` class and calls one of the two move methods below.

This is intentionally a starter, not a completed solution.  Replace the
TODO sections with your own expectimax and adversarial-search code.
"""

from math import inf
from itertools import chain
from multiprocessing import Array, Value
import random
from time import monotonic

from connect4.config import win_pts
from connect4.utils import (
    get_valid_actions,
    get_diagonals_primary, get_diagonals_secondary,
)
from copy import deepcopy
import numpy as np

class AIPlayer:
    def __init__(self, player_number: int, time: int):
        """Create an agent.

        :param player_number: 1 or 2
        :param time: time budget per move, in seconds
        """
        self.player_number = player_number
        self.opponent = 3 - player_number
        self.time_limit = float(time)
        self.type = "ai"
        self.player_string = "Player {}:ai".format(player_number)
        self.start_time = 0.0
        # Length preserves leading zeros; the decimal value indexes each table.
        # Shared storage survives the simulator's fresh worker on every turn.
        self.sequence_scores = {
            length: Array("d", 1 << length, lock=False)
            for length in range(13)
        }
        self._prepared_length = Value("i", 0, lock=False)

    def apply_action(self, state, player, action):
        new_state = deepcopy(state)
        board, popouts = new_state
        column, is_popout = action

        if not is_popout:
            empty_rows = np.where(board[:, column] == 0)[0]
            board[empty_rows[-1], column] = player

        else:
            board[1:, column] = board[:-1, column]
            board[0, column] = 0
            popouts[player].decrement()

        return new_state

    def evaluate(self, board):
        """Current score difference plus expected additional points.

        Each empty cell independently belongs to either player with probability
        1/2. This estimates potential, ignoring gravity, turn order and popouts.
        Existing opponent pieces separate a player's possible scoring series.
        """
        self._prepare_sequence_scores(max(board.shape))
        score = 0.0
        lines = chain(
            board, board.T,
            get_diagonals_primary(board), get_diagonals_secondary(board),
        )
        for line in lines:
            score += (
                self._expected_line_score(line, self.player_number)
                - self._expected_line_score(line, self.opponent)
            )

        return score

    def _expected_line_score(self, line, player_number):
        """Split at opponent pieces and look up each binary series's score."""
        expected_score = 0.0
        length = 0
        decimal_value = 0

        for cell in line:
            if cell != 0 and cell != player_number:
                expected_score += self.sequence_scores[length][decimal_value]
                length = 0
                decimal_value = 0
            else:
                decimal_value = (decimal_value << 1) | int(cell == player_number)
                length += 1
        return expected_score + self.sequence_scores[length][decimal_value]

    def _prepare_sequence_scores(self, max_length):

        """Precompute E[score] for every binary series up to max_length.

        Extend each shorter prefix with 0 (probability 1/2) or 1 (certain).
        Run lengths modulo four suffice for the game's run scoring rule.
        There are only 8190 nonempty series for a maximum length of 12.
        """
        if not 0 <= max_length <= 12:
            raise ValueError("The sequence table supports board dimensions up to 12")
        if self._prepared_length.value >= max_length:
            return

        group_size = len(win_pts) - 1
        gains = [win_pts[i + 1] - win_pts[i] for i in range(group_size)]
        prefix_probabilities = [[1.0] + [0.0] * (group_size - 1)]
        for length in range(1, max_length + 1):
            next_prefixes = []
            for decimal_value in range(1 << length):
                prefix = decimal_value >> 1
                p = 1.0 if decimal_value & 1 else 0.5
                probabilities = [1.0 - p] + [0.0] * (group_size - 1)
                score = self.sequence_scores[length - 1][prefix]
                for run_length, probability in enumerate(prefix_probabilities[prefix]):
                    extension_probability = probability * p
                    score += extension_probability * gains[run_length]
                    probabilities[(run_length + 1) % group_size] += extension_probability
                self.sequence_scores[length][decimal_value] = score
                next_prefixes.append(probabilities)
            prefix_probabilities = next_prefixes
        self._prepared_length.value = max_length

    def get_expectimax_move(self, state):
        """Choose a move against the supplied random agent.

        Part A of the assignment: use expectimax.  At your turns, choose the
        best child; at the random player's turns, average the child values.
        """
        DEPTH = 6
        self.start_time = monotonic()
        actions = get_valid_actions(self.player_number, state)
        if not actions:
            return (0, False)

        self._prepare_sequence_scores(max(state[0].shape))

        best_action = random.choice(actions)

        for d in range(1, DEPTH):
            print("depth ", d)
            if not self.time_remaining():
                return best_action
            best_value_at_depth = float("-inf")
            best_actions_at_depth = []
            for action in actions:
                new_state = self.apply_action(state, self.player_number, action)
                try:
                    curr_value = self.expectimax(new_state, self.opponent, d)
                    if not self.time_remaining():
                        raise TimeoutError
                except TimeoutError:
                    # Keep the result of the last fully completed depth.
                    return best_action

                if curr_value > best_value_at_depth:
                    best_value_at_depth = curr_value
                    best_actions_at_depth = [action]
                elif curr_value == best_value_at_depth:
                    best_actions_at_depth.append(action)

            best_action = random.choice(best_actions_at_depth)
            
        return best_action

    def expectimax(self, state, player, depth):
        """Return an expectimax value, or abort the whole depth on timeout."""

        if not self.time_remaining():
            raise TimeoutError

        if depth == 0:
            return self.evaluate(state[0])

        actions = get_valid_actions(player, state)
        if not actions:
            return self.evaluate(state[0])

        if player == self.player_number:
            max_val = -float("inf")
            for action in actions:
                value = self.expectimax(
                    self.apply_action(state, player, action),
                    3 - player,
                    depth - 1
                )
                max_val = max(max_val, value)
            return max_val

        if player == self.opponent:
            sum_scores = 0
            for action in actions:
                value = self.expectimax(
                    self.apply_action(state, player, action),
                    3 - player,
                    depth - 1
                )
                sum_scores += value
            return sum_scores / len(actions)

    def get_intelligent_move(self, state):
        """Choose a move against an adversarial opponent.

        Part B of the assignment: use minimax, preferably with alpha-beta
        pruning and a depth/time cutoff.
        """
        return self.get_expectimax_move(state)

    def minimax(self, state, player, depth, alpha=-inf, beta=inf):
        """Return the alpha-beta minimax value of a state."""
        # TODO: implement maximizing/minimizing branches and pruning.
        raise NotImplementedError

    def time_remaining(self):
        "Considering fixed overhead of 0.5 secs"
        return monotonic() - self.start_time < self.time_limit - 0.5
