"""Persistent AI worker for local experiments, not the assignment runner."""

import multiprocessing as mp
from time import monotonic
import traceback


def _serve(player, connection):
    try:
        connection.send(("ready", mp.current_process().pid))
        while True:
            request = connection.recv()
            if request is None:
                return
            method, state = request
            try:
                if method not in ("get_expectimax_move", "get_intelligent_move"):
                    raise ValueError(f"Unsupported move method: {method}")
                action = getattr(player, method)(state)
                connection.send(("ok", action))
            except Exception:
                connection.send(("error", traceback.format_exc()))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class PersistentAIWorker:
    """Start once, wait for readiness, and enforce a deadline on each request.

    Startup is deliberately outside the move budget in this experimental runner.
    An overrun or crash stops this worker; the next request starts a fresh one.
    """

    def __init__(self, player, startup_timeout=15.0):
        self.player = player
        self.startup_timeout = startup_timeout
        self.process = None
        self.connection = None
        self.startup_seconds = 0.0
        self.last_move_seconds = 0.0
        self.start()

    def start(self):
        if self.process is not None and self.process.is_alive():
            return
        self.close()
        context = mp.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=_serve, args=(self.player, child))
        self.connection = parent
        self.process = process
        started = monotonic()
        try:
            process.start()
            child.close()
            if not parent.poll(self.startup_timeout):
                raise TimeoutError("AI worker did not finish starting")
            status, _ = parent.recv()
            if status != "ready":
                raise RuntimeError("AI worker did not report readiness")
            self.startup_seconds = monotonic() - started
        except BaseException:
            child.close()
            self.close(force=True)
            raise

    def choose(self, state, method, time_limit):
        self.start()
        connection = self.connection
        started = monotonic()
        try:
            connection.send((method, state))
            remaining = max(0.0, time_limit - (monotonic() - started))
            if not connection.poll(remaining):
                raise TimeoutError("Player Exceeded time limit")
            status, payload = connection.recv()
            if status != "ok":
                raise RuntimeError(f"AI worker failed:\n{payload}")
            if monotonic() - started > time_limit:
                raise TimeoutError("Player Exceeded time limit")
            return payload
        except BaseException:
            self.close(force=True)
            raise
        finally:
            self.last_move_seconds = monotonic() - started

    def close(self, force=False):
        process, connection = self.process, self.connection
        self.process = None
        self.connection = None
        if process is None:
            return
        try:
            if process.pid is not None:
                if process.is_alive() and not force:
                    try:
                        connection.send(None)
                    except (OSError, EOFError):
                        pass
                    process.join(0.2)
                if process.is_alive():
                    process.terminate()
                    process.join(0.5)
                if process.is_alive():
                    process.kill()
                    process.join(1)
                if process.is_alive():
                    raise RuntimeError("Could not stop AI worker")
                process.join()
        finally:
            if connection is not None:
                connection.close()
