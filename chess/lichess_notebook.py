"""Notebook controls for the Lichess connector, with output saved to a log."""
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
LOG = ROOT / 'lichess_bot.log'
_process = None


def start_bot():
    global _process
    if _process is not None and _process.poll() is None:
        print('Bot is already running.')
        return
    # A notebook cannot answer a hidden subprocess prompt.
    if not os.environ.get('LICHESS_BOT_TOKEN', '').strip():
        token_file = ROOT / 'lichess.token'
        if not token_file.exists() or not token_file.read_text(encoding='utf-8-sig').strip():
            raise RuntimeError('Save your token in chess/lichess.token first.')
    with LOG.open('w', encoding='utf-8') as output:
        _process = subprocess.Popen(
            [sys.executable, '-u', str(ROOT / 'start_lichess.py')],
            cwd=str(ROOT), stdout=output, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
    time.sleep(1)
    if _process.poll() is not None:
        raise RuntimeError('Bot stopped during startup. Run bot_status() for details.')
    print('Bot process started. Run bot_status() to check connection; logs are in lichess_bot.log.')


def bot_status(lines=15):
    running = _process is not None and _process.poll() is None
    print('Notebook bot process:', 'running' if running else 'stopped')
    if LOG.exists():
        print('\n'.join(LOG.read_text(encoding='utf-8', errors='replace').splitlines()[-lines:]))


def challenge_bot(username):
    if not username.strip() or username == 'BOT_USERNAME':
        raise ValueError('Replace BOT_USERNAME with an online Lichess bot username.')
    # Token file/environment is used automatically by the same helper as the CLI.
    from lichess_auth import load_token
    env = os.environ.copy()
    env['LICHESS_BOT_TOKEN'] = load_token()
    result = subprocess.run(
        [sys.executable, str(ROOT / 'challenge_bot.py'), username.strip()],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=75,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
    )
    details = '\n'.join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode:
        raise RuntimeError('Challenge failed:\n' + (details or 'No error details returned.'))
    print(details)


def stop_bot():
    global _process
    if _process is None or _process.poll() is not None:
        print('Notebook bot is already stopped.')
        return
    # Stop the connector and its worker children; do this after a game finishes.
    import psutil
    try:
        parent = psutil.Process(_process.pid)
        children = parent.children(recursive=True)
        for process in children:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        parent.terminate()
        _, alive = psutil.wait_procs(children + [parent], timeout=3)
        for process in alive:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
        _process.wait(timeout=5)
    except psutil.NoSuchProcess:
        pass
    print('Notebook bot stopped.')
