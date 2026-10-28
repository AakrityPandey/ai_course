"""Our material minimax strategy, adapted to Lichess's complete chess rules."""
import logging
import random
import time

import chess
from chess.engine import PlayResult, Limit
from lib.engine_wrapper import MinimalEngine

from chess_engine.ai import VALUE_OF_EACH_PIECE, MATE_SCORE

logger = logging.getLogger(__name__)


class SearchTimeout(Exception):
    pass


def material(board):
    return sum(value * (len(board.pieces(kind, chess.WHITE))
                        - len(board.pieces(kind, chess.BLACK)))
               for kind, value in VALUE_OF_EACH_PIECE.items())


def minimax(board, depth, alpha, beta, deadline):
    if time.monotonic() >= deadline:
        raise SearchTimeout
    outcome = board.outcome()
    if outcome is not None:
        if outcome.winner is None:
            return 0
        return MATE_SCORE if outcome.winner == chess.WHITE else -MATE_SCORE
    if depth == 0:
        return material(board)
    maximizing = board.turn == chess.WHITE
    best = float('-inf') if maximizing else float('inf')
    for move in board.legal_moves:
        board.push(move)
        try:
            score = minimax(board, depth - 1, alpha, beta, deadline)
        finally:
            board.pop()
        best = max(best, score) if maximizing else min(best, score)
        if maximizing:
            alpha = max(alpha, best)
        else:
            beta = min(beta, best)
        if alpha >= beta:
            break
    return best


def search_budget(board, limit, maximum=2.0):
    """Keep most of our clock available for later moves and network latency."""
    remaining = limit.white_clock if board.turn else limit.black_clock
    increment = limit.white_inc if board.turn else limit.black_inc
    if limit.time is not None:
        remaining = min(remaining, limit.time) if remaining is not None else limit.time
    if remaining is None:
        return maximum
    usable = max(0.0, remaining - 0.25)
    return max(0.0, min(maximum, usable / 30 + (increment or 0) / 2, usable / 4))


def choose_move(board, limit, max_depth=3, max_seconds=2.0, root_moves=None):
    legal = list(board.legal_moves)
    allowed = set(root_moves) if isinstance(root_moves, list) else set(legal)
    moves = [move for move in legal if move in allowed]
    if not moves:
        return None, 0
    best_move, completed_depth = random.choice(moves), 0
    deadline = time.monotonic() + search_budget(board, limit, max_seconds)
    maximizing = board.turn == chess.WHITE
    # Keep a legal fallback and only replace it after a full iteration finishes.
    for depth in range(1, max_depth + 1):
        scores = []
        try:
            for move in moves:
                board.push(move)
                try:
                    score = minimax(board, depth - 1, float('-inf'), float('inf'), deadline)
                finally:
                    board.pop()
                scores.append((move, score))
        except SearchTimeout:
            break
        best_score = (max if maximizing else min)(score for _, score in scores)
        best_move = random.choice([move for move, score in scores if score == best_score])
        completed_depth = depth
    return best_move, completed_depth


class CourseMinimax(MinimalEngine):
    def search(self, board, time_limit: Limit, ponder, draw_offered, root_moves):
        move, _ = choose_move(board, time_limit, root_moves=root_moves)
        return PlayResult(move, None)
