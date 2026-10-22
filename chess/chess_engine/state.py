from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np


@dataclass
class BoardState:
    """Chess position plus the state required to continue the game.

    White pieces are positive, black pieces are negative, and empty squares are 0.
    White starts on row 0 and moves toward higher row numbers.
    """

    board: np.ndarray
    turn: int = 1
    last_move: Optional[Tuple[int, int, int, int]] = None
    castling_rights: dict = field(default_factory=lambda: {
        "white_kingside": True,
        "white_queenside": True,
        "black_kingside": True,
        "black_queenside": True,
    })

    def copy(self):
        """Return an independent state for move search."""
        return BoardState(
            board=self.board.copy(),
            turn=self.turn,
            last_move=self.last_move,
            castling_rights=self.castling_rights.copy(),
        )

    @classmethod
    def initial(cls, turn=1):
        board = np.zeros((8, 8), dtype=np.int8)
        board[0] = [4, 2, 3, 5, 6, 3, 2, 4]
        board[1] = 1
        board[6] = -1
        board[7] = -board[0]
        return cls(board=board, turn=turn)
