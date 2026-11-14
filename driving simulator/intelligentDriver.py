'''
Licensing Information: Please do not distribute or publish solutions to this
project. You are free to use and extend Driverless Car for educational
purposes. The Driverless Car project was developed at Stanford, primarily by
Chris Piech (piech@cs.stanford.edu). It was inspired by the Pacman projects.
'''
import util
import copy
import itertools
import heapq
import math
import os
import sys
from turtle import Vec2D
from engine.const import Const
from engine.vector import Vec2d
from engine.model.car.car import Car
from engine.model.layout import Layout
from engine.model.car.junior import Junior
from configparser import InterpolationMissingOptionError

# Class: Graph
# -------------
# Utility class
class Graph(object):
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges

# Class: IntelligentDriver
# ---------------------
# An intelligent driver that avoids collisions while visiting the given goal locations (or checkpoints) sequentially. 
class IntelligentDriver(Junior):
    num1 = 0  # Blocked alerts shared by all instances.
    num2 = 0  # No-safe-path alerts shared by all instances.
    GAMMA = 6  # Distance for checking nearby occupied cells and replanning.
    different_path = 10  # Number of distinct A* routes to compare.
    num_of_blocks = 10  # Score only this many cells ahead on each route.

    # Funciton: Init
    def __init__(self, layout: Layout, obstacle_probability: float = 0.15,
                 beta_probability: float = 0.15, debug=None):
        if not 0.0 <= obstacle_probability <= 1.0:
            raise ValueError('obstacle_probability must be between 0 and 1')
        if not 0.0 <= beta_probability <= 1.0:
            raise ValueError('beta_probability must be between 0 and 1')
        self.obstacle_probability = obstacle_probability
        self.beta_probability = beta_probability
        self.alpha = obstacle_probability
        self.beta = beta_probability
        if debug is None:
            setting = os.environ.get('INTELLIGENT_DRIVER_DEBUG', 'true')
            debug = setting.strip().lower() not in ('0', 'false', 'no', 'off')
        self.debug = bool(debug)
        self.burnInIterations = 30
        self.layout = layout 
        # self.worldGraph = None
        self.worldGraph = self.createWorldGraph()
        self.checkPoints = self.layout.getCheckPoints() # a list of single tile locations corresponding to each checkpoint
        self.transProb = util.loadTransProb()
        self.outgoing = {}
        for (source, destination), probability in self.transProb.items():
            if probability > 0:
                self.outgoing.setdefault(source, []).append((destination, probability))
        self.neighbors = {cell: [] for cell in self.worldGraph.nodes}
        for source, destination in self.worldGraph.edges:
            if destination not in self.neighbors[source]:
                self.neighbors[source].append(destination)
        self.currentPath = []
        self.currentCheckpoint = None
        self.lastCell = None
        self.movesSincePlan = 0
        self._brakeForFuture = False
        self._avoidanceTarget = None
        self._originalRoute = None
        self._avoidanceOrigin = None
        self._escapeCurrentCell = False
        self._reverseForFuture = False
        self._boundaryRecoveryTarget = None
        self._boundaryRecoveryPhase = None

    def debugPrint(self, *parts):
        """Print driver diagnostics only when debugging is enabled."""
        if self.debug:
            print(*parts, file=sys.stderr)
        
    # ONE POSSIBLE WAY OF REPRESENTING THE GRID WORLD. FEEL FREE TO CREATE YOUR OWN REPRESENTATION.
    # Function: Create World Graph
    # ---------------------
    # Using self.layout of IntelligentDriver, create a graph representing the given layout.
    def createWorldGraph(self):
        nodes = []
        edges = []
        # create self.worldGraph using self.layout
        numRows, numCols = self.layout.getBeliefRows(), self.layout.getBeliefCols()

        # NODES #
        ## each tile represents a node
        nodes = [(x, y) for x, y in itertools.product(range(numRows), range(numCols))]
        
        # EDGES #
        ## We create an edge between adjacent nodes (nodes at a distance of 1 tile)
        ## avoid the tiles representing walls or blocks#
        ## YOU MAY WANT DIFFERENT NODE CONNECTIONS FOR YOUR OWN IMPLEMENTATION,
        ## FEEL FREE TO MODIFY THE EDGES ACCORDINGLY.

        ## Get the tiles corresponding to the blocks (or obstacles):
        blocks = self.layout.getBlockData()
        blockTiles = []
        for block in blocks:
            row1, col1, row2, col2 = block[1], block[0], block[3], block[2]
            blockWidth = col2-col1
            blockHeight = row2-row1

            for i in range(blockHeight):
                for j in range(blockWidth):
                    blockTiles.append((row1+i, col1+j))

        ## Remove blockTiles from 'nodes'
        nodes = [x for x in nodes if x not in blockTiles]

        for node in nodes:
            x, y = node[0], node[1]
            adjNodes = [(x, y-1), (x, y+1), (x-1, y), (x+1, y)]
            
            # only keep allowed (within boundary) adjacent nodes
            adjacentNodes = []
            for tile in adjNodes:
                if tile[0]>=0 and tile[1]>=0 and tile[0]<numRows and tile[1]<numCols:
                    if tile not in blockTiles:
                        adjacentNodes.append(tile)

            for tile in adjacentNodes:
                edges.append((node, tile))
                edges.append((tile, node))
        return Graph(nodes, edges)

    #######################################################################################
    # Function: Get Next Goal Position
    # ---------------------
    # Given the current belief about where other cars are and a graph of how
    # one can driver around the world, chose the next position.
    #######################################################################################
    def getNextGoalPos(self, beliefOfOtherCars: list, parkedCars:list , chkPtsSoFar: int):
        '''
        Input:
        - beliefOfOtherCars: list of beliefs corresponding to all cars
        - parkedCars: list of booleans representing which cars are parked
        - chkPtsSoFar: the number of checkpoints that have been visited so far 
                       Note that chkPtsSoFar will only be updated when the checkpoints are updated in sequential order!
        
        Output:
        - goalPos: The position of the next tile on the path to the next goal location.
        - moveForward: Unset this to make the AutoCar stop and wait.

        Notes:
        - You can explore some files "layout.py", "model.py", "controller.py", etc.
         to find some methods that might help in your implementation. 
        '''
        self._brakeForFuture = False
        self._escapeCurrentCell = False
        self._reverseForFuture = False
        if chkPtsSoFar >= len(self.checkPoints):
            return self.getPos(), False

        checkpoint = self.checkPoints[chkPtsSoFar]
        position = self.getPos()
        current = (util.yToRow(position.y), util.xToCol(position.x))
        if current not in self.neighbors:
            # The car can briefly be outside the graph near a boundary.
            current = min(self.neighbors, key=lambda cell: math.hypot(
                util.colToX(cell[1]) - position.x,
                util.rowToY(cell[0]) - position.y,
            ))

        self.lastCell = current

        # Physical map boundaries take priority over traffic emergencies.
        if self._boundaryRecoveryTarget is not None:
            recovery = self.continueBoundaryRecovery(current, checkpoint)
            if recovery is not None:
                return recovery
        elif self.boundaryCrashImminent():
            target = self.safestInwardCell(current)
            if target is not None:
                self._boundaryRecoveryTarget = target
                self._boundaryRecoveryPhase = 'brake'
                self.debugPrint(f'Boundary emergency: braking before reversing '
                                f'from {current} toward {target}')
                self._brakeForFuture = True
                return self.getPos(), False
            self.debugPrint(f'Boundary emergency: no inward cell from {current}; '
                            f'stopping in place')
            self._brakeForFuture = True
            return self.getPos(), False

        current_probability = self.cellProbability(current, beliefOfOtherCars)

        # 1. Escape immediately when another car occupies our current cell.
        if current_probability > self.alpha:
            escape_path = self.pathToNearestEmptyCell(current, beliefOfOtherCars)
            self.debugPrint(f'Emergency 1: current {current} '
                            f'p={current_probability:.4f} '
                            f'> alpha={self.alpha:.4f}')
            self.debugPrint('Emergency 1 surrounding cells (8 directions):')
            for neighbor in self.surroundingCells(current):
                if neighbor not in self.neighbors:
                    self.debugPrint(
                        f'  {neighbor}: p=n/a (map obstacle/outside map)')
                else:
                    probability = self.cellProbability(
                        neighbor, beliefOfOtherCars)
                    status = ('empty' if probability <= self.alpha
                              else 'occupied')
                    self.debugPrint(
                        f'  {neighbor}: p={probability:.4f} ({status})')
            if escape_path and len(escape_path) > 1:
                self.currentCheckpoint = None
                self.currentPath = escape_path
                self._escapeCurrentCell = True
                command = self.driveToCell(escape_path[1])
                motion = 'reverse' if self._reverseForFuture else 'forward'
                destination = escape_path[-1]
                destination_probability = self.cellProbability(
                    destination, beliefOfOtherCars)
                self.debugPrint(f'Emergency 1 escape route: {escape_path}')
                self.debugPrint(
                    f'Emergency 1 target: next={escape_path[1]} '
                    f'motion={motion}, empty destination={destination} '
                    f'p={destination_probability:.4f}')
                return command
            return self.leastRiskFallback(current, beliefOfOtherCars, parkedCars)

        # Make or resume the ordinary route to the objective.
        if (checkpoint != self.currentCheckpoint or not self.currentPath or
                current not in self.currentPath):
            self.currentPath = self.leastCongestedPath(
                current, checkpoint, beliefOfOtherCars) or []
            self.currentCheckpoint = checkpoint
        elif current in self.currentPath:
            self.currentPath = self.currentPath[self.currentPath.index(current):]

        if not self.currentPath:
            return self.leastRiskFallback(current, beliefOfOtherCars, parkedCars)
        if len(self.currentPath) == 1:
            return self.getPos(), False

        # 2. A currently occupied next route cell is an alpha obstacle.
        next_cell = self.currentPath[1]
        next_probability = self.cellProbability(next_cell, beliefOfOtherCars)
        if next_probability > self.alpha:
            blocked = {cell for cell in self.worldGraph.nodes
                       if self.cellProbability(cell, beliefOfOtherCars)
                       > self.alpha}
            blocked.discard(current)
            self.debugPrint(f'Emergency 2: next {next_cell} '
                            f'p={next_probability:.4f} '
                            f'> alpha={self.alpha:.4f}; rerouting')
            self.currentPath = self.leastCongestedPath(
                current, checkpoint, beliefOfOtherCars, blocked) or []
            if not self.currentPath or len(self.currentPath) == 1:
                return self.leastRiskFallback(current, beliefOfOtherCars, parkedCars)
            next_cell = self.currentPath[1]

        # 3. A high one-step prediction for the next cell is a beta obstacle.
        predictions = self.futureCellProbabilities(
            self.worldGraph.nodes, beliefOfOtherCars, parkedCars)
        predicted_probability = predictions[next_cell]
        if predicted_probability > self.beta:
            blocked = {cell for cell, probability in predictions.items()
                       if probability > self.beta}
            blocked.discard(current)
            self.debugPrint(f'Emergency 3: predicted next {next_cell} '
                            f'p={predicted_probability:.4f} '
                            f'> beta={self.beta:.4f}; rerouting')
            self.currentPath = self.leastCongestedPath(
                current, checkpoint, beliefOfOtherCars, blocked) or []
            if not self.currentPath or len(self.currentPath) == 1:
                return self.leastRiskFallback(current, beliefOfOtherCars, parkedCars)
            next_cell = self.currentPath[1]

        return self.driveToCell(next_cell)

    def cellProbability(self, cell, beliefs):
        """Combined current occupancy probability for one cell."""
        return sum(belief.getProb(*cell) for belief in beliefs)

    def pathToNearestEmptyCell(self, start, beliefs):
        """Eight-direction route to the nearest drivable cell at/below alpha."""
        frontier = [start]
        parent = {start: None}
        for cell in frontier:
            if (cell != start and
                    self.cellProbability(cell, beliefs) <= self.alpha):
                path = []
                while cell is not None:
                    path.append(cell)
                    cell = parent[cell]
                return path[::-1]
            for neighbor in self.emergencyNeighbors(cell):
                if neighbor not in parent:
                    parent[neighbor] = cell
                    frontier.append(neighbor)
        return None

    def surroundingCells(self, cell):
        """All horizontal, vertical, and diagonal coordinates around a cell."""
        row, col = cell
        return [
            (row + dr, col + dc)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if (dr != 0 or dc != 0)
        ]

    def emergencyNeighbors(self, cell):
        """The surrounding cells that are valid drivable graph nodes."""
        return [neighbor for neighbor in self.surroundingCells(cell)
                if neighbor in self.neighbors]

    def driveToCell(self, target):
        """Drive or reverse at full throttle toward one adjacent cell."""
        target_pos = Vec2d(util.colToX(target[1]), util.rowToY(target[0]))
        to_target = target_pos - self.pos
        self._reverseForFuture = (to_target.x * self.dir.x +
                                  to_target.y * self.dir.y) < 0
        return target_pos, True

    def boundaryCrashImminent(self):
        """Predict whether accelerating and stopping would cross a map edge."""
        speed = self.velocity.get_length()
        if speed == 0.0:
            return False
        projected_speed = min(speed + Junior.ACCELERATION, self.maxSpeed)
        stopping_distance = 0.0
        while projected_speed > 0.0:
            stopping_distance += projected_speed
            projected_speed -= self.friction
        direction = self.velocity.normalized()
        projected = self.pos + direction * stopping_distance
        radius = math.hypot(Car.LENGTH, Car.WIDTH) / 2.0 + 2.0
        return (projected.x - radius < 0.0 or
                projected.y - radius < 0.0 or
                projected.x + radius >= self.layout.getWidth() or
                projected.y + radius >= self.layout.getHeight())

    def boundaryClearance(self, cell):
        """Distance from a cell center to its nearest map boundary."""
        x = util.colToX(cell[1])
        y = util.rowToY(cell[0])
        return min(x, y, self.layout.getWidth() - x,
                   self.layout.getHeight() - y)

    def safestInwardCell(self, current):
        """Choose the drivable neighbor with the greatest boundary clearance."""
        candidates = self.emergencyNeighbors(current)
        if not candidates:
            return None
        target = max(candidates,
                     key=lambda cell: (self.boundaryClearance(cell), cell))
        if self.boundaryClearance(target) <= self.boundaryClearance(current):
            return None
        return target

    def continueBoundaryRecovery(self, current, checkpoint):
        """Brake, reverse inward, brake again, then align to the objective."""
        target = self._boundaryRecoveryTarget
        if self._boundaryRecoveryPhase == 'brake':
            if self.velocity.get_length() > 0.05:
                self._brakeForFuture = True
                return self.getPos(), False
            self.velocity = Vec2d(0.0, 0.0)
            target_pos = Vec2d(util.colToX(target[1]),
                               util.rowToY(target[0]))
            reverse_direction = self.pos - target_pos
            if reverse_direction.get_length() > 0.0:
                # Face away from the safe cell so reverse motion goes into it.
                self.dir = reverse_direction.normalized()
            self._boundaryRecoveryPhase = 'reverse'
            self.debugPrint(f'Boundary recovery: stopped and aligned; '
                            f'reversing toward {target}')

        if self._boundaryRecoveryPhase == 'reverse':
            target_pos = Vec2d(util.colToX(target[1]), util.rowToY(target[0]))
            if current != target and (target_pos - self.pos).get_length() > 8.0:
                self.currentPath = [current, target]
                self._reverseForFuture = True
                return target_pos, True
            self._boundaryRecoveryPhase = 'final_brake'
            self.debugPrint(
                f'Boundary recovery: reached inward cell {target}; braking')

        if self._boundaryRecoveryPhase == 'final_brake':
            if self.velocity.get_length() > 0.05:
                self._brakeForFuture = True
                return self.getPos(), False
            self.velocity = Vec2d(0.0, 0.0)
            path = self.shortestPath(current, checkpoint) or []
            if len(path) > 1:
                next_pos = Vec2d(util.colToX(path[1][1]),
                                 util.rowToY(path[1][0]))
                direction = next_pos - self.pos
                if direction.get_length() > 0.0:
                    self.dir = direction.normalized()
            self.currentPath = path
            self.currentCheckpoint = checkpoint
            self._boundaryRecoveryTarget = None
            self._boundaryRecoveryPhase = None
            self.debugPrint(
                f'Boundary recovery: aligned to objective route {path}')
            return self.getPos(), False

        return None

    def leastRiskFallback(self, current, beliefs, parkedCars):
        """Choose the lowest next-step occupancy among neighbors and this cell.

        A fallback does not require a route to the checkpoint or original route.
        Replan on the next update so a temporary refuge never becomes a goal.
        """
        cells = [current] + list(self.neighbors.get(current, ()))
        risk = self.futureCellProbabilities(cells, beliefs, parkedCars)
        self.debugPrint('Fallback next-step probabilities:')
        for cell in cells:
            label = 'current' if cell == current else 'neighbor'
            self.debugPrint(f'  {label} {cell}: p={risk[cell]:.4f}')
        self.currentCheckpoint = None
        self.currentPath = [current]
        self._originalRoute = None
        self._avoidanceTarget = None
        self._avoidanceOrigin = None
        self._escapeCurrentCell = False
        self.movesSincePlan = 0
        # All candidates are one road step away. Break equal-risk ties by
        # physical distance from the car, then by cell for deterministic turns.
        candidates = sorted(cells[1:], key=lambda cell: (
            risk[cell], math.hypot(util.colToX(cell[1]) - self.pos.x,
                                   util.rowToY(cell[0]) - self.pos.y), cell))
        # This is a last-resort ranking, independent of the normal occupancy
        # threshold and turn preview: neither should exclude the lowest cell.
        if candidates and risk[candidates[0]] < risk[current]:
            target = candidates[0]
            target_pos = Vec2d(util.colToX(target[1]), util.rowToY(target[0]))
            to_target = target_pos - self.pos
            self._reverseForFuture = (to_target.x * self.dir.x +
                                      to_target.y * self.dir.y) < 0
            motion = 'reverse' if self._reverseForFuture else 'forward'
            self.debugPrint(f'Fallback result: {motion} to {target} '
                            f'(p={risk[target]:.4f})')
            self.currentPath = [current, target]
            self._brakeForFuture = False
            return target_pos, True
        self.debugPrint(
            f'Fallback result: stay at {current} (p={risk[current]:.4f})')
        self._brakeForFuture = True
        return self.getPos(), False

    def findClearSide(self, current, checkpoint, beliefs, parkedCars, blocked):
        """Prefer the lower-risk traversable left/right cell, then a shorter route."""
        heading = self.dir.normalized()
        dr, dc = ((0, 1 if heading.x >= 0 else -1)
                  if abs(heading.x) >= abs(heading.y)
                  else (1 if heading.y >= 0 else -1, 0))
        sides = [(current[0] - dc, current[1] + dr),
                 (current[0] + dc, current[1] - dr)]
        predicted = self.futureCellProbabilities(sides, beliefs, parkedCars)
        candidates = []
        excluded = self.nearbyCongestedCells(current, beliefs) | blocked | {current}
        self.debugPrint(f'Dodge check: current={current}, checkpoint={checkpoint}, '
                        f'position=({self.pos.x:.1f}, {self.pos.y:.1f}), '
                        f'heading=({heading.x:.2f}, {heading.y:.2f})')
        self.debugPrint(f'  left={sides[0]}, right={sides[1]}, '
                        f'obstacle threshold={self.obstacle_probability:.2f}')
        self.debugPrint(f'  blocked route cells={sorted(blocked)}, '
                        f'excluded cells={sorted(excluded)}')
        for label, side in zip(('left', 'right'), sides):
            current_probability = sum(b.getProb(*side) for b in beliefs)
            next_probability = predicted[side]
            risk = max(current_probability, next_probability)
            self.debugPrint(
                f'  {label} {side}: current p={current_probability:.4f}, '
                f'next p={next_probability:.4f}, risk={risk:.4f}')
            if side not in self.neighbors[current]:
                self.debugPrint('    rejected: not a traversable adjacent cell')
                continue
            if side in excluded:
                self.debugPrint('    rejected: cell is excluded or likely occupied')
                continue
            if risk >= self.obstacle_probability:
                self.debugPrint(
                    '    rejected: probability reaches the obstacle threshold')
                continue
            # Choose the shortest detour back to the saved route, not a new
            # permanent route to the checkpoint. Exclude earlier route cells
            # from each connector so it cannot double back after rejoining.
            original = self._originalRoute if self._originalRoute is not None else self.currentPath[2:]
            found_route = False
            for index, join in enumerate(original):
                if join in excluded:
                    continue
                connector = self.shortestPath(side, join, excluded | set(original[:index]))
                if connector:
                    turn_clear = self.turnIsClear(side, beliefs, parkedCars)
                    if not turn_clear:
                        self.debugPrint(
                            f'    route to {join} exists, but steering preview is unsafe')
                        continue
                    route = connector + original[index + 1:]
                    candidates.append((len(connector), risk, len(route), [current] + route))
                    found_route = True
                    self.debugPrint(f'    candidate: rejoin at {join}, '
                                    f'connector={len(connector) - 1} cells, '
                                    f'total remaining route={len(route)} cells')
            if not found_route:
                self.debugPrint(
                    '    rejected: no safe turn and route back to the original path')
        if not candidates:
            self.debugPrint('Dodge result: no safe left or right route')
            return None
        chosen = min(candidates)
        self.debugPrint(f'Dodge result: target={chosen[3][1]}, '
                        f'connector={chosen[0] - 1} cells, '
                        f'risk={chosen[1]:.4f}')
        return chosen[3]

    def turnIsClear(self, target, beliefs, parkedCars):
        """Preview actual steering and car footprint, not just the destination cell."""
        cells = [(r, c) for r in range(self.layout.getBeliefRows())
                 for c in range(self.layout.getBeliefCols())]
        predicted = self.futureCellProbabilities(cells, beliefs, parkedCars)
        probe = copy.copy(self)
        probe.pos = Vec2d(self.pos.x, self.pos.y)
        probe.dir = Vec2d(self.dir.x, self.dir.y)
        probe.velocity = Vec2d(self.velocity.x, self.velocity.y)
        goal = Vec2d(util.colToX(target[1]), util.rowToY(target[0]))
        for _ in range(20):
            if not self.positionIsClear(probe.pos.x, probe.pos.y, beliefs, predicted):
                return False
            if (goal - probe.pos).get_length() <= 8:
                return True
            probe.setWheelAngle(-(goal - probe.pos).get_angle_between(probe.dir))
            probe.accelerate(Junior.ACCELERATION)
            turn_angle = abs((goal - probe.pos).get_angle_between(probe.dir))
            if turn_angle >= 60 and probe.velocity.get_length() > 2.5:
                probe.velocity.set_length(2.5)
            old = Vec2d(probe.pos.x, probe.pos.y)
            probe.update()
            # Sample between updates so the footprint cannot skip an obstacle.
            for fraction in (0.25, 0.5, 0.75, 1.0):
                point = old + (probe.pos - old) * fraction
                if not self.positionIsClear(point.x, point.y, beliefs, predicted):
                    return False
        return False

    def positionIsClear(self, x, y, beliefs, predicted=None):
        radius = math.hypot(Car.LENGTH, Car.WIDTH) / 2 + 2.0
        tile = Const.BELIEF_TILE_SIZE
        block_size = Const.BLOCK_TILE_SIZE
        if (x - radius < 0 or y - radius < 0 or
                x + radius >= self.layout.getWidth() or
                y + radius >= self.layout.getHeight()):
            return False
        for x1, y1, x2, y2 in self.layout.getBlockData():
            nearest_x = max(x1 * block_size, min(x, x2 * block_size))
            nearest_y = max(y1 * block_size, min(y, y2 * block_size))
            if math.hypot(x - nearest_x, y - nearest_y) <= radius:
                return False
        for row in range(math.floor((y-radius)/tile), math.floor((y+radius)/tile)+1):
            for col in range(math.floor((x-radius)/tile), math.floor((x+radius)/tile)+1):
                if (sum(b.getProb(row, col) for b in beliefs) >= self.obstacle_probability
                        or (predicted is not None and
                            predicted.get((row, col), 0.0) >= self.obstacle_probability)):
                    return False
        return True

    def beliefForecasts(self, cells, beliefs, parkedCars):
        """Return occupancy now, after one transition, and after two transitions."""
        selected = set(cells)
        forecasts = [{cell: 0.0 for cell in selected} for _ in range(3)]
        for belief, parked in zip(beliefs, parkedCars):
            distribution = {}
            for row in range(belief.getNumRows()):
                for col in range(belief.getNumCols()):
                    source = (row, col)
                    prior = belief.getProb(row, col)
                    if prior:
                        distribution[source] = prior
            for forecast in forecasts:
                for cell in selected:
                    forecast[cell] += distribution.get(cell, 0.0)
                if forecast is forecasts[-1]:
                    break
                following = {}
                for source, prior in distribution.items():
                    moves = [(source, 1.0)] if parked else self.outgoing.get(source, [(source, 1.0)])
                    for destination, chance in moves:
                        following[destination] = following.get(destination, 0.0) + prior * chance
                distribution = following
        return tuple(forecasts)

    def futureCellProbabilities(self, cells, beliefs, parkedCars):
        """One-transition occupancy used by side-turn safety checks."""
        return self.beliefForecasts(cells, beliefs, parkedCars)[1]

    def collisionBeliefs(self, beliefs, parkedCars, threshold=0.02):
        """Sparse current and one-transition beliefs for crash diagnostics."""
        reports = []
        for index, (belief, parked) in enumerate(zip(beliefs, parkedCars), 1):
            current = {}
            following = {}
            for row in range(belief.getNumRows()):
                for col in range(belief.getNumCols()):
                    source = (row, col)
                    prior = belief.getProb(row, col)
                    if prior <= 0:
                        continue
                    current[source] = prior
                    moves = [(source, 1.0)] if parked else self.outgoing.get(source, [(source, 1.0)])
                    for destination, chance in moves:
                        following[destination] = following.get(destination, 0.0) + prior * chance
            def significant(distribution):
                return [{'cell': [row, col], 'p': round(probability, 4)}
                        for (row, col), probability in sorted(distribution.items())
                        if probability > threshold]
            reports.append({'car': index, 'belief': significant(current),
                            'next_belief': significant(following)})
        return reports

    def intelligent_autonomousAction(self, beliefs, parkedCars, chkPtsSoFar):
        actions = self.getAutonomousActions(beliefs, parkedCars, chkPtsSoFar)
        if Car.DRIVE_FORWARD in actions:
            percent = max(0.0, min(1.0, actions[Car.DRIVE_FORWARD]))
            self.accelerate(Junior.ACCELERATION * percent)
        if Car.REVERSE in actions:
            percent = max(0.0, min(1.0, actions[Car.REVERSE]))
            reverse = self.dir.normalized() * (-Junior.ACCELERATION * percent)
            self.velocity += reverse
            if self.velocity.get_length() > self.maxSpeed:
                self.velocity.set_length(self.maxSpeed)
        if Car.TURN_WHEEL in actions:
            self.setWheelAngle(actions[Car.TURN_WHEEL])

        if self._brakeForFuture:
            self.decellerate(self.maxSpeed)
            return

        # Current-cell escapes and reverse moves use full throttle. A reverse
        # target naturally appears as a 180-degree forward turn and must not
        # be limited by the forward-turn speed cap below.
        if (self._escapeCurrentCell or self._reverseForFuture or
                len(self.currentPath) < 2):
            return

        next_cell = self.currentPath[1]
        target = Vec2d(util.colToX(next_cell[1]), util.rowToY(next_cell[0]))
        to_target = target - self.pos

        if to_target.get_length() > 1:
            turn_angle = abs(to_target.get_angle_between(self.dir))
            if turn_angle >= 60 and self.velocity.get_length() > 2.5:
                self.velocity.set_length(2.5)

    def turnCarTowardsWheels(self):
        """Keep the car facing forward while its velocity points backward."""
        if self.velocity.get_length() == 0.0:
            return
        moving_backward = (self.velocity.x * self.dir.x +
                           self.velocity.y * self.dir.y) < 0
        if not moving_backward:
            super().turnCarTowardsWheels()
            return
        # Steering has the opposite effect while reversing. The body direction
        # remains opposite the velocity instead of flipping through 180 degrees.
        self.velocity.rotate(-self.wheelAngle)
        self.dir = Vec2d(-self.velocity.x, -self.velocity.y)

    def obstacleAhead(self, beliefs):
        """Check a conservative stopping corridor every driving update."""
        # Include one more acceleration step, since returning True would add it.
        speed = min(self.velocity.get_length() + Junior.ACCELERATION, self.maxSpeed)
        distance = 0.0
        while speed > 0:
            distance += speed
            speed -= self.friction
        direction = self.dir.normalized()
        for step in range(math.ceil(distance / 2) + 1):
            offset = min(step * 2, distance)
            point = self.pos + direction * offset
            if not self.positionIsClear(point.x, point.y, beliefs):
                return True
        return False

    def shortestPath(self, start, goal, blocked_nodes=frozenset(), blocked_edges=frozenset()):
        """A* with one-cell steps and Euclidean distance to the checkpoint."""
        if start not in self.neighbors or goal not in self.neighbors:
            return None
        frontier = [(math.dist(start, goal), 0, start)]
        distance = {start: 0}
        parent = {}
        while frontier:
            _, steps, cell = heapq.heappop(frontier)
            if steps != distance[cell]:
                continue
            if cell == goal:
                path = [cell]
                while cell != start:
                    cell = parent[cell]
                    path.append(cell)
                return path[::-1]
            for neighbor in self.neighbors[cell]:
                if neighbor in blocked_nodes or (cell, neighbor) in blocked_edges:
                    continue
                new_steps = steps + 1
                if new_steps < distance.get(neighbor, math.inf):
                    distance[neighbor] = new_steps
                    parent[neighbor] = cell
                    heapq.heappush(frontier, (
                        new_steps + math.dist(neighbor, goal), new_steps, neighbor,
                    ))
        return None

    def differentPaths(self, start, goal, blocked_nodes=frozenset(),
                       blocked_edges=frozenset()):
        """Yen's loopless k-shortest paths, using A* for each spur route."""
        first = self.shortestPath(start, goal, blocked_nodes, blocked_edges)
        if first is None:
            return []
        paths = [first]
        candidates = []
        seen = {tuple(first)}
        while len(paths) < self.different_path:
            previous = paths[-1]
            for index in range(len(previous) - 1):
                root = previous[:index + 1]
                excluded_edges = set(blocked_edges)
                for path in paths:
                    if len(path) > index + 1 and path[:index + 1] == root:
                        excluded_edges.add((path[index], path[index + 1]))
                spur = self.shortestPath(
                    root[-1], goal, set(blocked_nodes) | set(root[:-1]),
                    excluded_edges)
                if spur is None:
                    continue
                candidate = tuple(root[:-1] + spur)
                if candidate not in seen:
                    seen.add(candidate)
                    heapq.heappush(candidates, (len(candidate), candidate))
            if not candidates:
                break
            paths.append(list(heapq.heappop(candidates)[1]))
        return paths

    def leastCongestedPath(self, start, goal, beliefs,
                          blocked_nodes=frozenset(), blocked_edges=frozenset()):
        """Choose by weighted occupancy over the first num_of_blocks cells ahead."""
        paths = self.differentPaths(start, goal, blocked_nodes, blocked_edges)
        probabilities = {}
        scored = []
        for path in paths:
            score = 0.0
            for step, cell in enumerate(path[1:1 + self.num_of_blocks], start=1):
                if cell not in probabilities:
                    probabilities[cell] = self.cellProbability(cell, beliefs)
                score += probabilities[cell] / step
            scored.append((score, len(path), path))
            self.debugPrint(f'A* candidate: congestion={score:.6f}, path={path}')
        if not scored:
            return None
        score, _, chosen = min(scored)
        self.debugPrint(f'A* chosen: congestion={score:.6f}, path={chosen}')
        return chosen

    def nearbyCongestedCells(self, start, beliefOfOtherCars):
        """Block likely car cells within GAMMA road moves of the AutoCar."""
        blocked = set()
        seen = {start}
        frontier = {start}
        for _ in range(self.GAMMA):
            frontier = {
                neighbor for cell in frontier for neighbor in self.neighbors[cell]
                if neighbor not in seen
            }
            seen.update(frontier)
            for row, col in frontier:
                if sum(belief.getProb(row, col) for belief in beliefOfOtherCars) >= self.obstacle_probability:
                    blocked.add((row, col))
        return blocked

    # DO NOT MODIFY THIS METHOD !
    # Function: Get Autonomous Actions
    # --------------------------------
    def getAutonomousActions(self, beliefOfOtherCars: list, parkedCars: list, chkPtsSoFar: int):
        # Don't start until after your burn in iterations have expired
        if self.burnInIterations > 0:
            self.burnInIterations -= 1
            return[]
       
        goalPos, df = self.getNextGoalPos(beliefOfOtherCars, parkedCars, chkPtsSoFar)
        vectorToGoal = goalPos - self.pos
        if self._reverseForFuture:
            reverse_direction = Vec2d(-self.dir.x, -self.dir.y)
            wheelAngle = vectorToGoal.get_angle_between(reverse_direction)
        else:
            wheelAngle = -vectorToGoal.get_angle_between(self.dir)
        driveForward = df
        actions = {
            Car.TURN_WHEEL: wheelAngle
        }
        if driveForward:
            action = Car.REVERSE if self._reverseForFuture else Car.DRIVE_FORWARD
            actions[action] = 1.0
        return actions
    
    
