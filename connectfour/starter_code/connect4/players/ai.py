"""Fresh starter file for Assignment II: Game Playing AI Agent.

Only this file is intended to be submitted.  The simulator imports the
``AIPlayer`` class and calls one of the two move methods below.

This is intentionally a starter, not a completed solution.  Replace the
TODO sections with your own expectimax and adversarial-search code.
"""

from math import inf, log2
from itertools import chain
from multiprocessing import Array, Value
import random
from time import monotonic

from connect4.config import win_pts
from connect4.utils import (
    get_valid_actions, get_pts,
    get_diagonals_primary, get_diagonals_secondary,
)
from copy import deepcopy
import numpy as np

class AIPlayer:
    ENDGAME_WEIGHT = 10000
    PREFERRED_PLACEMENT_BONUS = 0.5
    OPPONENT_ONLY_POPOUT_BONUS = 2.0
    EARLY_POPOUT_PENALTY = 2.0
    ENDGAME_EMPTY_CELLS = 2

    def __init__(self, player_number: int, time: int):
        """Create an agent.

        :param player_number: 1 or 2
        :param time: time budget per move, in seconds
        """
        self.player_number = player_number
        self.opponent = 3 - player_number
        self.time_limit = float(time)
        search_budget = max(0.1, self.time_limit - 3)
        # Six moves at two seconds; add one move per doubling of the budget.
        self.endgame_moves = max(
            0, min(10, 6 + int(log2(search_budget / 2) // 1))
        )
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
        self.local_scores = {}


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
    
    def evaluate_move(self, board, move, player_number=None):
        """Score the board after a move, including that move's open directions.

        ``move`` is the game's (column, is_popout) action. A placement's row is
        the top occupied cell in its column on the resulting board. Popouts do
        not place a new piece, so they receive no placement-based bonuses.
        """
        filled = np.count_nonzero(board)
        weight = filled / board.size
        score = weight * self.evaluate(board)
        if move is None or move[1]:
            return score

        player_number = self.player_number if player_number is None else player_number
        column = move[0]
        occupied = np.flatnonzero(board[:, column] != 0)
        if not len(occupied):
            return score
        row = int(occupied[0])
        blocker = 3 - player_number
        rows, columns = board.shape
        open_neighbors = 0
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            for direction in (-1, 1):
                r, c = row + direction * dr, column + direction * dc
                while 0 <= r < rows and 0 <= c < columns and board[r, c] != blocker:
                    open_neighbors += 1
                    r += direction * dr
                    c += direction * dc

        sign = 1 if player_number == self.player_number else -1
        # Compare the actual placement with the opponent placing in the same
        # previously empty cell. Neither comparison changes the search board.
        before_move = board.copy()
        before_move[row, column] = 0
        player_before = get_pts(player_number, before_move)
        opponent_before = get_pts(blocker, before_move)
        player_gain = get_pts(player_number, board) - player_before
        before_move[row, column] = blocker
        opponent_gain = get_pts(blocker, before_move) - opponent_before
        score_swing = player_gain - opponent_gain
        score += sign * ((1 - weight) * open_neighbors)
        score += score_swing
        return score
    def evaluate(self, board):
        """Current score difference plus expected additional points.

        Each empty cell independently belongs to either player with probability
        1/2. This estimates potential, ignoring gravity, turn order and popouts.
        Existing opponent pieces separate a player's possible scoring series.
        """
        max_length = max(board.shape)
        if max_length not in self.local_scores:
            self._load_local_scores(max_length)
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
        scores = self.local_scores

        for cell in line:
            if cell != 0 and cell != player_number:
                expected_score += scores[length][decimal_value]
                length = 0
                decimal_value = 0
            else:
                decimal_value = (decimal_value << 1) | int(cell == player_number)
                length += 1
        return expected_score + scores[length][decimal_value]

    def _load_local_scores(self, max_length):
        """Copy shared scores once per move for ordinary list lookups in search."""
        self._prepare_sequence_scores(max_length)
        self.local_scores = {
            length: list(self.sequence_scores[length])
            for length in range(max_length + 1)
        }

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

    @staticmethod
    def _ordered_actions(actions, columns):
        """Search placements from the center outward, then other legal moves."""
        center = (columns - 1) / 2
        by_center = lambda action: (abs(action[0] - center), action[0])
        popouts = sorted((action for action in actions if action[1]), key=by_center)
        placements = sorted((action for action in actions if not action[1]), key=by_center)
        return placements + popouts

    def _search_actions(self, state, player):
        actions = get_valid_actions(player, state)
        return self._ordered_actions(actions, state[0].shape[1])

    def _root_move_preference(self, state, action):
        """Prefer selected current moves while either player has a PopOut."""
        board, popouts = state
        if not any(count.get_int() > 0 for count in popouts.values()):
            return 0.0
        column, is_popout = action
        if not is_popout:
            preferred_player = self.opponent if self.player_number == 1 else self.player_number
            return (
                self.PREFERRED_PLACEMENT_BONUS
                if column % 2 == preferred_player - 1 else 0.0
            )

        if self.player_number == 1:
            occupied = board[:, column]
            occupied = occupied[occupied != 0]
            if occupied.size and np.all(occupied == self.opponent):
                return self.OPPONENT_ONLY_POPOUT_BONUS
        elif np.count_nonzero(board == 0) > self.ENDGAME_EMPTY_CELLS:
            return -self.EARLY_POPOUT_PENALTY
        return 0.0

    def get_expectimax_move(self, state):
        """Choose a move against the supplied random agent.

        Part A of the assignment: use expectimax.  At your turns, choose the
        best child; at the random player's turns, average the child values.
        """

        # print({player: count.get_int() for player, count in state[1].items()})

        DEPTH = 100
        self.start_time = monotonic()
        actions = self._search_actions(state, self.player_number)
        if not actions:
            return (0, False)

        self._load_local_scores(max(state[0].shape))

        best_action = random.choice(actions)

        for d in range(1, DEPTH):
            # print("depth ", d)
            if not self.time_remaining():
                return best_action
            best_value_at_depth = float("-inf")
            best_actions_at_depth = []
            for action in actions:
                new_state = self.apply_action(state, self.player_number, action)
                try:
                    curr_value = self.expectimax(
                        new_state, self.opponent, d,
                        last_move=action, last_player=self.player_number,
                    )
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
            # print("depth", d, " done")
        return best_action

    def expectimax(self, state, player, depth, last_move=None, last_player=None):
        """Return an expectimax value, or abort the whole depth on timeout."""

        if not self.time_remaining():
            raise TimeoutError

        if depth == 0:
            return self.evaluate(state[0])

        actions = self._search_actions(state, player)
        if not actions:
            return self.evaluate(state[0])

        if player == self.player_number:
            max_val = -float("inf")
            for action in actions:
                value = self.expectimax(
                    self.apply_action(state, player, action),
                    3 - player,
                    depth - 1,
                    last_move=action, last_player=player,
                )
                max_val = max(max_val, value)
            return max_val

        if player == self.opponent:
            sum_scores = 0
            for action in actions:
                value = self.expectimax(
                    self.apply_action(state, player, action),
                    3 - player,
                    depth - 1,
                    last_move=action, last_player=player,
                )
                sum_scores += value
            return sum_scores / len(actions)

    def get_intelligent_move(self, state):
        """Choose a move against an adversarial opponent.

        Part B of the assignment: use minimax, preferably with alpha-beta
        pruning and a depth/time cutoff.
        """
        DEPTH = 100
        self.start_time = monotonic()
        actions = self._search_actions(state, self.player_number)
        if not actions:
            return (0, False)

        self._load_local_scores(max(state[0].shape))
        log_path = "ai_search.txt"
        action_labels = [f"{column} {'OUT' if is_popout else 'IN'}" for column, is_popout in actions]
        cell_width = 12
        header = f"{'Depth':>5} | {'Status':<8} | " + " | ".join(
            f"{label:>{cell_width}}" for label in action_labels
        )
        divider = "-" * len(header)

        def write_depth(depth, status, values):
            cells = [f"{'<=' if bounded else ''}{value:.3f}" for value, bounded in values]
            cells.extend("" for _ in range(len(actions) - len(cells)))
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"{depth:>5} | {status:<8} | "
                    + " | ".join(f"{cell:>{cell_width}}" for cell in cells)
                    + "\n"
                )

        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n{'=' * len(header)}\nPlayer {self.player_number} — current board\n")
            log_file.write("Columns: " + " ".join(f"{column:>2}" for column in range(state[0].shape[1])) + "\n")
            for row in state[0]:
                log_file.write("         " + " ".join(f"{int(cell):>2}" for cell in row) + "\n")
            log_file.write(
                "PopOuts: " + ", ".join(
                    f"P{player}={count.get_int()}" for player, count in sorted(state[1].items())
                ) + "\n"
            )
            log_file.write("Values are from this AI's perspective; <= marks an upper bound from pruning.\n")
            log_file.write(header + "\n" + divider + "\n")
        endgame_now = np.count_nonzero(state[0] == 0) + 2 * sum(
            count.get_int() for count in state[1].values()
        ) <= self.endgame_moves

        best_action = random.choice(actions)

        for d in range(1, DEPTH):
            # print("Cuti depth", d)
            if not self.time_remaining():
                return best_action
            best_value_at_depth = float("-inf")
            best_action_at_depth = actions[0]
            action_values = []
            alpha = -inf
            beta = inf
            for action in actions:
                new_state = self.apply_action(state, self.player_number, action)
                preference = self._root_move_preference(state, action)
                search_alpha = alpha
                try:
                    child_value = self.minimax(
                        new_state, self.opponent, d,
                        last_move=action, last_player=self.player_number,
                        alpha=alpha - preference, beta=beta,
                    )
                    curr_value = child_value + preference
                    alpha = max(alpha, curr_value)
                    if not self.time_remaining():
                        raise TimeoutError
                except TimeoutError:
                    # write_depth(d, "partial", action_values)
                    # Keep the result of the last fully completed depth.
                    return best_action

                action_values.append((curr_value, curr_value <= search_alpha))
                if curr_value > best_value_at_depth:
                    best_value_at_depth = curr_value
                    best_action_at_depth = action
                # A result equal to alpha can be only an upper bound. Keep
                # the proven best action rather than treating it as a tie.

            # write_depth(d, "complete", action_values)
            best_action = best_action_at_depth
            if endgame_now:
                return best_action
            # print("depth", d, " done")
        return best_action

    def minimax(self, state, player, depth,
                last_move=None, last_player=None, alpha=-inf, beta=inf):
        """Return the alpha-beta minimax value of a state."""

        if not self.time_remaining():
            raise TimeoutError
        actions = self._search_actions(state, player)
        if not actions:
            return self.ENDGAME_WEIGHT * (
                get_pts(self.player_number, state[0])
                - get_pts(self.opponent, state[0])
            )

        remaining_moves = np.count_nonzero(state[0] == 0) + 2 * sum(
            count.get_int() for count in state[1].values()
        )
        if depth <= 0 and remaining_moves > self.endgame_moves:
            return self.evaluate_move(state[0], last_move, last_player)

        # Within the time-based endgame threshold, ignore the depth cutoff.
        # A placement removes one empty cell; a popout consumes one allowance
        # and creates one empty cell, so remaining_moves falls by one either way.

        if player == self.player_number:
            best_value = -inf
            for action in actions:
                value = self.minimax(
                    self.apply_action(state, player, action),
                    3 - player,
                    depth - 1, last_move=action, last_player=player, alpha=alpha, beta=beta,
                )
                best_value = max(best_value, value)
                alpha = max(alpha, best_value)
                if alpha >= beta:
                    break
            return best_value

        if player == self.opponent:
            best_value = inf
            for action in actions:
                value = self.minimax(
                    self.apply_action(state, player, action),
                    3 - player,
                    depth - 1,
                    last_move=action, last_player=player, alpha=alpha, beta=beta,
                )
                best_value = min(best_value, value)
                beta = min(beta, best_value)
                if alpha >= beta:
                    break
            return best_value


    def time_remaining(self):
        "Considering fixed overhead of 2 secs"
        return monotonic() - self.start_time < self.time_limit - 3
