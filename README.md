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

I scan every row, column, and diagonal. A board edge or the other player’s token acts as a break, giving patterns such as

$$11100011.$$

Here, $1$ is my token and $0$ is an empty cell. Each empty cell is treated independently as

$$P(0\rightarrow 1)=\frac12,
\qquad
P(0\rightarrow 2)=\frac12,$$

where $2$ is the opponent’s token. If the line has $z$ empty cells, it has $2^z$ possible completed patterns. For $11100011$, $z=3$, so I evaluate 8 patterns.

Let $\Omega_\ell$ be the set of all completed patterns for line $\ell$. For a completed pattern $x$, define

$$D(x)=\operatorname{Score}_{AI}(x)-\operatorname{Score}_{OPP}(x).$$

Since every empty cell has probability $1/2$ of becoming either player’s token, a completed pattern with $z$ original empty cells has probability

$$P(x)=\left(\frac12\right)^z.$$

The heuristic value of line $\ell$ is its expected score difference:

$$h(\ell)=\sum_{x\in\Omega_\ell}P(x)D(x)
=\sum_{x\in\Omega_\ell}left(\frac12\right)^z
\left(\operatorname{Score}_{AI}(x)-\operatorname{Score}_{OPP}(x)\right).$$

I repeat this calculation for every pattern, such as $11100011$ and $222000222$, in every row, column, and diagonal. I then sum all their expected score differences. The complete heuristic is the double sum

$$H(B)=
\sum_{\ell\in\mathcal L(B)}
\sum_{x\in\Omega_\ell}
P(x)
\left(
\operatorname{Score}_{AI}(x)-
\operatorname{Score}_{OPP}(x)
\right),$$

where $\mathcal L(B)$ is the set of all row, column, and diagonal patterns. The inner sum combines every possible completion of one pattern. The outer sum combines all patterns on the board. A larger $H(B)$ means the board is better for my AI.

Directly enumerating these completions at every node of the game tree would be expensive. The maximum row, column, or diagonal length is 12, so the largest single pattern has only $2^{12}=4096$ completions. On the first move, I precompute the expected score for every binary pattern of lengths 1 through 12. The total number of nonempty patterns is

$$\sum_{k=1}^{12}2^k=8190.$$

This one-time computation is manageable. I store the results in lookup tables indexed by pattern length and binary value. Later expectimax and minimax calls read the stored score instead of repeating the exponential calculation. The tables are shared across turn workers, so later moves can reuse them as well.

### PopOut strategy

The code uses zero-based column indices. Player 1 can PopOut from columns $0,2,4,\ldots$, while Player 2 can PopOut from columns $1,3,5,\ldots$. Both players receive a small preference for placing in columns $1,3,5,\ldots$ while either player still has a PopOut.

For Player 1, these are Player 2's PopOut columns. Suppose Player 1 places a piece there and Player 2 later pops it out. Player 1 can place a piece back in the same column on the next move. Player 2 has spent one PopOut, while Player 1 can restore the removed piece. If Player 1 instead builds mainly in columns $0,2,4,\ldots$, Player 1 may later be forced to pop out their own pieces. Player 2 can then keep adding pieces, increasing Player 2's number of pieces on the board and disturbing Player 1's scoring patterns.

Player 2 also prefers columns $1,3,5,\ldots$. By occupying Player 2's own PopOut columns, Player 2 reduces Player 1's chance to create the repeated remove-and-replace situation described above.

On an initially empty $6\times8$ board, Player 2 places the 48th piece and Player 1 moves next. If the board is full and PopOuts are the only legal moves, Player 1 must PopOut first. Player 1 therefore prefers to spend a remaining PopOut on a column containing only Player 2's pieces. This uses one PopOut without removing Player 1's own piece. The heuristic gives this move a bonus of 2. Player 2 receives a penalty of 2 for using a PopOut while more than two cells are empty, encouraging Player 2 to save it for the endgame.

The placement preference is

$$P_{place}(j)=
\begin{cases}
0.5, & j\bmod 2=1 \text{ and at least one PopOut remains},\\
0, & \text{otherwise},
\end{cases}$$

where $j$ is the zero-based column index.

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
