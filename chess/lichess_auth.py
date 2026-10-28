"""Load a local Lichess token without logging it."""
import getpass
import os
from pathlib import Path

TOKEN_FILE = Path(__file__).resolve().parent / 'lichess.token'


def load_token():
    token = os.environ.get('LICHESS_BOT_TOKEN', '').strip()
    if not token and TOKEN_FILE.is_file():
        token = TOKEN_FILE.read_text(encoding='utf-8-sig').strip()
    if not token:
        token = getpass.getpass('Lichess BOT API token (hidden): ').strip()
    if not token:
        raise SystemExit('No token supplied.')
    if any(character.isspace() for character in token):
        raise SystemExit('The token must be a single value without spaces or line breaks.')
    return token
