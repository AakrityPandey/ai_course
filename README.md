# AI course projects

The three projects explore autonomous driving, [Connect Four and PopOut](connectfour/), and sentence correction.

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

## Connect Four and PopOut

The objective in this version of Connect Four is to finish with more points. Making a line of four earns 20 points and play continues. The game ends when the player whose turn it is has no legal action. It then compares the two players’ scores across all rows, columns, and diagonals.

### What changes on a turn

The state consists of a board and each player’s remaining PopOut allowance. A player can **drop** a piece into the lowest empty cell of a column or spend one allowance to **pop** the bottom piece from a nonempty column. Player 1 can pop even-indexed columns and player 2 can pop odd-indexed columns, counting from zero. Either can remove an opposing piece this way. Every piece above it shifts down, so one PopOut can break a horizontal line and create a diagonal elsewhere. The [AI player](connectfour/starter_code/connect4/players/ai.py) simulates each candidate on a copy of both the board and the allowances.

A contiguous run of two pieces scores 2 points, three scores 5, and four scores 20. Longer runs score in groups of four plus the remainder. For example, six consecutive pieces score 22 points: 20 for the group of four and 2 for the remaining pair.

### How the AI chooses a move

The simulator selects the search algorithm from the opponent type. Both algorithms explore legal future turns, but they answer different questions about a candidate move.

| Opponent | Algorithm | How the AI values a reply |
| --- | --- | --- |
| Random player | Expectimax | On its own turns the AI takes the highest child value. On the opponent’s turns it averages all legal replies with equal weight. A risky move can still be attractive if only one reply punishes it. |
| Human or another AI | Minimax with alpha–beta pruning | The AI assumes the opponent will choose the reply that leaves it with the lowest value. It skips the rest of a branch once that branch cannot change the decision above it. |

Both searches use **iterative deepening**. They examine placements from the center outward, followed by PopOuts in the same column order. The AI commits to a new best move only after comparing every legal root action at that depth. If the next depth runs out of time halfway through, it returns the last fully compared move. It reserves three seconds of the turn budget and has a random legal fallback if the first depth cannot finish.

### How the AI scores an unfinished board

A line with two friendly pieces and open space can be more promising than the same pair boxed in at both ends. To estimate that potential, the AI splits each row, column, and diagonal wherever an opposing piece blocks it. Within each segment, it treats friendly pieces as fixed and gives each empty cell an independent one-half chance of becoming friendly. It totals the expected run points and subtracts the opponent’s corresponding total. This approximation ignores gravity and turn order while scoring a leaf. The game-tree search accounts for both when generating actual moves.

The code precomputes expected scores for binary patterns of friendly pieces and empty cells, indexed by segment length and bit pattern. Shared tables let successive turn workers reuse the calculation. Expectimax uses this board score directly. At a minimax depth cutoff, the AI weights it by the fraction of occupied cells. For a placement, it also counts how far the new piece can extend before meeting a blocker and compares its immediate point gain with what the opponent could have gained by occupying the same cell. Open space carries more weight early in the game.

### When the AI searches to the end

Minimax estimates the maximum number of turns left as **empty cells + twice the total remaining PopOut allowances**. A drop consumes one empty cell. A PopOut creates one empty cell but spends an allowance worth two in the formula. Either move therefore reduces the bound by one.

When this bound is small enough for the turn budget, minimax continues past its ordinary depth limit. At a terminal board it uses the actual point difference multiplied by 10,000. This gives a known endgame result much greater weight than a small move preference, while the clock still limits how far the search can finish.

## Sentence correction

The corrector reads a sentence with character-recognition errors and uses an n-gram language model to score possible corrections. It reverses the confusion matrix to find which original characters could have produced each observed character. Each edit substitutes one character, preserving word lengths and spacing.

A greedy pass works from left to right. For each word, it tries single-character edits and scores them with up to five words of context on either side. It accepts an edit only when the score improves. The next word is therefore evaluated in the context of corrections already made.

Subsequent passes use **beam search** to explore corrections that need several edits. At each depth, the solver keeps up to 100 spellings for further expansion and can explore up to four substitutions per word. An intermediate spelling can score worse and still lead to a better final word. A visited set prevents repeated scoring of the same spelling during that word search.

The solver cuts a word search short if at least seven of the first ten distinct alternatives score worse than the unchanged word. This saves work on unpromising edits at the cost of potentially missing a deeper correction. It updates the current sentence after every word, so the runner can return the latest correction when the time budget expires mid-pass.
