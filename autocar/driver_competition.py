"""Isolated, deterministic driver comparisons without modifying simulator files."""
import argparse
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parent


@contextlib.contextmanager
def random_stream(rng):
    previous = random.getstate()
    random.setstate(rng.getstate())
    try:
        yield
    finally:
        rng.setstate(random.getstate())
        random.setstate(previous)


def simulate(board, driver_file, class_name, seed=1, cars=None, parked=False, seconds=120):
    """20 car updates/s; traffic and observations at 5 updates/s, no GUI sleeps."""
    import os
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    boards = json.loads((ROOT / 'test_boards.json').read_text())
    info = boards[board]
    cars = info['default_cars'] if cars is None else cars
    result = dict(board=board, driver=Path(driver_file).stem, seed=seed, cars=cars,
                  parked=parked, checkpoints_total=len(info['checkpoints']),
                  checkpoints_reached=0, checkpoint_times=[], completion_seconds=None,
                  status='error', elapsed_seconds=0.0, error=None)
    started = time.perf_counter()
    try:
        # Only rendering is replaced; car dynamics, collisions, inference and
        # checkpoint checks use the project's classes unchanged.
        display = types.ModuleType('engine.view.display')
        display.Display = type('HeadlessDisplay', (), {
            'COLORS': ['purple', 'green', 'teal', 'red', 'orange', 'blue'],
            'getKeys': staticmethod(lambda: []),
        })
        sys.modules['engine.view.display'] = display
        from engine.const import Const
        Const.WORLD = info['world']
        Const.CARS_PARKED = parked
        Const.NUM_AGENTS = cars
        Const.INFERENCE = 'estimator'
        Const.AUTO = Const.INTELLIGENT_DRIVER = Const.MULTIPLE_GOALS = True
        Const.NUM_CHECKPTS = len(info['checkpoints'])
        Const.COMPLETED_CHECKPTS = 0
        spec = importlib.util.spec_from_file_location('competition_candidate', driver_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        candidate = getattr(module, class_name, None)
        if candidate is None:
            result.update(status='not_implemented', error=f'No {class_name} class in {driver_file}')
            return result
        from engine.model import model as model_module
        from engine.model.layout import Layout
        traffic_rng = random.Random(seed)
        sensor_rng = random.Random(seed + 100000)
        driver_rng = random.Random(seed + 200000)

        class Candidate(candidate):
            def __init__(self, layout):
                with random_stream(driver_rng):
                    super().__init__(layout)

        model_module.IntelligentDriver = Candidate
        layout = Layout(Const.WORLD)
        spawn_count = len({tuple(n['pos']) for n in layout.data['agentGraph']['nodes']})
        if not 1 <= cars <= spawn_count:
            raise ValueError(f'cars must be between 1 and {spawn_count}')
        with random_stream(traffic_rng):
            model = model_module.Model(layout)
        beliefs = []
        with contextlib.redirect_stdout(io.StringIO()):
            for tick in range(int(seconds * 20)):
                if tick % 4 == 0:
                    beliefs = []
                    with random_stream(sensor_rng):
                        for car in model.getOtherCars():
                            observation = car.getObservation(model.junior)
                            inference = car.getInference()
                            inference.estimate(model.junior.pos.x, model.junior.pos.y,
                                               observation.getDist(), car.getParkedStatus())
                            beliefs.append(inference.getBelief())
                    with random_stream(traffic_rng):
                        for car in model.getOtherCars():
                            car.action()
                        for car in model.getOtherCars():
                            car.update()
                parked_flags = [car.getParkedStatus() for car in model.getOtherCars()]
                with random_stream(driver_rng):
                    model.junior.intelligent_autonomousAction(beliefs, parked_flags, model.nextCheckPtIdx)
                    model.junior.update()
                result['elapsed_seconds'] = (tick + 1) / 20
                if model.checkCollision(model.junior):
                    result['status'] = 'collision'
                    if hasattr(model.junior, 'collisionBeliefs'):
                        result['collision_beliefs'] = model.junior.collisionBeliefs(
                            beliefs, parked_flags)
                    break
                before = model.nextCheckPtIdx
                won = model._checkVictory()
                if model.nextCheckPtIdx > before:
                    result['checkpoint_times'].append(result['elapsed_seconds'])
                    result['checkpoints_reached'] = model.nextCheckPtIdx
                if won:
                    result.update(status='completed', completion_seconds=result['elapsed_seconds'])
                    break
            else:
                result['status'] = 'timeout'
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    finally:
        result['compute_seconds'] = round(time.perf_counter() - started, 4)
    return result


def run_suite(boards, drivers, seeds=(1,), cars=None, parked=False, seconds=120,
              python=sys.executable, wall_timeout=60, status_callback=None):
    """Run one child process per driver/board/seed, sequentially."""
    results = []
    try:
        for board in boards:
            for seed in seeds:
                for label, (filename, classname) in drivers.items():
                    game = f'{board} | seed {seed} | {label}'
                    print(f'{game} | running', flush=True)
                    if status_callback:
                        status_callback(True, game)
                    command = [python, str(ROOT / 'driver_competition.py'), board,
                               '--driver', str(filename), '--class-name', classname,
                               '--seed', str(seed), '--seconds', str(seconds)]
                    if cars is not None:
                        command += ['--cars', str(cars)]
                    if parked:
                        command += ['--parked']
                    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE, text=True)
                    err = ''
                    try:
                        started = time.monotonic()
                        while True:
                            remaining = wall_timeout - (time.monotonic() - started)
                            if remaining <= 0:
                                raise subprocess.TimeoutExpired(command, wall_timeout)
                            try:
                                out, err = process.communicate(timeout=min(1, remaining))
                                break
                            except subprocess.TimeoutExpired:
                                print(f'  still running ({time.monotonic() - started:.0f}s)', flush=True)
                        row = json.loads(out)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                        row = dict(board=board, seed=seed, status='wall_timeout',
                                   checkpoints_reached=0, checkpoint_times=[],
                                   completion_seconds=None, error='Process time limit exceeded; progress unknown')
                    except (ValueError, TypeError):
                        row = dict(board=board, seed=seed, status='error',
                                   checkpoints_reached=0, checkpoint_times=[],
                                   completion_seconds=None, error=(err or out)[-2000:])
                    except BaseException:
                        process.kill()
                        process.communicate()
                        raise
                    row['driver'] = label
                    results.append(row)
                    if status_callback:
                        status_callback(False, game)
                    total = row.get('checkpoints_total', '?')
                    print(f"  {row['status']}: {row['checkpoints_reached']}/{total} checkpoints"
                          + (f", {row['completion_seconds']} simulated seconds"
                             if row.get('completion_seconds') is not None else ''), flush=True)
                    print(f"  result returned: { {k: v for k, v in row.items() if k != 'collision_beliefs'} }", flush=True)
                    if err:
                        print(err.rstrip(), flush=True)
                    if row['status'] == 'collision' and row.get('collision_beliefs'):
                        for report in row['collision_beliefs']:
                            print(f"  Car {report['car']} belief (>0.02): {report['belief']}", flush=True)
                            print(f"  Car {report['car']} next belief (>0.02): {report['next_belief']}", flush=True)
    except KeyboardInterrupt:
        print('Stopped. Returning the runs already completed.')
    return results


def tables(results):
    """Speed races use only checkpoints reached by both drivers in a pair."""
    valid = {'completed', 'collision', 'timeout'}
    labels = sorted({r['driver'] for r in results})
    races = []
    for board, seed in sorted({(r['board'], r['seed']) for r in results}):
        pair = [r for r in results if (r['board'], r['seed']) == (board, seed)]
        if len(pair) != 2 or any(r['status'] not in valid for r in pair):
            continue
        a, b = pair
        for index, (ta, tb) in enumerate(zip(a['checkpoint_times'], b['checkpoint_times']), 1):
            races.append(dict(board=board, seed=seed, checkpoint=index,
                              **{a['driver']: ta, b['driver']: tb},
                              winner='tie' if abs(ta-tb) < 1e-9 else a['driver'] if ta < tb else b['driver']))
    summary = []
    for label in labels:
        all_rows = [r for r in results if r['driver'] == label]
        rows = [r for r in all_rows if r['status'] in valid]
        times = [r['completion_seconds'] for r in rows if r['status'] == 'completed']
        summary.append(dict(driver=label, scored_runs=len(rows),
                            boards_completed=len(times),
                            checkpoints_reached=sum(r['checkpoints_reached'] for r in rows),
                            checkpoint_speed_wins=sum(r['winner'] == label for r in races),
                            mean_completion_seconds=sum(times)/len(times) if times else None,
                            collisions=sum(r['status']=='collision' for r in rows),
                            timeouts=sum(r['status']=='timeout' for r in rows),
                            unscored_runs=len(all_rows)-len(rows)))
    return summary, races


def save_results(results, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'runs.json').write_text(json.dumps(results, indent=2))
    summary, races = tables(results)
    for name, rows in [('summary', summary), ('checkpoint_races', races)]:
        if rows:
            with (directory / f'{name}.csv').open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('board')
    parser.add_argument('--driver', required=True)
    parser.add_argument('--class-name', default='IntelligentDriver')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--cars', type=int)
    parser.add_argument('--parked', action='store_true')
    parser.add_argument('--seconds', type=float, default=120)
    args = parser.parse_args()
    print(json.dumps(simulate(args.board, args.driver, args.class_name,
                              args.seed, args.cars, args.parked, args.seconds)))
