from .state import BoardState


def add_if_valid_move(state, row, col, new_row, new_col):
    if not (0 <= new_row < 8 and 0 <= new_col < 8):
        return False
    piece = int(state.board[row, col])
    target = int(state.board[new_row, new_col])
    return piece != 0 and (target == 0 or piece * target < 0)


def is_square_attacked(state, target_row, target_col, by_color):
    board = state.board
    for row in range(8):
        for col in range(8):
            piece = int(board[row, col])
            if piece == 0 or (1 if piece > 0 else -1) != by_color:
                continue

            piece_type = abs(piece)
            dr, dc = target_row - row, target_col - col

            if piece_type == 1:
                direction = 1 if piece > 0 else -1
                if dr == direction and abs(dc) == 1:
                    return True
            elif piece_type == 2:
                if (abs(dr), abs(dc)) in ((1, 2), (2, 1)):
                    return True
            elif piece_type == 6:
                if max(abs(dr), abs(dc)) == 1:
                    return True
            else:
                diagonal = abs(dr) == abs(dc) and dr != 0
                straight = (dr == 0) != (dc == 0)
                if piece_type == 3 and not diagonal:
                    continue
                if piece_type == 4 and not straight:
                    continue
                if piece_type == 5 and not (diagonal or straight):
                    continue

                step_row = (dr > 0) - (dr < 0)
                step_col = (dc > 0) - (dc < 0)
                check_row, check_col = row + step_row, col + step_col
                blocked = False
                while (check_row, check_col) != (target_row, target_col):
                    if board[check_row, check_col] != 0:
                        blocked = True
                        break
                    check_row += step_row
                    check_col += step_col
                if not blocked:
                    return True
    return False


def is_in_check(state, color):
    king_positions = (state.board == color * 6).nonzero()
    if len(king_positions[0]) == 0:
        return True
    king_row, king_col = int(king_positions[0][0]), int(king_positions[1][0])
    return is_square_attacked(state, king_row, king_col, -color)


def valid_moves(state, row, col):
    """Return pseudo-legal destinations for the piece on row, col."""
    if not (0 <= row < 8 and 0 <= col < 8):
        return []
    board = state.board
    piece = int(board[row, col])
    if piece == 0:
        return []

    piece_type = abs(piece)
    side = 1 if piece > 0 else -1
    moves = []

    def add_step(new_row, new_col):
        if add_if_valid_move(state, row, col, new_row, new_col):
            moves.append((new_row, new_col))

    def add_sliding(directions):
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            while 0 <= new_row < 8 and 0 <= new_col < 8:
                target = int(board[new_row, new_col])
                if target == 0:
                    moves.append((new_row, new_col))
                else:
                    if piece * target < 0:
                        moves.append((new_row, new_col))
                    break
                new_row += dr
                new_col += dc

    if piece_type == 1:
        direction = 1 if side == 1 else -1
        start_row = 1 if side == 1 else 6
        next_row = row + direction
        if 0 <= next_row < 8 and board[next_row, col] == 0:
            moves.append((next_row, col))
            two_rows = row + 2 * direction
            if row == start_row and board[two_rows, col] == 0:
                moves.append((two_rows, col))

        for dc in (-1, 1):
            new_row, new_col = row + direction, col + dc
            if (0 <= new_row < 8 and 0 <= new_col < 8
                    and piece * int(board[new_row, new_col]) < 0):
                moves.append((new_row, new_col))

        if state.last_move is not None:
            from_row, from_col, to_row, to_col = state.last_move
            if (
                abs(int(board[to_row, to_col])) == 1
                and int(board[to_row, to_col]) == -side
                and abs(to_row - from_row) == 2
                and from_col == to_col
                and from_row == (6 if side == 1 else 1)
                and to_row == row
                and abs(to_col - col) == 1
                and 0 <= next_row < 8
                and board[next_row, to_col] == 0
            ):
                moves.append((next_row, to_col))

    elif piece_type == 2:
        for dr, dc in (
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1),
        ):
            add_step(row + dr, col + dc)
    elif piece_type == 3:
        add_sliding([(-1, -1), (-1, 1), (1, -1), (1, 1)])
    elif piece_type == 4:
        add_sliding([(-1, 0), (1, 0), (0, -1), (0, 1)])
    elif piece_type == 5:
        add_sliding([
            (-1, -1), (-1, 1), (1, -1), (1, 1),
            (-1, 0), (1, 0), (0, -1), (0, 1),
        ])
    elif piece_type == 6:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr != 0 or dc != 0:
                    add_step(row + dr, col + dc)

        home_row = 0 if side == 1 else 7
        if row == home_row and col == 4:
            for castle_side, rook_col, king_to_col, empty_cols, safe_cols in (
                ("kingside", 7, 6, (5, 6), (4, 5, 6)),
                ("queenside", 0, 2, (1, 2, 3), (4, 3, 2)),
            ):
                right_key = ("white_" if side == 1 else "black_") + castle_side
                if not state.castling_rights.get(right_key, False):
                    continue
                if int(board[home_row, rook_col]) != side * 4:
                    continue
                if any(board[home_row, c] != 0 for c in empty_cols):
                    continue
                if any(is_square_attacked(state, home_row, c, -side) for c in safe_cols):
                    continue
                moves.append((home_row, king_to_col))

    return moves


def legal_moves_for_piece(state, row, col):
    piece = int(state.board[row, col])
    if piece == 0 or piece * state.turn <= 0:
        return []
    side = 1 if piece > 0 else -1
    legal = []
    for new_row, new_col in valid_moves(state, row, col):
        if abs(int(state.board[new_row, new_col])) == 6:
            continue
        child = state.copy()
        apply_move(child, (row, col, new_row, new_col), validate=False)
        if not is_in_check(child, side):
            legal.append((new_row, new_col))
    return legal


def all_legal_moves(state):
    moves = []
    for row in range(8):
        for col in range(8):
            if int(state.board[row, col]) * state.turn > 0:
                for new_row, new_col in legal_moves_for_piece(state, row, col):
                    moves.append((row, col, new_row, new_col))
    return moves


def apply_move(state, move, promotion=5, validate=True):
    """Apply a (from_row, from_col, to_row, to_col) move to state."""
    from_row, from_col, to_row, to_col = move
    board = state.board
    if not (0 <= from_row < 8 and 0 <= from_col < 8
            and 0 <= to_row < 8 and 0 <= to_col < 8):
        raise ValueError("Move square is outside the board.")

    piece = int(board[from_row, from_col])
    if piece == 0:
        raise ValueError("The starting square is empty.")
    if piece * state.turn <= 0:
        raise ValueError("That piece does not belong to the side to move.")
    if validate and (to_row, to_col) not in legal_moves_for_piece(state, from_row, from_col):
        raise ValueError("That move is not legal in this position.")

    side = 1 if piece > 0 else -1
    captured_piece = int(board[to_row, to_col])
    is_promotion = abs(piece) == 1 and to_row in (0, 7)
    if is_promotion and promotion not in (2, 3, 4, 5):
        raise ValueError("Promotion must be 2 (knight), 3 (bishop), 4 (rook), or 5 (queen).")

    color = "white" if side == 1 else "black"
    home_row = 0 if side == 1 else 7
    if abs(piece) == 6:
        state.castling_rights[f"{color}_kingside"] = False
        state.castling_rights[f"{color}_queenside"] = False
    elif abs(piece) == 4 and from_row == home_row:
        if from_col == 0:
            state.castling_rights[f"{color}_queenside"] = False
        elif from_col == 7:
            state.castling_rights[f"{color}_kingside"] = False

    if abs(captured_piece) == 4:
        captured_color = "white" if captured_piece > 0 else "black"
        captured_home_row = 0 if captured_piece > 0 else 7
        if to_row == captured_home_row:
            if to_col == 0:
                state.castling_rights[f"{captured_color}_queenside"] = False
            elif to_col == 7:
                state.castling_rights[f"{captured_color}_kingside"] = False

    direction = 1 if side == 1 else -1
    if abs(piece) == 1 and from_col != to_col and captured_piece == 0:
        board[to_row - direction, to_col] = 0

    if abs(piece) == 6 and abs(to_col - from_col) == 2:
        rook_from_col, rook_to_col = (7, 5) if to_col > from_col else (0, 3)
        board[from_row, rook_to_col] = board[from_row, rook_from_col]
        board[from_row, rook_from_col] = 0

    board[to_row, to_col] = piece
    board[from_row, from_col] = 0
    if is_promotion:
        board[to_row, to_col] = side * promotion

    state.last_move = move
    state.turn *= -1
    return state


def game_status(state):
    """Return 'playing', 'checkmate', or 'stalemate'."""
    if all_legal_moves(state):
        return "playing"
    return "checkmate" if is_in_check(state, state.turn) else "stalemate"
