# AI course projects

The three projects explore autonomous driving, Connect Four, and sentence correction.

## Autonomous driving

The goal is to reach the checkpoints in order and avoid collisions. My car knows the road map. For each other car, it gets a noisy distance reading. My estimator uses these readings to estimate where each car is. My driver uses the estimates to choose a route and steer.

### Algorithms

- **Track each car.** The default estimator uses pruned exact inference. The first reading narrows the search to nearby road cells. On later steps, the motion model gives a predicted probability $q(c)$ for each cell $c$. For a parked car, this is its previous probability. If $L(c)$ is the likelihood of the new distance reading at cell $c$, I calculate $w(c)=q(c)L(c)^2$ and normalize the weights to get probabilities.
- **Prune unlikely cells.** Let $N$ be the total number of grid cells. After each reading, I keep cells with probability $p(c)>0.001/N$ and scale their probabilities to sum to 1. The next update starts from these cells.
- **Particle filter (alternative).** I use 100 samples to represent one car’s possible positions. I start near the distance given by the first reading. For a moving car, I sample its next positions from the motion model. I then resample, giving more weight to positions that fit the new reading.
- **Find routes.** A* finds a shortest path to the next checkpoint using moves up, down, left, or right. Yen’s algorithm uses A* to find up to 10 different paths without loops.
- **Score congestion.** For each cell $c$, I add the probabilities of all other cars to obtain an occupancy score $r(c)$. For a path with $m$ cells ahead, I calculate
  $$S=\sum_{i=1}^{\min(10,m)}\frac{r(c_i)}{i},$$
  where $c_1$ is the next cell. I choose the path with the smallest $S$. If two paths have the same score, I choose the shorter one. The factor $1/i$ gives more weight to nearby traffic because it affects the car sooner. Predictions for distant cells may become outdated before the car reaches them. After 10 cells, the weights are already small, so I ignore those cells to reduce computation.
- **React to traffic.** I handle two urgent cases. If another car is likely to be in my current cell, I use breadth-first search in eight directions to find the nearest cell with occupancy at most 0.15 and move toward it immediately. If another car is likely to occupy my next path cell, either now or after one transition, I treat that cell as blocked and replan the route. If no complete route is available, I move to a neighboring cell only when its predicted risk is lower than the risk of staying still.

- **Control the car.** I steer toward the center of the next cell. On a normal forward turn of $60^\circ$ or more, I cap the speed at 2.5. Near a map boundary, the driver can brake and reverse toward an inner cell.

### Observations

- **Distance alone does not give a position.** Two cells on different roads can give the same distance reading. The motion model helps distinguish them across readings. With equal priors, a cell with twice the likelihood gets four times the weight because the update uses $L^2$.
- **Pruning reduces computation.** Fewer cells survive, so the next update checks fewer possible moves. The cost is that a low-probability cell may be dropped before a later reading supports it.
- **The route score favors nearby traffic.** The same occupancy contributes $r$ one step ahead and $r/5$ five steps ahead. Scoring only 10 cells limits the work per path. It can also miss a queue 11 cells ahead. Since $r(c)$ sums estimates for several cars, it can exceed 1.
- **A clear cell now may be occupied on the next step.** This is why the driver checks both current and predicted traffic. It also slows down on sharp turns because a clear path on the grid can still be hard to follow at speed.

## Connect Four and PopOut

The objective in this version of Connect Four is to finish with more points. A run of 2 pieces gives 2 points, a run of 3 gives 5 points, and a run of 4 gives 20 points. Scoring a run does not end the game. The game ends when the current player has no legal move, and the player with the larger total score wins.

### What changes on a turn

The state consists of a board and each player’s remaining PopOut allowance. A player can **drop** a piece into the lowest empty cell of a column or spend one allowance to **pop** the bottom piece from a nonempty column. Player 1 can pop even-indexed columns and player 2 can pop odd-indexed columns, counting from zero. Either can remove an opposing piece this way. Every piece above it shifts down, so one PopOut can break a horizontal line and create a diagonal elsewhere. The [AI player](connectfour/starter_code/connect4/players/ai.py) simulates each candidate on a copy of both the board and the allowances.

Scores are calculated over every row, column, and diagonal. For a run of length $k$, let $r=k\bmod 4$. Its score is

$$g(k)=20\left\lfloor\frac{k}{4}\right\rfloor+b_r,$$

where $b_0=0$, $b_1=0$, $b_2=2$, and $b_3=5$. For example, a run of 6 pieces gives $20+2=22$ points.

### How the AI chooses a move

The simulator selects the search algorithm from the opponent type. Both algorithms explore legal future turns, but they answer different questions about a candidate move.

| Opponent | Algorithm | How the AI values a reply |
| --- | --- | --- |
| Random player | Expectimax | On its own turns the AI takes the highest child value. On the opponent’s turns it averages all legal replies with equal weight. A risky move can still be attractive if only one reply punishes it. |
| Human or another AI | Minimax with alpha–beta pruning | The AI assumes the opponent will choose the reply that leaves it with the lowest value. It skips the rest of a branch once that branch cannot change the decision above it. |

Both searches use **iterative deepening**. They examine placements from the center outward, followed by PopOuts in the same column order. The AI commits to a new best move only after comparing every legal root action at that depth. If the next depth runs out of time halfway through, it returns the last fully compared move. It reserves three seconds of the turn budget and has a random legal fallback if the first depth cannot finish.

### Mathematical heuristic

Let $B$ be the board and let $\mathcal L(B)$ contain all rows, columns, and diagonals. For player $p$, I split each line at the opponent’s pieces. Inside each remaining segment, a cell already occupied by $p$ has probability 1 of belonging to $p$, and an empty cell has probability $1/2$.

For each possible completion of the segment, I calculate its score using $g(k)$. Let $E_p(\ell)$ be player $p$'s expected score on line $\ell$. The basic board heuristic is

$$V(B)=\sum_{\ell\in\mathcal L(B)}\left(E_{AI}(\ell)-E_{OPP}(\ell)\right).$$

A positive value favors my AI, while a negative value favors the opponent. This estimate treats empty cells independently. The search applies gravity, legal turns, and PopOut rules when it generates moves.

At a minimax depth limit, I also use information about the last move. Define:

- $\rho=$ occupied cells divided by total board cells;
- $O=$ number of cells visible from the new piece along the horizontal, vertical, and two diagonal axes, stopping at the board edge or an opponent piece;
- $s=1$ when my AI made the last move and $s=-1$ when the opponent made it;
- $\Delta_p=$ points gained by the player who placed the piece;
- $\Delta_{\bar p}=$ points the other player would gain by placing in the same cell.

For a placement, the code uses

$$H(B)=\rho V(B)+s(1-\rho)O+\Delta_p-\Delta_{\bar p}.$$

For a PopOut, no new piece is placed, so it uses

$$H(B)=\rho V(B).$$

Early in the game, $1-\rho$ is large, so open lines around the new piece have more weight. As the board fills, $\rho$ increases, so the expected board score has more weight. I precompute the expected score for every binary segment pattern up to length 12 and reuse these values during search.

At the root of minimax, I add a small move preference $P(a)$:

$$P(a)=
\begin{cases}
0.5, & \text{for a placement in an odd-indexed column while a PopOut remains},\\
2, & \text{when Player 1 pops a column containing only opponent pieces},\\
-2, & \text{when Player 2 uses a PopOut while more than 2 cells are empty},\\
0, & \text{otherwise}.
\end{cases}$$

The root value of action $a$ is therefore

$$Q(a)=\operatorname{Minimax}(B_a)+P(a).$$

Expectimax uses $V(B)$ at its depth limit. Minimax uses $H(B)$ at its depth limit. At a terminal state, minimax uses

$$T(B)=10000\left(\operatorname{Score}_{AI}(B)-\operatorname{Score}_{OPP}(B)\right).$$

### When the AI searches to the end

Minimax estimates the maximum number of turns left as **empty cells + twice the total remaining PopOut allowances**. A drop consumes one empty cell. A PopOut creates one empty cell but spends an allowance worth two in the formula. Either move therefore reduces the bound by one.

When this bound is small enough for the turn budget, minimax continues past its ordinary depth limit. At a terminal board it uses the actual point difference multiplied by 10,000. This gives a known endgame result much greater weight than a small move preference, while the clock still limits how far the search can finish.

## Sentence correction

The solver fixes one word at a time. A confusion matrix tells it which letters might have been mistaken for one another. A language model scores each possible spelling using the surrounding words. A lower score means the wording looks more likely to the model.

### Why try more than one spelling?

Suppose the intended word is **market**, but the input says **marxot**. Changing the **x** to **k** gives **markot**. That fixes one mistake, but the given model may give both misspellings the same score. A greedy search only accepts a change when the score improves, so it can get stuck. Beam search keeps several spellings around. It can try changing the **o** in **markot** to **e** and reach **market**, even though the first edit alone looked unhelpful.

The solver starts with a quick greedy pass which fixes most of the one character spelling mistakes. It then uses beam search to try up to four letter changes per word, keeping up to 100 spellings at each step.

### How the solver saves time

- **Move on when a word looks right.** I noticed that changing a letter in a correct word usually made the score worse. Changing a letter in a misspelled word often left the score the same. So if at least 7 of the first 10 different spellings score worse than the starting word, the solver moves on. Equal scores do not count toward the seven. This is a useful shortcut but speeds up beam search significantly, though it can occasionally skip a word that needs fixing.
- **Use a shorter context when calculating the n-gram language-model score.** I noticed that nearby words determined which spelling the model preferred, while distant words added the same cost to every candidate. For each proposed edit, I therefore scored only the target word and up to five words on either side. In my experiments, this significantly improved correction efficiency: each guess took less time to score, leaving more of the time budget to explore other possible corrections. The solver still checks the full-sentence score periodically.
