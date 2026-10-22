import random  
import math
import re

class SentenceCorrector(object):
    def __init__(self, cost_fn, conf_matrix):
        self.conf_matrix = conf_matrix
        self.cost_fn = cost_fn
        self.best_state = None
        self.conf_reverse_matrix = {}
        for original, errors in self.conf_matrix.items():
            for error in errors:
                if error not in self.conf_reverse_matrix:
                    self.conf_reverse_matrix[error] = []
                self.conf_reverse_matrix[error].append(original)  
        self.best_cost = float('inf')  
        self.states_visited = 0




    #implementing local serach with random restarts at the maxima
    #neighbour is defined by only one change in character
    ##################################################
    def chooseBestLocalCharacter(self, current_state, i, window_start, window_end):
        curr_char = current_state[i]
        window = current_state[window_start:window_end]
        local_index = i - window_start

        best_cost = self.cost_fn(window)
        best_chars = [curr_char]

        for replacement in self.conf_reverse_matrix.get(curr_char, []):
            if replacement == curr_char:
                continue

            candidate = (
                window[:local_index]
                + replacement
                + window[local_index + 1:]
            )
            cost = self.cost_fn(candidate)

            if cost < best_cost:
                best_cost = cost
                best_chars = [replacement]
            elif cost == best_cost:
                best_chars.append(replacement)

        return random.choice(best_chars)
    
    def getBestNeighbour(self, current_state, current_cost):
        possible_neighbours = []

        best_neighbours = [current_state]
        best_cost = current_cost
        word_spans = list(re.finditer(r'\S+', current_state))
        
        for i in range(len(current_state)):
            curr_char = current_state[i]
            if curr_char in self.conf_reverse_matrix :
                possible_errors = self.conf_reverse_matrix[current_state[i]]
                replacement = self.chooseBestLocalCharacter(
                                current_state, i, window_start, window_end
                            )
                if replacement == current_state[i]:
                    continue
                possible_neighbour = current_state[:i] + possible_errors[j] + current_state[i + 1:]
                neighbour_cost = self.cost_fn(possible_neighbour)
                if  neighbour_cost == best_cost :
                    best_neighbours.append(possible_neighbour)
                elif neighbour_cost < best_cost :
                    best_cost = neighbour_cost
                    best_neighbours = [possible_neighbour]

        return [random.choice(best_neighbours), best_cost]



        


        

                


    
    def greedyStep(self, current_state, current_cost):
        best_neighbour ,best_cost = self.getBestNeighbour(current_state, current_cost)
        return [best_neighbour, best_cost]
            

        

    def randomStep(self, current_state):
        result = []
        for char in current_state:
            choices = [char] + self.conf_reverse_matrix.get(char, [])
            result.append(random.choice(choices))
        
        result = ''.join(result)
        return [result, self.cost_fn(result)]


    def greedyWithRandomRestarts(self, start_state):

        current_cost = self.cost_fn(start_state)
        current_state = start_state
        while True:
            best_neighbour, best_cost = self.greedyStep(current_state, current_cost)
            if(best_cost < current_cost):
                current_cost = best_cost
                current_state = best_neighbour
                self.assignGlobalBestState(current_state, current_cost)
            else:
                current_state, current_cost = self.randomStep(current_state)
                self.assignGlobalBestState(current_state, current_cost)
            self.states_visited += 1


    def probabilityFn(self, step):
        return 1 / (1.0 + math.exp(-step))

    def probabilisticGreedyOrRandom(self, start_state):
        current_cost = self.cost_fn(start_state)
        current_state = start_state
        step = 0
        while True:
            self.assignGlobalBestState(current_state, current_cost)
            if(random.random() < self.probabilityFn(step)):
                current_state, current_cost = self.greedyStep(current_state, current_cost)
            else:
                current_state, current_cost = self.randomStep(current_state)
            step += 1


    def partiallyRandomStep(self, n, current_state):
        num = int(n * len(current_state))
        eligible = [
            i for i, char in enumerate(current_state)
            if any(ch != char for ch in self.conf_reverse_matrix.get(char, []))
        ]

        result = list(current_state)

        for i in random.sample(eligible, min(num, len(eligible))):
            choices = [
                ch for ch in self.conf_reverse_matrix[current_state[i]]
                if ch != current_state[i]
            ]
            result[i] = random.choice(choices)

        result = ''.join(result)
        return [result, self.cost_fn(result)]



    #allgreedy
    def kGreedySearch(self, start_state, K = 1, N_RANDOM = 1.0):
        current_states = [[start_state,self.cost_fn(start_state)]]
        self.best_state = current_states[0][0]
        self.best_cost = current_states[0][1]

        for i in range(1, K):
            current_states.append(self.partiallyRandomStep(N_RANDOM, start_state))
            self.assignGlobalBestState(current_states[i][0], current_states[i][1])
            self.states_visited += 1


        while True:
            next_neighbours = [self.greedyStep(state, cost) for state, cost in current_states]
            next_neighbours = [
                self.partiallyRandomStep(N_RANDOM, curr_state)
                if curr_state == state and curr_cost == cost
                else [state, cost]
                for (state, cost), (curr_state, curr_cost)
                in zip(next_neighbours, current_states)
            ]
            self.states_visited += K
            current_states = next_neighbours
            for state, cost in next_neighbours:
                self.assignGlobalBestState(state, cost)


    def getMGeneticCombinations(self, M, current_states):
        M = int(M * len(current_states))
        current_states.sort(key = lambda pair: pair[1])
        min_cost = current_states[0][1]
        weights = [math.exp(-(cost - min_cost)) for state, cost in current_states]
        genetic_combinations = []

        for _ in range(M):
            parent1 ,parent2 = random.choices(current_states, weights=weights, k=2)
            text1, text2 = parent1[0], parent2[0]
            split = random.randrange(1, len(text1))
            child1 = text1[:split] + text2[split:]
            child2 = text2[:split] + text1[split:]
            genetic_combinations.append([child1, self.cost_fn(child1)])
            genetic_combinations.append([child2, self.cost_fn(child2)])

        genetic_combinations.sort(key=lambda pair: pair[1])
        genetic_combinations = genetic_combinations[0:M]
        self.assignGlobalBestState(genetic_combinations[0][0], genetic_combinations[0][1])
        return genetic_combinations

        



    def kGeneticGreedy(self, start_state, K=2, M=1.0, P_GENETIC=0.2):
        current_states = [[start_state, self.cost_fn(start_state)]]
        self.best_state, self.best_cost = current_states[0]

        for i in range(1, K):
            current_states.append(self.greedyStep(self.best_state, self.best_cost))
            self.states_visited += 1

        while True:
            current_states.sort(key=lambda pair: pair[1])
            self.assignGlobalBestState(current_states[0][0], current_states[0][1])

            if random.random() < P_GENETIC:
                children = self.getMGeneticCombinations(M, current_states)
                remaining = K - len(children)
                current_states = current_states[:remaining] + children
            else:
                current_states = [self.greedyStep(state, cost) for state, cost in current_states]
            
            self.states_visited += K
            

    def greedyWordWise(self, current_state):
        pass  # Original archived method was an empty, unfinished stub.
        

    def assignGlobalBestState(self, current_state, current_cost):
        if(current_cost < self.best_cost):
            self.best_state = current_state
            self.best_cost = current_cost
            
    ########################################################################

    def search(self, start_state, **kwargs):
        self.best_state = start_state
        K = kwargs.get("K", 1)

        if all(key in kwargs for key in ("K", "M", "P_GENETIC")):
            self.kGeneticGreedy(
                start_state, K=K, M=kwargs["M"], P_GENETIC=kwargs["P_GENETIC"]
            )
        else:
            N = kwargs.get("N", 1.0)
            self.kGreedySearch(start_state, K, N)

# Full solver snapshot before isolating the latest algorithm (2026-10-15).
# Existing SentenceCorrector above is preserved; this snapshot includes all experiments.
import re
import random
import math
import hashlib
import heapq
from pathlib import Path
from itertools import product, combinations

class ArchivedSentenceCorrector(object):
    def __init__(self, cost_fn, conf_matrix):
        self.conf_matrix = conf_matrix
        self.cost_fn = cost_fn
        self.best_state = None
        self.greedy_iterations = 0
        self.beam_iterations = 0
        self.states_visited = 0
        self.conf_reverse_matrix = {}
        for original, errors in self.conf_matrix.items():
            for error in errors:
                if error not in self.conf_reverse_matrix:
                    self.conf_reverse_matrix[error] = []
                self.conf_reverse_matrix[error].append(original)
        self.best_cost = float('inf')
        self.num_of_steps = 0
        self.num_of_iterations = 0
        self.num_of_restarts = 0
        self.improving_restarts = 0
        self._restart_pending_improvement = False

    def dummy_randomrestart(self, state, window_start, W, n=3):
        """Return the original state unchanged to test without random restarts."""
        return state

    def nrandomrestart(self, state, window_start, W, n=3):
        """Perturb n random eligible characters in a window starting at a word index.

        Enumerate all allowed replacement combinations for the selected positions
        and return the lowest-context-cost sentence. Every selected character
        must change, so the restart can escape a single-edit local minimum even
        if its best combination is worse than the current state. If fewer than
        n characters have alternatives, use all eligible characters. Return the
        original state when none do. This does not update the global best.
        """
        if not isinstance(n, int) or n < 1:
            raise ValueError('n must be a positive integer')
        if not isinstance(W, int) or W < 1:
            raise ValueError('W must be a positive integer')
        words = list(re.finditer(r'\S+', state))
        if not isinstance(window_start, int) or not 0 <= window_start < len(words):
            raise ValueError('window_start must be a valid zero-based word index')
        left, right, context_left, context_right = self._window_bounds(words, window_start, W)
        eligible = []
        for position in range(left, right):
            alternatives = list(dict.fromkeys(
                ch for ch in self.conf_reverse_matrix.get(state[position], [])
                if len(ch) == 1 and not ch.isspace() and ch != state[position]
            ))
            if alternatives:
                eligible.append((position, alternatives))
        if not eligible:
            return state
        selected = random.sample(eligible, min(n, len(eligible)))
        best_context, best_cost = None, float('inf')
        context = state[context_left:context_right]
        for replacements in product(*(choices for _, choices in selected)):
            candidate = list(context)
            for (position, _), replacement in zip(selected, replacements):
                candidate[position - context_left] = replacement
            candidate = ''.join(candidate)
            cost = self.cost_fn(candidate)
            if best_context is None or cost < best_cost:
                best_context, best_cost = candidate, cost
        return state[:context_left] + best_context + state[context_right:]

    def chooseBestPair(self, window, prefix='', suffix='', current_cost=None):
        """Return the best strict single-character improvement; pairs are disabled.

        Try all allowed single-character replacements. Score the surrounding context, but only edit the window.
        Return (window, cost) unchanged if no candidate improves the baseline.
        """
        best_window = window
        best_cost = (self.cost_fn(prefix + window + suffix)
                     if current_cost is None else current_cost)
        eligible = []
        for position, char in enumerate(window):
            choices = list(dict.fromkeys(
                ch for ch in self.conf_reverse_matrix.get(char, [])
                if len(ch) == 1 and not ch.isspace() and ch != char
            ))
            if choices:
                eligible.append((position, choices))
        # Generate all candidates from the same original window.
        for position, choices in eligible:
            for replacement in choices:
                candidate = window[:position] + replacement + window[position + 1:]
                cost = self.cost_fn(prefix + candidate + suffix)
                if cost < best_cost:
                    best_window, best_cost = candidate, cost
        # Two-character evaluation disabled; retained for later experiments.
        # for (i, first_choices), (j, second_choices) in combinations(eligible, 2):
        #     for first, second in product(first_choices, second_choices):
        #         candidate = (window[:i] + first + window[i + 1:j]
        #                      + second + window[j + 1:])
        #         cost = self.cost_fn(prefix + candidate + suffix)
        #         if cost < best_cost:
        #             best_window, best_cost = candidate, cost
        return best_window, best_cost

    def chooseRandomGeneticCandidate(self, window, prefix='', suffix=''):
        """Sample one single-character neighbor, weighted by exp(-score)."""
        options = []
        for position, char in enumerate(window):
            for replacement in dict.fromkeys(self.conf_reverse_matrix.get(char, [])):
                if len(replacement) != 1 or replacement.isspace() or replacement == char:
                    continue
                candidate = window[:position] + replacement + window[position + 1:]
                options.append((candidate, self.cost_fn(prefix + candidate + suffix)))
        if not options:
            return window, self.cost_fn(prefix + window + suffix)

        lowest = min(score for _, score in options)
        weights = [max(math.exp(-(score - lowest)), 1e-12) for _, score in options]
        print(random.choices(options, weights=weights, k=1)[0])
        return random.choices(options, weights=weights, k=1)[0]

    def randomlyMutateCharacter(self, window):
        """Randomly replace one eligible character using the confusion matrix."""
        positions = [
            pos for pos, char in enumerate(window)
            if any(len(rep) == 1 and not rep.isspace() and rep != char
                   for rep in self.conf_reverse_matrix.get(char, []))
        ]
        if not positions:
            return window
        pos = random.choice(positions)
        char = window[pos]
        choices = list(dict.fromkeys(
            rep for rep in self.conf_reverse_matrix.get(char, [])
            if len(rep) == 1 and not rep.isspace() and rep != char
        ))
        replacement = random.choice(choices)
        return window[:pos] + replacement + window[pos + 1:]
    # ---------- helpers ----------

    def _score(self, state, prefix, suffix, cache):
        if state not in cache:
            cache[state] = self.cost_fn(prefix + state + suffix)
        return cache[state]

    def _per_index_parents(self, window, prefix, suffix, cache):
        """Pick one best non-worsening candidate per character position.

        If one or more replacements tie the current character's score, choose
        randomly among those tied candidates so equal-scoring edits can enter
        the parent pool. Strictly worse edits are excluded.
        """
        parents = {}
        for pos, char in enumerate(window):
            current_cost = self._score(window, prefix, suffix, cache)
            options = [(current_cost, window)]  # Keep the current character.
            for rep in dict.fromkeys(self.conf_reverse_matrix.get(char, [])):
                if len(rep) != 1 or rep.isspace() or rep == char:
                    continue
                cand = window[:pos] + rep + window[pos + 1:]
                cand_cost = self._score(cand, prefix, suffix, cache)
                if cand_cost <= current_cost:
                    options.append((cand_cost, cand))
            best_cost = min(candidate_cost for candidate_cost, _ in options)
            tied_best = [
                option for option in options if option[0] == best_cost
            ]
            selected = random.choice(tied_best)
            parents[selected[1]] = selected[0]
        return [(c, s) for s, c in parents.items()]

    @staticmethod
    def _sample_parent_pairs(parents, k):
        """Sample k pairs of different parents, weighted by exp(-cost).

        The same parent may appear in several pairs; within one pair the
        two parents are always different.
        """
        lo = min(c for c, _ in parents)
        weights = [max(math.exp(-(c - lo)), 1e-12) for c, _ in parents]  # shifted for stability
        indices = range(len(parents))
        pairs = []
        for _ in range(k):
            first = random.choices(indices, weights=weights)[0]
            rest = list(weights)
            rest[first] = 0
            second = random.choices(indices, weights=rest)[0]
            pairs.append((parents[first][1], parents[second][1]))
        return pairs

    @staticmethod
    def _four_states(p1, p2):
        """state1 = p1, state2 = p2, state3/state4 = random-split crossovers."""
        states = [p1, p2]
        if len(p1) > 1:
            s = random.randint(1, len(p1) - 1)
            states.append(p1[:s] + p2[s:])
            s = random.randint(1, len(p1) - 1)
            states.append(p2[:s] + p1[s:])
        return states

    # ---------- main ----------

    def geneticCorrection(self, W=5, k=6):
        """Window-based genetic correction with a single evolving state.

        For each window of W words, repeat:
        1. From the current state, find at every index the best of
           {keep the char, any single-char replacement}; each result is a parent.
        2. Sample k pairs of different parents with P ~ exp(-cost); a parent
           may appear in several pairs.
        3. For each pair build 4 states: parent1, parent2, and two
           random-split crossovers (p1[:s]+p2[s:], p2[:s]+p1[s:]).
        4. Choose randomly among the lowest-cost distinct offspring.
        Keep strict improvements and continue refining the window. Carry an
        equal-cost choice forward, then advance to the next window so a flat
        score cannot trap the inner loop. Full passes repeat until timeout.
        """
        if not isinstance(W, int) or W < 1:
            raise ValueError('W must be a positive integer')
        if not isinstance(k, int) or k < 1:
            raise ValueError('k must be a positive integer')
        if self.best_state is None:
            raise ValueError('Initialize the sentence with search() first')

        state = self.best_state
        words = list(re.finditer(r'\S+', state))
        update_interval = k * 10

        while words:
            changed = False
            for start in range(max(1, len(words) - W + 1)):
                left, right, context_left, context_right = self._window_bounds(words, start, W)
                window = state[left:right]
                prefix = state[context_left:left]
                suffix = state[right:context_right]
                cache = {}

                current = window
                cost = self._score(current, prefix, suffix, cache)

                while True:
                    parents = self._per_index_parents(current, prefix, suffix, cache)
                    if len(parents) >= 2:
                        candidates = set()
                        something = self._sample_parent_pairs(parents, k)
                        for p1, p2 in something:
                            candidates.update(self._four_states(p1, p2))
                    else:
                        candidates = {s for _, s in parents}
                    if not candidates:
                        break

                    scored = [(self._score(s, prefix, suffix, cache), s)
                              for s in sorted(candidates)]
                    best_cost = min(score for score, _ in scored)
                    best_state = random.choice([
                        candidate for score, candidate in scored
                        if score == best_cost
                    ])
                    if best_cost < cost:
                        cost, current = best_cost, best_state
                    else:
                        if best_cost == cost:
                            current = best_state
                        break

                if current != window:
                    state = state[:left] + current + state[right:]
                    changed = True
                    self.num_of_steps += 1
                    if self.num_of_steps % update_interval == 0:
                        self.assignGlobalBestState(state, self.cost_fn(state))

            self.num_of_iterations += 1
            self.assignGlobalBestState(state, self.cost_fn(state))
            

        return self.best_state
    @staticmethod
    def _window_bounds(words, start, W):
        """Return editable and centered 10 * W context character boundaries."""
        end = min(start + W, len(words))
        size = min(W * 10, len(words))
        context_start = max(0, start - (size - (end - start)) // 2)
        context_start = min(context_start, len(words) - size)
        return (words[start].start(), words[end - 1].end(),
                words[context_start].start(), words[context_start + size - 1].end())



    def beamEscape(self, window, prefix='', suffix='', current_cost=None,
                   max_depth=3, beam_width=100):
        """Keep the lowest-cost beam_width distinct states at each depth.

        Equal and worse intermediate states are allowed. Return the best
        strict improvement at the first successful depth. Retain only the
        current and next beams, not a search-wide visited set. Break cost
        ties with fresh random priorities at each depth. Each candidate has
        one priority per depth, so duplicate paths get no extra chances.
        """
        if not isinstance(max_depth, int) or max_depth < 1:
            raise ValueError('max_depth must be a positive integer')
        if not isinstance(beam_width, int) or beam_width < 1:
            raise ValueError('beam_width must be a positive integer')
        baseline = (self.cost_fn(prefix + window + suffix)
                    if current_cost is None else current_cost)
        beam = {window: baseline}
        for _ in range(max_depth):
            next_beam = {}
            priorities = {}
            salt = random.getrandbits(128).to_bytes(16, 'big')
            for state in beam:
                for position, char in enumerate(state):
                    for replacement in dict.fromkeys(self.conf_reverse_matrix.get(char, [])):
                        if len(replacement) != 1 or replacement.isspace() or replacement == char:
                            continue
                        candidate = state[:position] + replacement + state[position + 1:]
                        if candidate == window or candidate in next_beam:
                            continue
                        cost = self.cost_fn(prefix + candidate + suffix)
                        priority = hashlib.blake2b(
                            candidate.encode('utf-8'), key=salt, digest_size=16
                        ).digest()
                        if len(next_beam) >= beam_width:
                            worst = max(next_beam, key=lambda item: (
                                next_beam[item], priorities[item], item
                            ))
                            if (cost, priority, candidate) >= (
                                    next_beam[worst], priorities[worst], worst):
                                continue
                            del next_beam[worst]
                            del priorities[worst]
                        next_beam[candidate] = cost
                        priorities[candidate] = priority
            if not next_beam:
                break
            best = min(next_beam, key=lambda item: (
                next_beam[item], priorities[item], item
            ))
            if next_beam[best] < baseline:
                return best, next_beam[best]
            beam = next_beam
        return window, baseline

    def greedyWithBeamCorrection(self, W=5, M=3, beam_depth=3, beam_width=100):
        """Run greedy descent with bounded beam search escapes at stuck windows."""
        if not isinstance(beam_depth, int) or beam_depth < 1:
            raise ValueError('beam_depth must be a positive integer')
        if not isinstance(beam_width, int) or beam_width < 1:
            raise ValueError('beam_width must be a positive integer')
        self.slidingWindowCorrection(W, M, beam_depth=beam_depth,
                                     beam_width=beam_width)
        return self.best_state

    def slidingWindowCorrection(self, W, M, n=3, beam_depth=None, beam_width=100):
        """Greedily correct W words using up to 10 * W words of scoring context.

        Each step evaluates all allowed single-character replacements inside
        the editable window and applies only the best strict cost improvement.
        After M steps, or when no edit improves the score, advance one word.
        Save the full sentence when an entire pass accepts no edits.
        Random restarts are disabled; their implementation is kept for testing.
        Nonempty searches with M > 0 keep cycling until an external timeout.
        With beam_depth set, try beam search at each stuck window.
        Unsuccessful passes continue until an external timeout.

        Context includes the editable window and is divided approximately
        equally between its left and right sides, shifting at sentence edges.
        Full-sentence cost saves the global best every M * 10 completed steps
        and after a full pass with no improvements.
        A timeout therefore exposes the best saved checkpoint.

        In the reported five-sentence comparison with M=5 and W=1 through 5,
        the original greedy approach (without random restarts) tied full-string scoring for the best observed costs on
        every sentence. Those results motivate retaining this method; they do
        not establish a global optimum or guarantee the best result on new data.
        """
        if not isinstance(W, int) or W <= 0:
            raise ValueError('W must be a positive integer')
        if not isinstance(M, int) or M < 0:
            raise ValueError('M must be a non-negative integer')
        if not isinstance(n, int) or n < 1:
            raise ValueError('n must be a positive integer')
        if self.best_state is None:
            raise ValueError('Initialize the sentence with search() first')

        state = self.best_state
        update_interval = M * 10
        # Keep whitespace intact while identifying the word boundaries.
        words = list(re.finditer(r'\S+', state))
        # Repeat full passes, including after a pass with no accepted edits.
        while words and M > 0:
            pass_improved = False
            for start in range(max(1, len(words) - W + 1)):
                left, right, context_left, context_right = self._window_bounds(words, start, W)
                window = state[left:right]
                prefix = state[context_left:left]
                suffix = state[right:context_right]
                cost = self.cost_fn(prefix + window + suffix)
                for _ in range(M):
                    next_window, next_cost = self.chooseBestPair(
                        window, prefix, suffix, cost
                    )
                    if next_window == window and beam_depth is not None:
                        # Save greedy progress before spending time on beam search.
                        self.assignGlobalBestState(state, self.cost_fn(state))
                        next_window, next_cost = self.beamEscape(
                            window, prefix, suffix, cost,
                            beam_depth, beam_width
                        )
                    changed = next_window != window
                    # Commit the greedy edit or beam search escape.
                    if changed:
                        pass_improved = True
                        state = state[:left] + next_window + state[right:]
                        if beam_depth is not None:
                            self.assignGlobalBestState(state, self.cost_fn(state))
                    window, cost = next_window, next_cost
                    self.num_of_steps += 1
                    if self.num_of_steps % update_interval == 0:
                        # Publish the best sentence at periodic checkpoints.
                        self.assignGlobalBestState(state, self.cost_fn(state))
                    # if not changed:
                    #     break
            # Count only passes that finished all windows before the timeout.
            self.num_of_iterations += 1
            if not pass_improved:
                # Save the completed greedy result. Random restarts are disabled.
                self.assignGlobalBestState(state, self.cost_fn(state))
                # restart_start = random.randrange(max(1, len(words) - W + 1))
                # restarted_state = self.nrandomrestart(state, restart_start, W, n)
                # if restarted_state != state:
                #     self.num_of_restarts += 1
                #     self._restart_pending_improvement = True
                #     state = restarted_state
                #     # Count immediate restart gains as well as later greedy gains.
                #     self.assignGlobalBestState(state, self.cost_fn(state))
                # else:
                #     self._restart_pending_improvement = False


        return state

    def geneticThenGreedyCorrection(self, W=5, M=3):
        """For each window, sample one genetic edit, greedily refine M times,
        and commit the proposal only if its final context score beats the
        original window score. The original sentence remains the fallback.
        """
        if not isinstance(W, int) or W < 1:
            raise ValueError('W must be a positive integer')
        if not isinstance(M, int) or M < 0:
            raise ValueError('M must be a non-negative integer')
        state = self.best_state
        words = list(re.finditer(r'\S+', state))
        while words and M > 0:
            for start in range(max(1, len(words) - W + 1)):
                left, right, context_left, context_right = self._window_bounds(words, start, W)
                window = state[left:right]
                prefix, suffix = state[context_left:left], state[right:context_right]
                original_cost = self.cost_fn(prefix + window + suffix)

                # Allow the sampled genetic proposal to worsen temporarily.
                proposal, proposal_cost = self.chooseRandomGeneticCandidate(
                    window, prefix, suffix
                )
                # Add one random confusion-matrix mutation before greedy search.
                proposal = self.randomlyMutateCharacter(proposal)
                proposal_cost = self.cost_fn(prefix + proposal + suffix)
                for _ in range(M):
                    improved, improved_cost = self.chooseBestPair(
                        proposal, prefix, suffix, proposal_cost
                    )
                    self.num_of_steps += 1
                    if improved == proposal:
                        break
                    proposal, proposal_cost = improved, improved_cost

                # Keep the proposal only if the completed genetic-plus-greedy
                # sequence improves on the saved original window context.
                if proposal != window and proposal_cost < original_cost:
                    state = state[:left] + proposal + state[right:]
                    self.assignGlobalBestState(state, self.cost_fn(state))

            self.num_of_iterations += 1
        return self.best_state

    def assignGlobalBestState(self, current_state, current_cost):
        if current_cost < self.best_cost:
            # Count each restart only once, when it first beats the global best.
            if self._restart_pending_improvement:
                self.improving_restarts += 1
                self._restart_pending_improvement = False
            self.best_state = current_state
            self.best_cost = current_cost

    ########################################################################

    # def search(self, start_state, W=5, M=3, n=3, k=4,
    #            beam_depth=5, beam_width=100):
    #     self.num_of_steps = 0

    #     self.num_of_iterations = 0
    #     self.num_of_restarts = 0
    #     self.improving_restarts = 0
    #     self._restart_pending_improvement = False
    #     self.best_state = start_state
    #     self.best_cost = self.cost_fn(start_state)
    #     return self.geneticCorrection(W, k)
    
    def wordCandidates(self, word, prefix='', suffix='', D=3, B=10, X=10, Y=10,
                       print_completed=False):
        """Yield scored beam-search candidates through depth D.

        Each edge changes one character. Retain at most B candidates per
        layer, with random priorities for cost ties. A seen set prevents
        repeated scoring and cycles; it stores words, not scored frontiers.
        Worse intermediate candidates remain eligible for the next beam.
        Stop if at least X of the first X + Y distinct candidates cost more
        than the original word in context. Equal costs do not count as worse.
        X=None disables this check; incomplete samples do not trigger it.
        """
        if not isinstance(D, int) or isinstance(D, bool) or D < 0:
            raise ValueError('D must be a non-negative integer')
        if not isinstance(B, int) or isinstance(B, bool) or B < 1:
            raise ValueError('B must be a positive integer')
        if X is not None and (not isinstance(X, int) or isinstance(X, bool) or X < 1):
            raise ValueError('X must be a positive integer or None')
        if not isinstance(Y, int) or isinstance(Y, bool) or Y < 0:
            raise ValueError('Y must be a non-negative integer')
        visited = {word}
        beam = [word]
        cost = self.cost_fn(prefix + word + suffix)
        self.states_visited += 1
        baseline = cost
        checked, worse = 0, 0
        yield word, cost
        for _ in range(D):
            next_beam = []
            for candidate in beam:
                for position, char in enumerate(candidate):
                    for replacement in self.conf_reverse_matrix.get(char, []):
                        if len(replacement) != 1 or replacement.isspace() or replacement == char:
                            continue
                        neighbor = candidate[:position] + replacement + candidate[position + 1:]
                        if neighbor in visited:
                            continue
                        visited.add(neighbor)
                        cost = self.cost_fn(prefix + neighbor + suffix)
                        self.states_visited += 1
                        # Yield every evaluated candidate for best-so-far selection.
                        yield neighbor, cost
                        # Check only the first X + Y distinct candidates across
                        # this word's search, against its unchanged context cost.
                        if X is not None and checked < X + Y:
                            checked += 1
                            worse += cost > baseline
                            if checked == X + Y and worse >= X:
                                return
                        # Negative keys put the worst retained option at the root.
                        entry = (-cost, -random.random(), neighbor)
                        if len(next_beam) < B:
                            heapq.heappush(next_beam, entry)
                        elif entry > next_beam[0]:
                            heapq.heapreplace(next_beam, entry)
            if not next_beam:
                break
            beam = [candidate for _, _, candidate in sorted(next_beam, reverse=True)]
        else:
            if print_completed and D > 0:
                print(word, flush=True)

    def saveBeamResult(self, original, result_path=None, phase="beam search"):
        """Append one completed beam-search result, preserving previous sentences."""
        path = (Path(result_path) if result_path is not None else
                Path(__file__).resolve().parent / 'results' /
                ('greedy_results.txt' if phase == 'greedy' else 'beam_results.txt'))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as output:
            output.write(f'Input before {phase}: {original}\n'
                         f'Output after {phase}: {self.best_state}\n'
                         f'Cost after {phase}: {self.best_cost}\n\n')

    def wordByWordCorrection(self, W=5, D=3, B=10, result_path=None, greedy_passes=2,
                             UpdateAfter=50, X=10, Y=10):
        """Run greedy passes, then repeat beam passes until an external timeout.

        Keep each word unless context cost strictly improves. Break ties among
        improving candidates randomly, and save each completed pass result.
        Unchanged passes continue; empty input returns immediately. Nonempty
        input needs a positive external timeout to stop.
        """
        if not isinstance(W, int) or isinstance(W, bool) or W < 1:
            raise ValueError('W must be a positive integer')
        if not isinstance(D, int) or isinstance(D, bool) or D < 0:
            raise ValueError('D must be a non-negative integer')
        if not isinstance(B, int) or isinstance(B, bool) or B < 1:
            raise ValueError('B must be a positive integer')
        if (not isinstance(UpdateAfter, int) or isinstance(UpdateAfter, bool)
                or UpdateAfter < 1):
            raise ValueError('UpdateAfter must be a positive integer')
        if (not isinstance(greedy_passes, int) or isinstance(greedy_passes, bool)
                or greedy_passes < 0):
            raise ValueError('greedy_passes must be a non-negative integer')
        if X is not None and (not isinstance(X, int) or isinstance(X, bool) or X < 1):
            raise ValueError('X must be a positive integer or None')
        if not isinstance(Y, int) or isinstance(Y, bool) or Y < 0:
            raise ValueError('Y must be a non-negative integer')
        if self.best_state is None:
            raise ValueError('Initialize the sentence with search() first')
        state = self.best_state
        original = state
        words = list(re.finditer(r'\S+', state))
        pass_index = 0
        self.greedy_iterations = 0
        self.beam_iterations = 0
        while words:
            phase = 'greedy' if pass_index < greedy_passes else 'beam search'
            depth = 1 if phase == 'greedy' else D
            if phase == 'beam search':
                original = state
            for index, match in enumerate(words):
                left, right = match.span()
                context_left = words[max(0, index - W)].start()
                context_right = words[min(len(words) - 1, index + W)].end()
                prefix = state[context_left:left]
                suffix = state[right:context_right]
                candidates = self.wordCandidates(
                    state[left:right], prefix, suffix, depth, B,
                    X if phase == 'beam search' else None, Y,
                    print_completed=(phase == 'beam search'))
                # The generator yields the unchanged word first.
                selected, baseline = next(candidates)
                lowest, ties = baseline, 1
                for candidate, cost in candidates:
                    if cost < lowest:
                        selected, lowest, ties = candidate, cost, 1
                    elif cost == lowest and cost < baseline:
                        ties += 1
                        if random.randrange(ties) == 0:
                            selected = candidate
                original_word = state[left:right]
                state = state[:left] + selected + state[right:]
                # Publish before evaluating the whole sentence in case of timeout.
                self.best_state = state
                # if lowest < baseline:
                #     print(
                #         f'Iteration {self.num_of_iterations + 1} | '
                #         f'Step {self.num_of_steps + 1} | Word {index + 1}: '
                #         f'{original_word!r} -> {selected!r} | '
                #         f'Context cost: {baseline} -> {lowest}',
                #         flush=True,
                #     )
                self.num_of_steps += 1
                if self.num_of_steps % UpdateAfter == 0:
                    self.best_cost = self.cost_fn(state)
            if self.num_of_steps % UpdateAfter != 0:
                self.best_cost = self.cost_fn(state)
            self.num_of_iterations += 1
            if phase == 'greedy':
                self.greedy_iterations += 1
            else:
                self.beam_iterations += 1
            if pass_index == greedy_passes - 1 or phase == 'beam search':
                if phase == 'greedy':
                    print(f'Cost after {phase}: {self.best_cost}', flush=True)
                self.saveBeamResult(original, result_path, phase)
            pass_index += 1
        return self.best_state

    def search(self, start_state, W=5, D=5, B=100,
               result_path=None, greedy_passes=1, UpdateAfter=50, X=10, Y=5):
        """Run greedy passes, then beam search until timeout."""
        self.best_state = start_state
        self.best_cost = None
        self.states_visited = 0
        self.num_of_steps = 0
        self.num_of_iterations = 0
        self.num_of_restarts = 0
        self.improving_restarts = 0
        self._restart_pending_improvement = False
        self.best_cost = self.cost_fn(start_state)
        return self.wordByWordCorrection(W, D, B, result_path, greedy_passes, UpdateAfter, X, Y)
