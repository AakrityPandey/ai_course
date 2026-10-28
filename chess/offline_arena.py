"""Local matches using the same CourseMinimax search as the Lichess bot."""
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import random
import sys
import time

import chess
import chess.engine
import chess.pgn

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lichess-bot'))
from course_lichess_engine import choose_move

DEFAULT_OPPONENTS = ['random', 'sunfish', 'stockfish_0', 'stockfish_5', 'stockfish_10']


def open_opponent(name):
    if name == 'random':
        return None
    if name == 'sunfish':
        command = [sys.executable, '-u', str(ROOT / 'offline_engines/sunfish/sunfish.py')]
    elif name.startswith('stockfish_'):
        files = list((ROOT / 'offline_engines/stockfish').rglob('*.exe'))
        if not files:
            raise FileNotFoundError('Stockfish is missing from offline_engines/stockfish.')
        command = str(files[0])
    else:
        raise ValueError('Unknown opponent: ' + name)
    engine = chess.engine.SimpleEngine.popen_uci(command, timeout=15)
    try:
        if name.startswith('stockfish_'):
            engine.configure({'Threads': 1, 'Hash': 32, 'Skill Level': int(name.split('_')[1])})
    except Exception:
        engine.quit()
        raise
    return engine


def opening(seed, plies=4):
    rng = random.Random(seed)
    board = chess.Board()
    moves = []
    for _ in range(plies):
        if board.is_game_over():
            break
        move = rng.choice(list(board.legal_moves))
        moves.append(move)
        board.push(move)
    return moves


def play_game(opponent, engine, our_color, opening_moves, initial_seconds, increment, depth, max_plies, seed):
    rng = random.Random(seed)
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers['White'] = 'CourseMinimax' if our_color else opponent
    game.headers['Black'] = opponent if our_color else 'CourseMinimax'
    game.headers['Event'] = 'Offline course benchmark'
    game.headers['Date'] = datetime.now().strftime('%Y.%m.%d')
    game.headers['TimeControl'] = '{}+{}'.format(initial_seconds, increment)
    clocks = {chess.WHITE: float(initial_seconds), chess.BLACK: float(initial_seconds)}
    flagged = None
    node = game
    for move in opening_moves:
        board.push(move)
        node = node.add_variation(move)
    elapsed, our_moves = 0.0, 0
    error = ''
    try:
        while not board.is_game_over(claim_draw=True) and len(board.move_stack) < max_plies:
            side = board.turn
            limit = chess.engine.Limit(white_clock=clocks[chess.WHITE],
                                       black_clock=clocks[chess.BLACK],
                                       white_inc=increment, black_inc=increment)
            start = time.monotonic()
            try:
                if side == our_color:
                    move, _ = choose_move(board, limit, max_depth=depth)
                    our_moves += 1
                elif engine is None:
                    move = rng.choice(list(board.legal_moves))
                else:
                    engine.timeout = clocks[side] + 0.1
                    move = engine.play(board, limit, game=game).move
            except TimeoutError:
                flagged = side
                clocks[side] = 0.0
                break
            spent = time.monotonic() - start
            clocks[side] -= spent
            if side == our_color:
                elapsed += spent
            if clocks[side] <= 0:
                flagged = side
                clocks[side] = 0.0
                break
            if move not in board.legal_moves:
                raise ValueError('Engine returned an illegal move: ' + str(move))
            board.push(move)
            clocks[side] += increment
            node = node.add_variation(move)
            node.set_clock(clocks[side])
    except Exception as exc:
        error = '{}: {}'.format(type(exc).__name__, exc)
    outcome = board.outcome(claim_draw=True)
    if error:
        result, status, score = '*', 'error', None
    elif flagged is not None:
        winner = not flagged
        if board.has_insufficient_material(winner):
            result, status, score = '1/2-1/2', 'timeout_insufficient_material', 0.5
        else:
            result = '1-0' if winner == chess.WHITE else '0-1'
            status, score = 'timeout', float(winner == our_color)
    elif outcome is None:
        result, status, score = '*', 'move_limit', None
    else:
        result = outcome.result()
        status = outcome.termination.name.lower()
        score = 0.5 if outcome.winner is None else float(outcome.winner == our_color)
    game.headers['Result'] = result
    game.headers['Termination'] = status
    node.comment = error or status
    return game, {'opponent': opponent, 'color': 'white' if our_color else 'black',
                  'result': result, 'score': score, 'status': status,
                  'plies': len(board.move_stack), 'our_moves': our_moves,
                  'our_seconds': round(elapsed, 4),
                  'white_clock': round(clocks[chess.WHITE], 3),
                  'black_clock': round(clocks[chess.BLACK], 3), 'error': error}


def summarize(rows):
    summary = []
    for opponent in dict.fromkeys(row['opponent'] for row in rows):
        games = [r for r in rows if r['opponent'] == opponent]
        finished = [r for r in games if r['score'] is not None]
        wins = sum(r['score'] == 1 for r in finished)
        draws = sum(r['score'] == 0.5 for r in finished)
        losses = sum(r['score'] == 0 for r in finished)
        summary.append({'opponent': opponent, 'games': len(games), 'wins': wins,
                        'draws': draws, 'losses': losses,
                        'unfinished': sum(r['status'] == 'move_limit' for r in games),
                        'errors': sum(r['status'] == 'error' for r in games),
                        'score_pct': round(100 * (wins + draws / 2) / len(finished), 1) if finished else None})
    return summary


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_benchmark(opponents=None, pairs=1, initial_seconds=300, increment=0, depth=3, max_plies=200, seed=42):
    """Each pair plays the same seeded opening with colors reversed."""
    opponents = list(DEFAULT_OPPONENTS if opponents is None else opponents)
    if not opponents or pairs < 1 or initial_seconds <= 0 or increment < 0 or depth < 1 or max_plies < 5:
        raise ValueError('Choose opponents and positive settings; max_plies must be at least 5.')
    output = ROOT / 'offline_results' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    output.mkdir(parents=True)
    metadata = {'opponents': opponents, 'pairs': pairs, 'initial_seconds': initial_seconds, 'increment': increment,
                'depth': depth, 'max_plies': max_plies, 'seed': seed,
                'course_search_sha256': hashlib.sha256((ROOT / 'course_lichess_engine.py').read_bytes()).hexdigest(),
                'note': 'Engine skill levels are not human Elo ratings. Move-limit games are unfinished.'}
    (output / 'settings.json').write_text(json.dumps(metadata, indent=2))
    rows = []
    for opponent in opponents:
        engine = open_opponent(opponent)
        try:
            for pair in range(pairs):
                moves = opening(seed + pair)
                for color in (chess.WHITE, chess.BLACK):
                    if engine is not None:
                        # Reset opponent hash/state between games.
                        engine.configure({'Clear Hash': None} if 'Clear Hash' in engine.options else {})
                    game, row = play_game(opponent, engine, color, moves,
                                          initial_seconds, increment, depth, max_plies, seed + pair)
                    index = len(rows) + 1
                    filename = '{:03d}_{}_{}.pgn'.format(index, opponent, row['color'])
                    (output / filename).write_text(str(game) + '\n', encoding='utf-8')
                    row['pgn'] = filename
                    rows.append(row)
                    write_csv(output / 'games.csv', rows)
                    write_csv(output / 'summary.csv', summarize(rows))
                    print('{} as {}: {} ({})'.format(opponent, row['color'], row['result'], row['status']), flush=True)
        finally:
            if engine is not None:
                engine.quit()
    summary = summarize(rows)
    print('\nSaved results:', output)
    return summary, output
