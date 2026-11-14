import signal


def run_solver_with_timeout(solver, input_string, time_out=-1):
    if time_out <= 0:
        solver.search(input_string)
        return

    if not hasattr(signal, 'setitimer'):
        from wrapt_timeout_decorator import timeout
        timeout(time_out)(solver.search)(input_string)
        return

    def expire(signum, frame):
        raise TimeoutError()

    previous_handler = signal.signal(signal.SIGALRM, expire)
    try:
        signal.setitimer(signal.ITIMER_REAL, time_out)
        solver.search(input_string)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
