"""Offline integration checks; does not contact Lichess or require a token."""
import sys
from pathlib import Path
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / 'lichess-bot'))
import chess
from chess.engine import Limit
from course_lichess_engine import choose_move, minimax, MATE_SCORE


class OnlineEngineTests(unittest.TestCase):
    def test_opening_restores_board(self):
        board = chess.Board()
        before = board.fen()
        move, depth = choose_move(board, Limit(time=2), max_depth=2)
        self.assertIn(move, board.legal_moves)
        self.assertGreaterEqual(depth, 1)
        self.assertEqual(board.fen(), before)
        self.assertEqual(board.move_stack, [])

    def test_zero_clock_has_legal_fallback(self):
        board = chess.Board()
        start = time.monotonic()
        move, depth = choose_move(board, Limit(time=0), max_depth=10)
        self.assertIn(move, board.legal_moves)
        self.assertEqual(depth, 0)
        self.assertLess(time.monotonic() - start, 0.5)
        self.assertEqual(board.move_stack, [])

    def test_both_colors_take_free_queen(self):
        for fen, expected in [
            ('4k3/8/8/8/8/8/q7/R3K3 w - - 0 1', 'a1a2'),
            ('r3k3/Q7/8/8/8/8/8/4K3 b - - 0 1', 'a8a7'),
        ]:
            board = chess.Board(fen)
            move, _ = choose_move(board, Limit(time=5), max_depth=1)
            self.assertEqual(move.uci(), expected)

    def test_special_moves_and_root_restrictions(self):
        for fen, uci in [
            ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', 'e1g1'),
            ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6'),
            ('4k3/P7/8/8/8/8/8/4K3 w - - 0 1', 'a7a8n'),
        ]:
            board = chess.Board(fen)
            forced = chess.Move.from_uci(uci)
            before = board.fen()
            move, _ = choose_move(board, Limit(time=5), max_depth=1, root_moves=[forced])
            self.assertEqual(move, forced)
            self.assertEqual(board.fen(), before)

    def test_mate_and_stalemate(self):
        for fen, expected in [
            ('7k/6Q1/6K1/8/8/8/8/8 b - - 0 1', MATE_SCORE),
            ('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1', 0),
        ]:
            board = chess.Board(fen)
            self.assertEqual(minimax(board, 2, -float('inf'), float('inf'), time.monotonic()+1), expected)
            self.assertIsNone(choose_move(board, Limit(time=1))[0])


if __name__ == '__main__':
    unittest.main()
