import random

from .rules import all_legal_moves, apply_move, game_status, is_in_check

HEURISTICS = ["total material score", "on each piece - number of defenders"]
VALUE_OF_EACH_PIECE = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
MATE_SCORE = 100_000


def random_move(state):
    moves = all_legal_moves(state)
    return random.choice(moves) if moves else None


def evaluate_position(state):
    """Score material from White's perspective."""
    score = 0
    for piece in state.board.flat:
        piece = int(piece)
        if piece:
            score += (1 if piece > 0 else -1) * VALUE_OF_EACH_PIECE[abs(piece)]
    return score


def _minimax(state, depth, alpha, beta):
    moves = all_legal_moves(state)
    if not moves:
        if is_in_check(state, state.turn):
            return -MATE_SCORE if state.turn == 1 else MATE_SCORE
        return 0
    if depth == 0:
        return evaluate_position(state)

    if state.turn == 1:
        best_score = float("-inf")
        for move in moves:
            child = state.copy()
            apply_move(child, move, validate=False)
            best_score = max(best_score, _minimax(child, depth - 1, alpha, beta))
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
        return best_score

    best_score = float("inf")
    for move in moves:
        child = state.copy()
        apply_move(child, move, validate=False)
        best_score = min(best_score, _minimax(child, depth - 1, alpha, beta))
        beta = min(beta, best_score)
        if alpha >= beta:
            break
    return best_score


def calculate_best_move(state, depth=3, on_branch=None):
    """Return the minimax move found within depth plies, or None if game is over."""
    if depth < 1:
        raise ValueError("depth must be at least 1")
    moves = all_legal_moves(state)
    if not moves:
        return None

    best_score = float("-inf") if state.turn == 1 else float("inf")
    best_moves = []
    alpha, beta = float("-inf"), float("inf")
    for move in moves:
        child = state.copy()
        apply_move(child, move, validate=False)
        # A full window gives an exact value for each reported root branch.
        # Sharing root bounds is faster but can return only a bound for losers.
        low, high = (float("-inf"), float("inf")) if on_branch else (alpha, beta)
        score = _minimax(child, depth - 1, low, high)
        if on_branch is not None:
            on_branch({"move": move, "immediate": evaluate_position(child),
                       "score": score, "depth": depth})
        if ((state.turn == 1 and score > best_score)
                or (state.turn == -1 and score < best_score)):
            best_score, best_moves = score, [move]
        elif score == best_score:
            best_moves.append(move)
        if state.turn == 1:
            alpha = max(alpha, best_score)
        else:
            beta = min(beta, best_score)
    return random.choice(best_moves)
