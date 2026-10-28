"""Load the bundled Cburnett SVG chess pieces without network access."""
from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "pieces" / "cburnett"
PIECE_NAMES = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}


def make_piece_icon(pygame, piece, size=80):
    color = "w" if piece > 0 else "b"
    path = ASSET_DIR / (color + PIECE_NAMES[abs(piece)] + ".svg")
    # Rasterize above display resolution, then downsample for smooth edges.
    icon = pygame.image.load_sized_svg(str(path), (size * 3, size * 3))
    return pygame.transform.smoothscale(icon, (size, size))
