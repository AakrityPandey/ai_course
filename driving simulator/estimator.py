from __future__ import annotations

import math
import random
from collections import Counter
from itertools import accumulate
import util
from util import Belief
from engine.const import Const

# Class: Estimator
#----------------------
# Maintain and update a belief distribution over the probability of a car being in a tile.
class Estimator(object):
    ALPHA = 0.001  # Minimum probability relative to an equal share of all cells.
    BETA = 1    # Number of readings between pruning steps.
    GAMMA = 1.5    # Size of the first-reading search box relative to measured distance.
    NUM_PARTICLES = 100
    INITIAL_SIGMAS = 3  # Initial distance band: observed distance +/- 3 sensor stds.

    def __init__(self, numRows: int, numCols: int):
        self.belief = util.Belief(numRows, numCols, 0.0)
        self._total_cells = numRows * numCols
        self.transProb = util.loadTransProb()
        self._seen_observation = False
        self._observation_count = 0

        # Ignore zero-probability entries in the transition table.
        self._outgoing = {}
        for (source, destination), probability in self.transProb.items():
            if probability > 0:
                self._outgoing.setdefault(source, []).append((destination, probability))

        # Start uniformly over cells that the StdCar can occupy.
        for row, col in self._outgoing:
            if 0 <= row < numRows and 0 <= col < numCols:
                self.belief.setProb(row, col, 1.0)
        self.belief.normalize()
        self._active_states = [
            cell for cell in self._outgoing
            if 0 <= cell[0] < numRows and 0 <= cell[1] < numCols
        ]
        self.tracker_method = Const.TRACKER_METHOD
        cells = set(self._active_states)
        cells.update(dest for moves in self._outgoing.values() for dest, _ in moves
                     if 0 <= dest[0] < numRows and 0 <= dest[1] < numCols)
        self._moves = {
            cell: [(dest, prob) for dest, prob in
                   self._outgoing.get(cell, [(cell, 1.0)])
                   if 0 <= dest[0] < numRows and 0 <= dest[1] < numCols]
            for cell in cells
        }
        self._cell_centers = {
            cell: (util.colToX(cell[1]), util.rowToY(cell[0])) for cell in cells
        }
        self.nextBelief = None  # Available after the first observation.
        if self.tracker_method == 'particle_filter':
            self._particles = []  # Draw the first particles after the first reading.
            # Cache fixed movement distributions and cell centers once.
            self._particle_moves = {
                cell: (tuple(dest for dest, _ in moves),
                       tuple(accumulate(prob for _, prob in moves)))
                for cell, moves in self._moves.items() if moves
            }

    def estimate(self, posX: float, posY: float, observedDist: float, isParked: bool) -> tuple[Belief, Belief]:
        """Update the current belief and forecast one transition ahead."""
        if self.tracker_method == 'particle_filter':
            self.particle_filter(posX, posY, observedDist, isParked)
        else:
            self._pruned_exact_inference(posX, posY, observedDist, isParked)
        self._seen_observation = True
        self._predictNextBelief(isParked)
        return self.belief, self.nextBelief

    def _pruned_exact_inference(self, posX, posY, observedDist, isParked):
        rows = self.belief.getNumRows()
        cols = self.belief.getNumCols()
        source_states = self._active_states
        if not self._seen_observation:
            # observedDist is in pixels, so convert the X/Y limits to columns/rows.
            radius = self.GAMMA * max(0.0, observedDist)
            first_row = max(0, util.yToRow(posY - radius))
            last_row = min(rows - 1, util.yToRow(posY + radius))
            first_col = max(0, util.xToCol(posX - radius))
            last_col = min(cols - 1, util.xToCol(posX + radius))
            nearby_states = [
                (row, col)
                for row in range(first_row, last_row + 1)
                for col in range(first_col, last_col + 1)
                if self.belief.getProb(row, col) > 0.0
                if abs(util.colToX(col) - posX) <= radius
                and abs(util.rowToY(row) - posY) <= radius
            ]
            if not nearby_states:
                # Keep a usable belief if the noisy reading gives an empty box.
                nearby_states = [min(
                    source_states,
                    key=lambda cell: math.hypot(
                        util.colToX(cell[1]) - posX,
                        util.rowToY(cell[0]) - posY,
                    ),
                )]
            source_states = nearby_states

        # Predict using only states retained from the previous estimate.
        predicted = {}
        if self._seen_observation and not isParked:
            for cell in source_states:
                prior = self.belief.getProb(*cell)
                for destination, move_probability in self._moves[cell]:
                    predicted[destination] = predicted.get(destination, 0.0) + prior * move_probability
        else:
            for cell in source_states:
                predicted[cell] = self.belief.getProb(*cell)

        # Observe only states reachable from the retained states.
        weights = {}
        for cell, prior in predicted.items():
            x, y = self._cell_centers[cell]
            expected_distance = math.hypot(x - posX, y - posY)
            likelihood = util.pdf(expected_distance, Const.SONAR_STD, observedDist)
            weights[cell] = prior * likelihood ** 2

        total = sum(weights.values())
        if total == 0.0:
            weights = predicted
            total = sum(weights.values())

        # Prune before writing the display grid. Normalize only retained cells,
        # avoiding a scan of the entire world at every pruning step.
        active = {cell: weight / total for cell, weight in weights.items() if weight > 0.0}
        self._observation_count += 1
        if self._observation_count % self.BETA == 0:
            kept = {cell: prob for cell, prob in active.items()
                    if prob * self._total_cells > self.ALPHA}
            if not kept:
                cell = max(active, key=active.get)
                kept = {cell: active[cell]}
            kept_total = sum(kept.values())
            active = {cell: prob / kept_total for cell, prob in kept.items()}

        for row, col in self._active_states:
            self.belief.setProb(row, col, 0.0)
        for (row, col), probability in active.items():
            self.belief.setProb(row, col, probability)
        self._active_states = list(active)

    def _predictNextBelief(self, isParked):
        """Predict one step ahead from the updated belief, without sensor data."""
        predicted = {}
        for cell in self._active_states:
            prior = self.belief.getProb(*cell)
            moves = [(cell, 1.0)] if isParked else self._moves[cell]
            for destination, probability in moves:
                predicted[destination] = predicted.get(destination, 0.0) + prior * probability
        total = sum(predicted.values())
        if total == 0.0:
            predicted = {cell: self.belief.getProb(*cell) for cell in self._active_states}
            total = sum(predicted.values())
        self.nextBelief = util.Belief(self.belief.getNumRows(), self.belief.getNumCols(), 0.0)
        for (row, col), probability in predicted.items():
            self.nextBelief.setProb(row, col, probability / total)

    def getNextBelief(self) -> Belief | None:
        """One-step prediction; None until estimate has received an observation."""
        return self.nextBelief

    def getBeliefs(self):
        return self.belief, self.nextBelief
  
    def getBelief(self) -> Belief:
        return self.belief

    def particle_filter(self, posX, posY, observedDist, isParked):
        if not self._seen_observation:
            # Use the first reading to place particles near a noisy distance ring.
            band = self.INITIAL_SIGMAS * Const.SONAR_STD
            outer_radius = max(0.0, observedDist + band)
            first_row = max(0, util.yToRow(posY - outer_radius))
            last_row = min(self.belief.getNumRows() - 1,
                           util.yToRow(posY + outer_radius))
            first_col = max(0, util.xToCol(posX - outer_radius))
            last_col = min(self.belief.getNumCols() - 1,
                           util.xToCol(posX + outer_radius))
            candidates = []
            weights = []
            box_cells = (last_row - first_row + 1) * (last_col - first_col + 1)
            if box_cells <= len(self._active_states):
                cells_to_check = (
                    (row, col)
                    for row in range(first_row, last_row + 1)
                    for col in range(first_col, last_col + 1)
                )
            else:
                cells_to_check = self._active_states
            for row, col in cells_to_check:
                if self.belief.getProb(row, col) == 0.0:
                    continue  # A cell the StdCar cannot occupy.
                dx = util.colToX(col) - posX
                dy = util.rowToY(row) - posY
                if abs(dx) > outer_radius or abs(dy) > outer_radius:
                    continue
                expected_distance = math.hypot(dx, dy)
                if abs(expected_distance - observedDist) <= band:
                    candidates.append((row, col))
                    weights.append(util.pdf(expected_distance, Const.SONAR_STD, observedDist))
            if not candidates:
                # An extreme reading may leave the distance band empty.
                candidates = self._active_states
                weights = [
                    util.pdf(
                        math.hypot(util.colToX(col) - posX, util.rowToY(row) - posY),
                        Const.SONAR_STD,
                        observedDist,
                    )
                    for row, col in candidates
                ]
            self._particles = random.choices(
                candidates, weights=weights if sum(weights) > 0.0 else None,
                k=self.NUM_PARTICLES,
            )
        else:
            # Group duplicate particles, but draw an independent move for each.
            counts = Counter(self._particles)
            if not isParked:
                moved = Counter()
                for cell, count in counts.items():
                    distribution = self._particle_moves.get(cell)
                    if distribution is None:
                        moved[cell] += count
                    else:
                        destinations, cumulative = distribution
                        if len(destinations) == 1:
                            moved[destinations[0]] += count
                        else:
                            moved.update(random.choices(
                                destinations, cum_weights=cumulative, k=count,
                            ))
                counts = moved

            # One likelihood per occupied cell. Multiplicity preserves the
            # same resampling probabilities as weighting particles separately.
            candidates = list(counts)
            weights = []
            for cell in candidates:
                x, y = self._cell_centers[cell]
                expected_distance = math.hypot(x - posX, y - posY)
                weights.append(counts[cell] * util.pdf(
                    expected_distance, Const.SONAR_STD, observedDist,
                ))
            if sum(weights) == 0.0:
                weights = [counts[cell] for cell in candidates]
            self._particles = random.choices(
                candidates, weights=weights, k=self.NUM_PARTICLES,
            )

        # Only previously occupied cells need clearing. Counts / N already
        # sum to one, so no full-grid normalization pass is needed.
        counts = Counter(self._particles)
        for row, col in self._active_states:
            self.belief.setProb(row, col, 0.0)
        for (row, col), count in counts.items():
            self.belief.setProb(row, col, count / len(self._particles))
        self._active_states = list(counts)
