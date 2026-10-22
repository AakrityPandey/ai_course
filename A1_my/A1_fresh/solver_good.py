"""Latest solver: greedy warm-up followed by beam search until timeout.

Earlier experiments are preserved in solvers_old.py.
"""
import re
import random
import heapq
from pathlib import Path


class SentenceCorrector(object):
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
                # print(word, flush=True)
                pass

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
                self.best_state = state
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

    def search(self, start_state, W=5, D=4, B=200,
               result_path=None, greedy_passes=1, UpdateAfter=50, X=5, Y=2):
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


