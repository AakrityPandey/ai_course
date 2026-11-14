"""Build reproducible test scenarios from the supplied road maps."""
import copy
import json
import pickle
import random
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def road_graph(data):
    rows, cols = data['size'][1] // 30, data['size'][0] // 30
    blocked = set()
    for x1, y1, x2, y2 in data['blocks']:
        blocked.update((r, c) for r in range(y1-1, y2+1) for c in range(x1-1, x2+1))
    cells = {(r, c) for r in range(rows) for c in range(cols)} - blocked
    return {cell: [n for n in ((cell[0]-1, cell[1]), (cell[0]+1, cell[1]),
                               (cell[0], cell[1]-1), (cell[0], cell[1]+1)) if n in cells]
            for cell in sorted(cells)}


def distances(graph, start):
    result = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for neighbor in graph[cell]:
            if neighbor not in result:
                result[neighbor] = result[cell] + 1
                queue.append(neighbor)
    return result


def transform(data, transitions, mode):
    data = copy.deepcopy(data)
    width, height = data['size']
    rows, cols = height // 30, width // 30
    flip_x = mode in ('mirror_x', 'rotate_180')
    flip_y = mode in ('mirror_y', 'rotate_180')

    def point(pos):
        x, y = pos
        return [width-x if flip_x else x, height-y if flip_y else y]

    def cell(rc):
        r, c = rc
        return (rows-1-r if flip_y else r, cols-1-c if flip_x else c)

    def rectangle(rect):
        x1, y1, x2, y2 = rect
        if flip_x:
            x1, x2 = cols-x2, cols-x1
        if flip_y:
            y1, y2 = rows-y2, rows-y1
        return [x1, y1, x2, y2]

    def direction(name):
        if flip_x:
            name = {'east': 'west', 'west': 'east'}.get(name, name)
        if flip_y:
            name = {'north': 'south', 'south': 'north'}.get(name, name)
        return name

    data['junior'] = point(data['junior'])
    data['juniorDir'] = direction(data['juniorDir'])
    data['blocks'] = [rectangle(rect) for rect in data['blocks']]
    data['intersections']['nodes'] = [rectangle(rect) for rect in data['intersections']['nodes']]
    for key in ('agentGraph', 'juniorGraph'):
        for node in data[key]['nodes']:
            node['pos'] = point(node['pos'])
            if 'dir' in node:
                node['dir'] = direction(node['dir'])
    transitions = {(cell(source), cell(dest)): p for (source, dest), p in transitions.items()}
    return data, transitions


def checkpoints(data, count, style, seed, transitions):
    graph = road_graph(data)
    start = (int(data['junior'][1] // 30), int(data['junior'][0] // 30))
    reachable = distances(graph, start)
    rows, cols = data['size'][1] // 30, data['size'][0] // 30
    # Keep checkpoint centers off the outermost row/column for ordinary tests.
    candidates = [cell for cell in sorted(reachable)
                  if cell != start and 0 < cell[0] < rows-1 and 0 < cell[1] < cols-1]
    if style == 'congested':
        traffic_cells = {cell for source_dest in transitions for cell in source_dest}
        candidates = [cell for cell in candidates if cell in traffic_cells]
    rng = random.Random(seed)
    goals = []
    current = start
    for _ in range(count):
        steps = distances(graph, current)
        available = [cell for cell in candidates if cell not in goals and steps[cell] >= 3]
        if style == 'local':
            goal = min(available, key=lambda c: (abs(steps[c]-5), c))
        elif style in ('tour', 'congested'):
            goal = max(available, key=lambda c: (steps[c], c))
        else:
            goal = rng.choice(available)
        goals.append(goal)
        current = goal
    return goals


def build():
    manifest = {}
    variants = [
        ('local', 'original', 3, 'local'),
        ('tour', 'original', 6, 'tour'),
        ('mixed', 'original', 5, 'mixed'),
        ('mirror_x', 'mirror_x', 4, 'mixed'),
        ('mirror_y', 'mirror_y', 5, 'mixed'),
        ('rotated', 'rotate_180', 6, 'tour'),
        ('congested', 'original', 6, 'congested'),
    ]
    for base in ('small', 'lombard'):
        original = json.loads((ROOT / 'layouts' / f'm_{base}.json').read_text())
        with (ROOT / 'learned' / f'{base}TransProb.p').open('rb') as handle:
            transitions = pickle.load(handle)
        for index, (suffix, mode, count, style) in enumerate(variants):
            name = f'{base}_{suffix}'
            data, table = transform(original, transitions, mode)
            goals = checkpoints(data, count, style, 410 + index, table)
            data['finish'] = [[c, r, c+1, r+1] for r, c in goals]
            graph = road_graph(data)
            start = (int(data['junior'][1] // 30), int(data['junior'][0] // 30))
            lengths = []
            for goal in goals:
                lengths.append(distances(graph, start)[goal])
                start = goal
            totals = {}
            for (source, destination), probability in table.items():
                assert 0 <= source[0] < data['size'][1]//30
                assert 0 <= source[1] < data['size'][0]//30
                assert 0 <= destination[0] < data['size'][1]//30
                assert 0 <= destination[1] < data['size'][0]//30
                totals[source] = totals.get(source, 0) + probability
            assert all(abs(total-1) < 1e-8 for total in totals.values())
            world = f'm_test_{name}'
            (ROOT / 'layouts' / f'{world}.json').write_text(json.dumps(data, indent=2) + '\n')
            with (ROOT / 'learned' / f'test_{name}TransProb.p').open('wb') as handle:
                pickle.dump(table, handle)
            manifest[name] = {'world': world, 'base': base, 'transform': mode,
                              'checkpoints': goals, 'shortest_steps_per_leg': lengths,
                              'default_cars': 3 if style == 'congested' else 1}
    (ROOT / 'test_boards.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Created and checked {len(manifest)} test boards.')


if __name__ == '__main__':
    build()
