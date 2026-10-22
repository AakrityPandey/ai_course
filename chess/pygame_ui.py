"""Pygame interface for the modular chess engine."""

from chess_engine import apply_move, game_status, legal_moves_for_piece
from chess_engine.rules import is_in_check


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

                self._play_automatic_turn(pygame)
                self._draw(screen, pygame, label_font, status_font)
                pygame.display.flip()
                clock.tick(30)
        finally:
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
        if game_status(self.state) != "playing":
            return

        _, player = self.players[self.state.turn]
        if player.mode == "manual":
            return

        now = pygame.time.get_ticks()
        if now - self._last_ai_move_time < 350:
            return

        move = player.choose_move(self.state)
        if move is not None:
            self._apply(move)
        self._last_ai_move_time = now

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
        white_piece = piece > 0
        fill = self.WHITE_PIECE if white_piece else self.BLACK_PIECE
        outline = self.BLACK_PIECE if white_piece else self.WHITE_PIECE
        x, y = rect.center
        piece_type = abs(piece)

        def polygon(points):
            points = [(x + dx, y + dy) for dx, dy in points]
            pygame.draw.polygon(screen, fill, points)
            pygame.draw.polygon(screen, outline, points, width=2)

        # Shared foot gives every silhouette a stable chess-piece shape.
        pygame.draw.ellipse(screen, fill, (x - 22, y + 17, 44, 10))
        pygame.draw.ellipse(screen, outline, (x - 22, y + 17, 44, 10), width=2)
        polygon([(-17, 15), (17, 15), (12, 8), (-12, 8)])

        if piece_type == 1:  # pawn
            polygon([(-4, 4), (4, 4), (11, 11), (-11, 11)])
            pygame.draw.circle(screen, fill, (x, y - 10), 9)
            pygame.draw.circle(screen, outline, (x, y - 10), 9, width=2)
        elif piece_type == 2:  # knight
            polygon([
                (-15, 10), (-13, -4), (-6, -17), (1, -23), (13, -20),
                (8, -12), (16, -5), (15, 10),
            ])
            pygame.draw.circle(screen, outline, (x + 5, y - 15), 2)
        elif piece_type == 3:  # bishop
            polygon([(-12, 10), (-8, -3), (-3, -11), (-7, -17), (0, -24),
                     (7, -17), (3, -11), (8, -3), (12, 10)])
            pygame.draw.line(screen, outline, (x - 4, y - 17), (x + 4, y - 9), 2)
        elif piece_type == 4:  # rook
            pygame.draw.rect(screen, fill, (x - 14, y - 16, 28, 29))
            pygame.draw.rect(screen, outline, (x - 14, y - 16, 28, 29), width=2)
            for dx in (-14, -4, 6):
                pygame.draw.rect(screen, fill, (x + dx, y - 24, 8, 9))
                pygame.draw.rect(screen, outline, (x + dx, y - 24, 8, 9), width=2)
        elif piece_type == 5:  # queen
            polygon([(-15, 9), (-11, -8), (-6, 1), (0, -15), (6, 1),
                     (12, -8), (15, 9)])
            for dx, dy in ((-11, -9), (0, -17), (12, -9)):
                pygame.draw.circle(screen, fill, (x + dx, y + dy), 4)
                pygame.draw.circle(screen, outline, (x + dx, y + dy), 4, width=2)
        else:  # king
            polygon([(-12, 10), (-8, -5), (-4, -12), (4, -12), (8, -5), (12, 10)])
            pygame.draw.rect(screen, fill, (x - 3, y - 28, 6, 19))
            pygame.draw.rect(screen, outline, (x - 3, y - 28, 6, 19), width=1)
            pygame.draw.rect(screen, fill, (x - 10, y - 23, 20, 6))
            pygame.draw.rect(screen, outline, (x - 10, y - 23, 20, 6), width=1)

    def _status_text(self):
        status = game_status(self.state)
        if status == "checkmate":
            winner = "Black" if self.state.turn == 1 else "White"
            return "Checkmate — {} wins".format(winner)
        if status == "stalemate":
            return "Stalemate"

        player_name, player = self.players[self.state.turn]
        color = "White" if self.state.turn == 1 else "Black"
        message = "{} to move — {} ({})".format(color, player_name, player.mode)
        if is_in_check(self.state, self.state.turn):
            message += " — check"
        return message
