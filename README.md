# AI course projects

The three projects explore sentence correction, [Connect Four and PopOut](connectfour/), and autonomous driving.

## Sentence correction

The corrector reads a sentence with character-recognition errors and uses an n-gram language model to score possible corrections. It reverses the confusion matrix to find which original characters could have produced each observed character. Each edit substitutes one character, preserving word lengths and spacing.

A greedy pass works from left to right. For each word, it tries single-character edits and scores them with up to five words of context on either side. It accepts an edit only when the score improves. The next word is therefore evaluated in the context of corrections already made.

Subsequent passes use **beam search** to explore corrections that need several edits. At each depth, the solver keeps up to 100 spellings for further expansion and can explore up to four substitutions per word. An intermediate spelling can score worse and still lead to a better final word. A visited set prevents repeated scoring of the same spelling during that word search.

The solver cuts a word search short if at least seven of the first ten distinct alternatives score worse than the unchanged word. This saves work on unpromising edits at the cost of potentially missing a deeper correction. It updates the current sentence after every word, so the runner can return the latest correction when the time budget expires mid-pass.

## Autonomous driving

The autonomous car must reach a sequence of checkpoints while sharing the road with traffic. It receives a noisy distance reading for each other car. The estimator turns those readings into a probability distribution over road cells. The driver uses the distributions to choose a route, then steers toward cell centers in the simulator’s continuous coordinate system.

### Sparse belief tracking

[`estimator.py`](driving%20simulator/estimator.py) maintains a probability distribution per other car and selects the path named `pruned_exact_inference`:

1. Initialize uniformly over cells with valid outgoing transition entries.
2. Cache positive-probability outgoing transitions and cell centers.
3. Restrict initial support to a box around the first distance observation, using a radius of `1.5 * max(0, observedDist)` pixels.
4. If that box contains no supported state, retain the supported cell nearest the observing car.
5. On later moving-car updates, propagate retained support through the transition model; parked cars keep their position distribution.
6. Weight reachable states by distance-observation likelihood, normalize, and prune small probabilities.
7. Clear stale displayed support and write the retained distribution back to the belief grid.
8. Produce a separate one-transition forecast without another observation.

The following rules control which cells survive each update.

| Setting | Value / behavior |
| --- | --- |
| `ALPHA` | `0.001`; retain states whose normalized probability times total grid cells exceeds this threshold |
| `BETA` | `1`; prune every reading |
| `GAMMA` | `1.5`; first-observation search-box scale |
| Zero-likelihood fallback | Reuse the predicted weights if all observation weights sum to zero |
| Empty pruning fallback | Keep the most likely state |
| Missing outgoing transition | Cached self-loop for eligible cells |

Despite its name, this is **approximate inference**: support pruning, first-reading truncation, and likelihood sharpening differ from a full unmodified Bayesian filter. Every reading uses `prior * likelihood²`.

The alternative **particle filter** tracks 100 sampled positions per car. It initializes particles near the distance ring implied by the first reading, within three sensor standard deviations. On later readings it samples a transition for each moving particle, weights occupied cells by particle count times the sonar likelihood, and resamples. Both trackers return the current belief and a one-step forecast.

### Route planning and congestion

[`intelligentDriver.py`](driving%20simulator/intelligentDriver.py) builds a four-neighbor grid graph excluding obstacle tiles. It follows checkpoints in their required order, reusing a route while the current cell remains on it and rebuilding when the checkpoint changes or the route becomes invalid.

The route planner uses:

- **A\*** with unit step costs and Euclidean distance to the checkpoint.
- **Yen's loopless k-shortest-path procedure**, using A* spur searches and excluding selected edges/root nodes to generate alternatives.
- Up to **ten distinct routes** per planning decision.
- A congestion score over the first **ten cells ahead**, summing each cell's occupancy divided by its step index. For example, the same occupancy contributes five times as much at the next cell as it does five steps ahead. Cells beyond the scoring window can still affect route length, but their occupancy adds nothing to this score. This bounds the scoring work and can delay a response to congestion farther along the route.
- Path length as a secondary preference after congestion.

Cell occupancy is formed by summing other-car belief mass. This can exceed one and should be interpreted as an occupancy-risk proxy, not a calibrated probability that at least one car occupies the cell.

### Current and predicted hazard handling

The driver independently propagates the received current beliefs to produce present, one-step, and two-step occupancy maps, keeping parked-car distributions stationary. It does not directly consume the estimator's `getNextBelief()` output; the two components expose prediction through different interfaces.

The driver's layered response includes:

1. Physical-boundary recovery takes priority, including braking, reversing, and turning toward a safer inward target.
2. If the current cell exceeds the occupancy threshold, search for an escape route to a sufficiently empty cell.
3. If the next planned cell is currently occupied, block risky cells and reroute.
4. If the next cell is likely to be occupied after a transition, reroute using the predicted hazards.
5. If a normal route is unavailable, consider side-clearance maneuvers and least-risk fallbacks.

Both configurable obstacle thresholds default to `0.15` and are validated in `[0,1]`. Additional helpers inspect surrounding cells, turning clearance, obstacle proximity, and forecast risk. The geometric clearance check uses a radius based on half the vehicle diagonal plus two pixels and checks map boundaries, rectangular obstacles, and belief mass around the vehicle footprint.

Control includes a 30-update burn-in, steering toward target-cell centers, explicit reverse actions, emergency braking, and a turn-speed cap: on ordinary forward turns of at least 60 degrees, speeds above 2.5 are reduced. Escape and reverse maneuvers bypass that forward-turn cap. These additions address the gap between a valid grid route and a physically negotiable simulated trajectory.
