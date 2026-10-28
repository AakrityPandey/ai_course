"""Importable process entry point for notebook-safe AI searches."""

from .players import Player


def choose_move_in_process(connection, state, mode, depth):
    try:
        move = Player(mode=mode, depth=depth).choose_move(state)
        connection.send((True, move))
    except Exception as error:
        connection.send((False, "{}: {}".format(type(error).__name__, error)))
    finally:
        connection.close()
