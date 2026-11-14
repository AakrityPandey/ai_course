"""Launch a generated checkpoint board without changing the simulator files."""
import argparse
import json
import os
from pathlib import Path
import random
import importlib.util
import time

ROOT = Path(__file__).resolve().parent


def main():
    boards = json.loads((ROOT / 'test_boards.json').read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('board', nargs='?', choices=boards)
    parser.add_argument('--list', action='store_true', help='List test boards without opening a window')
    parser.add_argument('--cars', type=int, help='Override the board default (1 normally, 3 for congested boards)')
    parser.add_argument('--parked', action='store_true')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--driver-file', default=str(ROOT / 'intelligentDriver.py'))
    parser.add_argument('--driver-class', default='IntelligentDriver')
    debug_group = parser.add_mutually_exclusive_group()
    debug_group.add_argument('--driver-debug', dest='driver_debug',
                             action='store_true', help='Enable driver diagnostics')
    debug_group.add_argument('--no-driver-debug', dest='driver_debug',
                             action='store_false', help='Disable driver diagnostics')
    parser.set_defaults(driver_debug=None)
    parser.add_argument('--result', type=Path, help='Write live-game results to JSON')
    parser.add_argument('--seconds', type=float, default=120, help='Live game time limit')
    args = parser.parse_args()
    if args.driver_debug is not None:
        os.environ['INTELLIGENT_DRIVER_DEBUG'] = str(args.driver_debug).lower()
    if args.list:
        for name, board in boards.items():
            print(f"{name:22} {len(board['checkpoints'])} checkpoints; "
                  f"{sum(board['shortest_steps_per_leg'])} minimum grid moves; "
                  f"{board['default_cars']} cars")
        return
    if args.board is None:
        parser.error('Choose a board, or use --list.')
    if args.seconds <= 0:
        parser.error('--seconds must be positive')
    board = boards[args.board]
    cars = board['default_cars'] if args.cars is None else args.cars
    if cars < 1:
        parser.error('--cars must be at least 1; the supplied driver needs car beliefs to run.')
    layout_data = json.loads((ROOT / 'layouts' / (board['world'] + '.json')).read_text())
    spawn_count = len({tuple(node['pos']) for node in layout_data['agentGraph']['nodes']})
    if cars > spawn_count:
        parser.error(f'This board has only {spawn_count} distinct traffic spawn positions.')
    os.chdir(ROOT)
    from engine.const import Const
    Const.WORLD = board['world']
    Const.CARS_PARKED = args.parked
    Const.SHOW_CARS = True
    Const.NUM_AGENTS = cars
    Const.INFERENCE = 'estimator'
    Const.TRACKER_METHOD = 'pruned_exact_inference'
    Const.SPEED = 'verySlow'
    Const.HEARTBEATS_PER_SECOND = Const.HEARTBEAT_DICT[Const.SIM_SPEED]
    Const.SECONDS_PER_HEARTBEAT = 1.0 / Const.HEARTBEATS_PER_SECOND
    Const.AUTO = True
    Const.INTELLIGENT_DRIVER = True
    Const.MULTIPLE_GOALS = True
    Const.NUM_CHECKPTS = len(board['checkpoints'])
    Const.COMPLETED_CHECKPTS = 0
    Const.TITLE = f'{Path(args.driver_file).stem} | {args.board}'
    random.seed(args.seed)
    from engine.model import model as model_module
    spec = importlib.util.spec_from_file_location('live_candidate', args.driver_file)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    if not hasattr(candidate, args.driver_class):
        parser.error(f'No {args.driver_class} class in {args.driver_file}')
    model_module.IntelligentDriver = getattr(candidate, args.driver_class)
    from engine.controller import Controller
    from engine.view.display import Display

    class LiveController(Controller):
        def isGameOver(self):
            if time.perf_counter() - self.started >= args.seconds:
                self.timed_out = True
                return True
            return super().isGameOver()

        def outputGameResult(self):
            if self.timed_out:
                print('Time limit reached.')
            else:
                super().outputGameResult()

    print(f"Running {args.board}: {Const.NUM_CHECKPTS} checkpoints, seed {args.seed}")
    controller = LiveController()
    controller.timed_out = False
    checkpoint_times = []
    original_check = controller.model._checkVictory
    def record_checkpoint():
        before = controller.model.nextCheckPtIdx
        won = original_check()
        if controller.model.nextCheckPtIdx > before:
            checkpoint_times.append(round(time.perf_counter() - controller.started, 3))
        return won
    controller.model._checkVictory = record_checkpoint
    controller.started = time.perf_counter()
    try:
        quit_requested = controller.drive()
        status = ('timeout' if controller.timed_out else 'quit' if quit_requested else
                  'collision' if controller.userThread.hasCollided() else 'completed')
        result = dict(board=args.board, driver=Path(args.driver_file).stem, seed=args.seed,
                      status=status, checkpoints_reached=len(checkpoint_times),
                      checkpoints_total=Const.NUM_CHECKPTS, checkpoint_times=checkpoint_times,
                      completion_seconds=checkpoint_times[-1] if status == 'completed' else None)
        if status == 'collision' and hasattr(controller.model.junior, 'collisionBeliefs'):
            beliefs = [car.getInference().getBelief()
                       for car in controller.model.getOtherCars()]
            parked = [car.getParkedStatus()
                      for car in controller.model.getOtherCars()]
            result['collision_beliefs'] = controller.model.junior.collisionBeliefs(beliefs, parked)
            for report in result['collision_beliefs']:
                print(f"Car {report['car']} belief (>0.02): {report['belief']}")
                print(f"Car {report['car']} next belief (>0.02): {report['next_belief']}")
        if args.result:
            args.result.parent.mkdir(parents=True, exist_ok=True)
            args.result.write_text(json.dumps(result, indent=2))
        # Notebook competitions pass --result and should exit after recording
        # a win, collision, or timeout instead of waiting in freezeFrame().
        if not quit_requested and not args.result:
            controller.freezeFrame()
    finally:
        Display.endGraphics()


if __name__ == '__main__':
    main()
