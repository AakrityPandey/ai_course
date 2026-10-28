"""Prepare and run lichess-bot with our engine. --check never connects online."""
import argparse
import os
from pathlib import Path
import runpy
import sys
from lichess_auth import load_token

ROOT = Path(__file__).resolve().parent
CONNECTOR = ROOT / 'lichess-bot'


def merge(base, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge(base[key], value)
        else:
            base[key] = value
    return base


def prepare():
    import yaml
    if not (CONNECTOR / 'lichess-bot.py').is_file():
        raise SystemExit('Connector missing. See LICHESS_SETUP.md for installation.')
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(CONNECTOR))
    config = merge(yaml.safe_load((CONNECTOR / 'config.yml.default').read_text()),
                   yaml.safe_load((ROOT / 'lichess_config.yml').read_text()))
    (CONNECTOR / 'config.yml').write_text(yaml.safe_dump(config, sort_keys=False))
    homemade = CONNECTOR / 'homemade.py'
    source = homemade.read_text(encoding='utf-8')
    registration = '\nfrom course_lichess_engine import CourseMinimax\n'
    if registration.strip() not in source:
        homemade.write_text(source + registration, encoding='utf-8')
    os.chdir(CONNECTOR)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate locally; no account needed.')
    parser.add_argument('--upgrade', action='store_true', help='Convert a fresh account to BOT, then run.')
    args = parser.parse_args()
    prepare()
    if args.check:
        from lib.config import load_config
        from lib.engine_wrapper import create_engine
        import chess
        from chess.engine import Limit
        config = load_config('config.yml')
        with create_engine(config) as engine:
            board = chess.Board()
            result = engine.search(board, Limit(time=0.2), False, False, None)
            assert result.move in board.legal_moves
        print('PASS: connector configuration and engine work offline.')
        return
    os.environ['LICHESS_BOT_TOKEN'] = load_token()
    sys.argv = ['lichess-bot.py', '--config', 'config.yml', '--disable_auto_logging']
    if args.upgrade:
        sys.argv.append('-u')
    runpy.run_path(str(CONNECTOR / 'lichess-bot.py'), run_name='__main__')


if __name__ == '__main__':
    main()
