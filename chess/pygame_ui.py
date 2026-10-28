"""Pygame interface for the modular chess engine."""

from chess_engine import apply_move, game_status, legal_moves_for_piece
from chess_engine.rules import is_in_check
from chess_engine.worker import choose_move_in_process
import multiprocessing


class PygameChessUI:
    BOARD_SIZE = 640
    SQUARE_SIZE = 80
    BOARD_LEFT = 44
    BOARD_TOP = 52
    WINDOW_WIDTH = 728
    WINDOW_HEIGHT = 748

    LIGHT_SQUARE = (238, 238, 210)
    DARK_SQUARE = (118, 150, 86)
    BACKGROUND = (35, 38, 39)
    TEXT_COLOR = (245, 245, 240)
    SELECTED = (245, 205, 66)
    LAST_MOVE = (205, 210, 106)
    LEGAL_MOVE = (55, 125, 76)
    CAPTURE = (190, 65, 65)
    WHITE_PIECE = (249, 247, 239)
    BLACK_PIECE = (35, 37, 38)

    def __init__(self, state, players):
        self.state = state
        self.players = players
        self.selected_square = None
        self.legal_targets = []
        self.last_ui_move = None
        self._last_ai_move_time = 0
        self._ai_process = None
        self._ai_connection = None
        self._ai_error = None
        self._piece_icons = {}

    def run(self):
        try:
            import pygame
        except ImportError as error:
            raise ImportError(
                "Pygame is needed to display the chess window. In a notebook cell, "
                "run %pip install pygame, restart the kernel, and rerun the notebook."
            ) from error

        pygame.init()
        screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption("Chess")
        clock = pygame.time.Clock()
        label_font = pygame.font.SysFont("Arial", 20, bold=True)
        status_font = pygame.font.SysFont("Arial", 21)
        running = True

        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        self._handle_click(event.pos, pygame)

                if not running:
                    break
                self._play_automatic_turn(pygame)
                self._draw(screen, pygame, label_font, status_font)
                pygame.display.flip()
                clock.tick(30)
        finally:
            self._stop_ai()
            pygame.quit()

        return self.state

    def _handle_click(self, position, pygame):
        if game_status(self.state) != "playing":
            return
        _, player = self.players[self.state.turn]
        if player.mode != "manual":
            return

        x, y = position
        board_x = x - self.BOARD_LEFT
        board_y = y - self.BOARD_TOP
        if not (0 <= board_x < self.BOARD_SIZE and 0 <= board_y < self.BOARD_SIZE):
            return

        col = board_x // self.SQUARE_SIZE
        row = 7 - board_y // self.SQUARE_SIZE
        piece = int(self.state.board[row, col])

        if self.selected_square is None:
            if piece * self.state.turn > 0:
                self._select(row, col)
            return

        if (row, col) in self.legal_targets:
            move = (*self.selected_square, row, col)
            self._apply(move)
            return

        if piece * self.state.turn > 0:
            self._select(row, col)
        else:
            self.selected_square = None
            self.legal_targets = []

    def _select(self, row, col):
        self.selected_square = (row, col)
        self.legal_targets = legal_moves_for_piece(self.state, row, col)

    def _apply(self, move):
        apply_move(self.state, move)
        self.last_ui_move = move
        self.selected_square = None
        self.legal_targets = []

    def _play_automatic_turn(self, pygame):
        if self._ai_connection is not None:
            if self._ai_connection.poll():
                try:
                    success, result = self._ai_connection.recv()
                except EOFError:
                    success, result = False, "AI process exited without a move."
                if success == "branch":
                    print("  {}  immediate={:+g}  minimax(depth {})={:+g}".format(
                        self._move_label(result["move"]), result["immediate"],
                        result["depth"], result["score"]), flush=True)
                    return
                self._stop_ai()
                if success:
                    if result is not None:
                        print("Selected: {}\n".format(self._move_label(result)), flush=True)
                        self._apply(result)
                    self._last_ai_move_time = pygame.time.get_ticks()
                else:
                    self._ai_error = str(result)
                    print("AI search failed:", result)
            elif not self._ai_process.is_alive():
                self._stop_ai()
                self._ai_error = "AI process exited unexpectedly."
            return

        if self._ai_error:
            return
        if game_status(self.state) != "playing":
            return

        _, player = self.players[self.state.turn]
        if player.mode == "manual":
            return

        now = pygame.time.get_ticks()
        if now - self._last_ai_move_time < 350:
            return

        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(
            target=choose_move_in_process,
            args=(sender, self.state.copy(), player.mode, player.depth),
            daemon=True,
        )
        try:
            process.start()
        except Exception:
            receiver.close()
            sender.close()
            raise
        sender.close()
        self._ai_connection = receiver
        self._ai_process = process

    @staticmethod
    def _move_label(move):
        row, col, target_row, target_col = move
        return "{}{} -> {}{}".format(
            "abcdefgh"[col], row + 1, "abcdefgh"[target_col], target_row + 1)

    def _stop_ai(self):
        if self._ai_process is not None:
            self._ai_process.join(timeout=0.05)
            if self._ai_process.is_alive():
                self._ai_process.terminate()
                self._ai_process.join()
            self._ai_process.close()
            self._ai_process = None
        if self._ai_connection is not None:
            self._ai_connection.close()
            self._ai_connection = None

    def _draw(self, screen, pygame, label_font, status_font):
        screen.fill(self.BACKGROUND)

        for row in range(8):
            for col in range(8):
                x = self.BOARD_LEFT + col * self.SQUARE_SIZE
                y = self.BOARD_TOP + (7 - row) * self.SQUARE_SIZE
                rect = pygame.Rect(x, y, self.SQUARE_SIZE, self.SQUARE_SIZE)
                color = self.LIGHT_SQUARE if (row + col) % 2 == 0 else self.DARK_SQUARE
                if self.last_ui_move and (row, col) in (
                    (self.last_ui_move[0], self.last_ui_move[1]),
                    (self.last_ui_move[2], self.last_ui_move[3]),
                ):
                    color = self.LAST_MOVE
                if (row, col) == self.selected_square:
                    color = self.SELECTED
                pygame.draw.rect(screen, color, rect)

                if (row, col) in self.legal_targets:
                    if int(self.state.board[row, col]) == 0:
                        pygame.draw.circle(
                            screen,
                            self.LEGAL_MOVE,
                            rect.center,
                            self.SQUARE_SIZE // 9,
                        )
                    else:
                        pygame.draw.rect(screen, self.CAPTURE, rect, width=5)

                piece = int(self.state.board[row, col])
                if piece:
                    self._draw_piece(screen, pygame, rect, piece)

        for col, file_name in enumerate("abcdefgh"):
            x = self.BOARD_LEFT + col * self.SQUARE_SIZE + self.SQUARE_SIZE // 2
            file_surface = label_font.render(file_name, True, self.TEXT_COLOR)
            screen.blit(file_surface, file_surface.get_rect(center=(x, 28)))

        for row in range(8):
            rank = str(row + 1)
            y = self.BOARD_TOP + (7 - row) * self.SQUARE_SIZE + self.SQUARE_SIZE // 2
            rank_surface = label_font.render(rank, True, self.TEXT_COLOR)
            screen.blit(rank_surface, rank_surface.get_rect(center=(24, y)))

        status = self._status_text()
        status_surface = status_font.render(status, True, self.TEXT_COLOR)
        screen.blit(status_surface, (self.BOARD_LEFT, self.BOARD_TOP + self.BOARD_SIZE + 20))

    def _draw_piece(self, screen, pygame, rect, piece):
        from piece_icons import make_piece_icon

        key = (int(piece), rect.width)
        if key not in self._piece_icons:
            self._piece_icons[key] = make_piece_icon(pygame, *key)
        screen.blit(self._piece_icons[key], rect)

    def _status_text(self):
        if self._ai_error:
            return "AI error — see notebook output"
        status = game_status(self.state)
        if status == "checkmate":
            winner = "Black" if self.state.turn == 1 else "White"
            return "Checkmate — {} wins".format(winner)
        if status == "stalemate":
            return "Stalemate"

        player_name, player = self.players[self.state.turn]
        color = "White" if self.state.turn == 1 else "Black"
        message = "{} to move — {} ({})".format(color, player_name, player.mode)
        if self._ai_process is not None:
            message += " — thinking..."
        if is_in_check(self.state, self.state.turn):
            message += " — check"
        return message
