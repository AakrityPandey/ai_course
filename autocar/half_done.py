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
    GAMMA = 6  # Distance for checking nearby occupied cells and replanning.

    # Funciton: Init
    def __init__(self, layout: Layout, obstacle_probability: float = 0.1):
        if not 0.0 <= obstacle_probability <= 1.0:
            raise ValueError('obstacle_probability must be between 0 and 1')
        self.obstacle_probability = obstacle_probability
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
            # some padding to ensure the AutoCar doesn't crash into the blocks due to its size. (optional)
            row1, col1, row2, col2 = row1-1, col1-1, row2+1, col2+1
            blockWidth = col2-col1 
            blockHeight = row2-row1 

            for i in range(blockHeight):
                for j in range(blockWidth):
                    blockTile = (row1+i, col1+j)
                    blockTiles.append(blockTile)

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

        if self.lastCell is not None and current != self.lastCell:
            self.movesSincePlan += 1
        self.lastCell = current

        if checkpoint != self.currentCheckpoint:
            self._originalRoute = None
            self._avoidanceTarget = None
            self._avoidanceOrigin = None
        if checkpoint != self.currentCheckpoint or (
                self._originalRoute is None and self.movesSincePlan >= self.GAMMA / 2):
            blocked = self.nearbyCongestedCells(current, beliefOfOtherCars)
            path = self.shortestPath(current, checkpoint, blocked)
            if path is None:
                self._brakeForFuture = True
                return self.getPos(), False
            self.currentPath = path
            self.currentCheckpoint = checkpoint
            self.movesSincePlan = 0

        if current in self.currentPath:
            self.currentPath = self.currentPath[self.currentPath.index(current):]

        # If traffic is predicted to enter our own cell, leave along the
        # already selected route at full throttle instead of waiting there.
        current_next = self.futureCellProbabilities(
            [current], beliefOfOtherCars, parkedCars,
        )[current]
        if current_next > 0.15:
            self._escapeCurrentCell = True
            target = checkpoint if len(self.currentPath) == 1 else self.currentPath[1]
            return Vec2d(util.colToX(target[1]), util.rowToY(target[0])), True

        # Rejoin the original route as soon as a forward route cell is reachable.
        if self._originalRoute and current != self._avoidanceOrigin:
            for index, cell in enumerate(self._originalRoute):
                goal = Vec2d(util.colToX(cell[1]), util.rowToY(cell[0]))
                if (goal - self.pos).get_length() <= 8:
                    self.currentPath = self._originalRoute[index:]
                    self._originalRoute = None
                    self._avoidanceTarget = None
                    self._avoidanceOrigin = None
                    self.movesSincePlan = 0
                    break
                if cell in self.neighbors[current] and self.turnIsClear(
                        cell, beliefOfOtherCars, parkedCars):
                    self.currentPath = [current] + self._originalRoute[index:]
                    self._avoidanceTarget = cell
                    return goal, True

        # Advance along the route between cell changes.
        if current in self.currentPath:
            index = self.currentPath.index(current)
            self.currentPath = self.currentPath[index:]
        # React to predicted occupancy of only the immediately next route cell.
        next_cells = self.currentPath[1:2]
        belief_m1, belief_m2, belief_m3 = self.beliefForecasts(
            next_cells, beliefOfOtherCars, parkedCars,
        )
        future_blocked = {
            cell for cell in next_cells
            if belief_m1[cell] > 0.2
            and belief_m3[cell] > belief_m2[cell] > belief_m1[cell]
        }
        # Finish an avoidance turn before selecting a different side.
        if self._avoidanceTarget is not None:
            goal = Vec2d(util.colToX(self._avoidanceTarget[1]),
                         util.rowToY(self._avoidanceTarget[0]))
            if (goal - self.pos).get_length() <= 8:
                self._avoidanceTarget = None
            elif self.turnIsClear(self._avoidanceTarget, beliefOfOtherCars, parkedCars):
                return goal, True
            else:
                self._avoidanceTarget = None

        straight_ahead_blocked = self.obstacleAhead(beliefOfOtherCars)
        if straight_ahead_blocked and not future_blocked and next_cells:
            # The straight-line stopping corridor can hit a wall even when
            # steering into the next route cell is safe (for example, a
            # corner beside the map boundary).
            next_cell = next_cells[0]
            if self.turnIsClear(next_cell, beliefOfOtherCars, parkedCars):
                goal = Vec2d(util.colToX(next_cell[1]), util.rowToY(next_cell[0]))
                return goal, True
        if future_blocked or straight_ahead_blocked:
            path = self.findClearSide(current, checkpoint, beliefOfOtherCars,
                                      parkedCars, future_blocked)
            if path is None:
                self._brakeForFuture = True
                return self.getPos(), False
            if self._originalRoute is None:
                # Skip the obstructed next cell; returning to it can restart
                # the same dodge forever.
                self._originalRoute = self.currentPath[2:]
                self._avoidanceOrigin = current
            self.currentPath = path
            self._avoidanceTarget = path[1]
            self.movesSincePlan = 0
            target = path[1]
            return Vec2d(util.colToX(target[1]), util.rowToY(target[0])), True

        target = checkpoint if len(self.currentPath) == 1 else self.currentPath[1]
        return Vec2d(util.colToX(target[1]), util.rowToY(target[0])), True

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
        for side in sides:
            if side not in self.neighbors[current] or side in excluded:
                continue
            risk = max(sum(b.getProb(*side) for b in beliefs), predicted[side])
            if risk >= self.obstacle_probability:
                continue
            # Choose the shortest detour back to the saved route, not a new
            # permanent route to the checkpoint. Exclude earlier route cells
            # from each connector so it cannot double back after rejoining.
            original = self._originalRoute if self._originalRoute is not None else self.currentPath[2:]
            for index, join in enumerate(original):
                if join in excluded:
                    continue
                connector = self.shortestPath(side, join, excluded | set(original[:index]))
                if connector and self.turnIsClear(side, beliefs, parkedCars):
                    route = connector + original[index + 1:]
                    candidates.append((len(connector), risk, len(route), [current] + route))
        return min(candidates)[3] if candidates else None

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

    def intelligent_autonomousAction(self, beliefs, parkedCars, chkPtsSoFar):
        super().intelligent_autonomousAction(beliefs, parkedCars, chkPtsSoFar)
        if self._brakeForFuture:
            self.decellerate(self.maxSpeed)

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
        wheelAngle = -vectorToGoal.get_angle_between(self.dir)
        driveForward = df
        actions = {
            Car.TURN_WHEEL: wheelAngle
        }
        if driveForward:
            actions[Car.DRIVE_FORWARD] = 1.0
        return actions
    
    
