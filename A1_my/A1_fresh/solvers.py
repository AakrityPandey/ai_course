# """Latest solver: beam search with cycling word depths until timeout.

# Earlier experiments are preserved in solvers_old.py.
# """
# import re
# import random
# import heapq
# from pathlib import Path


# class SentenceCorrector(object):
#     def __init__(self, cost_fn, conf_matrix):
#         self.conf_matrix = conf_matrix
#         self.cost_fn = cost_fn
#         self.best_state = None
#         self.greedy_iterations = 0
#         self.beam_iterations = 0
#         self.states_visited = 0
#         self.conf_reverse_matrix = {}
#         for original, errors in self.conf_matrix.items():
#             for error in errors:
#                 if error not in self.conf_reverse_matrix:
#                     self.conf_reverse_matrix[error] = []
#                 self.conf_reverse_matrix[error].append(original)
#         self.best_cost = float('inf')
#         self.num_of_steps = 0
#         self.num_of_iterations = 0
#         self.num_of_restarts = 0
#         self.improving_restarts = 0
#         self._restart_pending_improvement = False

#     def wordCandidates(self, word, prefix='', suffix='', D=3, B=10, X=10, Y=10,
#                        print_completed=False):
#         """Yield scored beam-search candidates through depth D.

#         Each edge changes one character. Retain at most B candidates per
#         layer, with random priorities for cost ties. A seen set prevents
#         repeated scoring and cycles; it stores words, not scored frontiers.
#         Worse intermediate candidates remain eligible for the next beam.
#         Stop if at least X of the first X + Y distinct candidates cost more
#         than the original word in context. Equal costs do not count as worse.
#         X=None disables this check; incomplete samples do not trigger it.
#         """
#         if not isinstance(D, int) or isinstance(D, bool) or D < 0:
#             raise ValueError('D must be a non-negative integer')
#         if not isinstance(B, int) or isinstance(B, bool) or B < 1:
#             raise ValueError('B must be a positive integer')
#         if X is not None and (not isinstance(X, int) or isinstance(X, bool) or X < 1):
#             raise ValueError('X must be a positive integer or None')
#         if not isinstance(Y, int) or isinstance(Y, bool) or Y < 0:
#             raise ValueError('Y must be a non-negative integer')
#         visited = {word}
#         beam = [word]
#         cost = self.cost_fn(prefix + word + suffix)
#         self.states_visited += 1
#         baseline = cost
#         checked, worse = 0, 0
#         yield word, cost
#         for _ in range(D):
#             next_beam = []
#             for candidate in beam:
#                 for position, char in enumerate(candidate):
#                     for replacement in self.conf_reverse_matrix.get(char, []):
#                         if len(replacement) != 1 or replacement.isspace() or replacement == char:
#                             continue
#                         neighbor = candidate[:position] + replacement + candidate[position + 1:]
#                         if neighbor in visited:
#                             continue
#                         visited.add(neighbor)
#                         cost = self.cost_fn(prefix + neighbor + suffix)
#                         self.states_visited += 1
#                         # Yield every evaluated candidate for best-so-far selection.
#                         yield neighbor, cost
#                         # Check only the first X + Y distinct candidates across
#                         # this word's search, against its unchanged context cost.
#                         if X is not None and checked < X + Y:
#                             checked += 1
#                             worse += cost > baseline
#                             if checked == X + Y and worse >= X:
#                                 return
#                         # Negative keys put the worst retained option at the root.
#                         entry = (-cost, -random.random(), neighbor)
#                         if len(next_beam) < B:
#                             heapq.heappush(next_beam, entry)
#                         elif entry > next_beam[0]:
#                             heapq.heapreplace(next_beam, entry)
#             if not next_beam:
#                 break
#             beam = [candidate for _, _, candidate in sorted(next_beam, reverse=True)]
#         else:
#             if print_completed and D > 0:
#                 # print(word, flush=True)
#                 pass

#     def saveBeamResult(self, original, result_path=None, phase="beam search"):
#         """Append one completed beam-search result, preserving previous sentences."""
#         path = (Path(result_path) if result_path is not None else
#                 Path(__file__).resolve().parent / 'results' /
#                 ('greedy_results.txt' if phase == 'greedy' else 'beam_results.txt'))
#         path.parent.mkdir(parents=True, exist_ok=True)
#         with path.open('a', encoding='utf-8') as output:
#             output.write(f'Input before {phase}: {original}\n'
#                          f'Output after {phase}: {self.best_state}\n'
#                          f'Cost after {phase}: {self.best_cost}\n\n')

#     def wordByWordCorrection(self, W=5, B=10, result_path=None,
#                              UpdateAfter=50, X=10, Y=10, D=5):
#         """Repeat beam passes, cycling the global depth after each sentence pass.

#         Global depth d cycles from 1 through D; each word uses min(d, len(word)).
#         Keep each word unless context cost strictly improves. Break ties among
#         improving candidates randomly, and save each completed pass result.
#         Unchanged passes continue; empty input returns immediately. Nonempty
#         input needs a positive external timeout to stop.
#         """
#         if not isinstance(W, int) or isinstance(W, bool) or W < 1:
#             raise ValueError('W must be a positive integer')
#         if not isinstance(D, int) or isinstance(D, bool) or D < 1:
#             raise ValueError('D must be a positive integer')
#         if not isinstance(B, int) or isinstance(B, bool) or B < 1:
#             raise ValueError('B must be a positive integer')
#         if (not isinstance(UpdateAfter, int) or isinstance(UpdateAfter, bool)
#                 or UpdateAfter < 1):
#             raise ValueError('UpdateAfter must be a positive integer')
#         if X is not None and (not isinstance(X, int) or isinstance(X, bool) or X < 1):
#             raise ValueError('X must be a positive integer or None')
#         if not isinstance(Y, int) or isinstance(Y, bool) or Y < 0:
#             raise ValueError('Y must be a non-negative integer')
#         if self.best_state is None:
#             raise ValueError('Initialize the sentence with search() first')
#         state = self.best_state
#         original = state
#         words = list(re.finditer(r'\S+', state))
#         pass_index = 0
#         self.greedy_iterations = 0
#         self.beam_iterations = 0
#         while words:
#             d = 1 + pass_index % D
#             # print(d, flush=True)
#             original = state
#             for index, match in enumerate(words):
#                 left, right = match.span()
#                 word = state[left:right]
#                 depth = min(d, len(word))
#                 context_left = words[max(0, index - W)].start()
#                 context_right = words[min(len(words) - 1, index + W)].end()
#                 prefix = state[context_left:left]
#                 suffix = state[right:context_right]
#                 candidates = self.wordCandidates(
#                     state[left:right], prefix, suffix, depth, B,
#                     X, Y, print_completed=True)
#                 # The generator yields the unchanged word first.
#                 selected, baseline = next(candidates)
#                 lowest, ties = baseline, 1
#                 for candidate, cost in candidates:
#                     if cost < lowest:
#                         selected, lowest, ties = candidate, cost, 1
#                     elif cost == lowest and cost < baseline:
#                         ties += 1
#                         if random.randrange(ties) == 0:
#                             selected = candidate
#                 original_word = state[left:right]
#                 state = state[:left] + selected + state[right:]
#                 self.best_state = state
#                 self.num_of_steps += 1
#                 if self.num_of_steps % UpdateAfter == 0:
#                     self.best_cost = self.cost_fn(state)
#             if self.num_of_steps % UpdateAfter != 0:
#                 self.best_cost = self.cost_fn(state)
#             self.num_of_iterations += 1
#             self.beam_iterations += 1
#             self.saveBeamResult(original, result_path)
#             pass_index += 1
#         return self.best_state

#     def search(self, start_state, W=5, B=200,
#                result_path=None, UpdateAfter=50, X=5, Y=2, D=5):
#         """Cycle global depth from 1 to D, capped at each word's length."""
#         self.best_state = start_state
#         self.best_cost = None
#         self.states_visited = 0
#         self.num_of_steps = 0
#         self.num_of_iterations = 0
#         self.num_of_restarts = 0
#         self.improving_restarts = 0
#         self._restart_pending_improvement = False
#         self.best_cost = self.cost_fn(start_state)
#         return self.wordByWordCorrection(W, B, result_path, UpdateAfter, X, Y, D=D)


"""Latest solver: greedy warm-up followed by beam search until timeout.

Earlier experiments are preserved in solvers_old.py.
"""
import re
import random
import heapq
from pathlib import Path


class SentenceCorrectorCuti(object):
    def __init__(self, cost_fn, conf_matrix, verbose=False):
        self.verbose = verbose
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
            if self.verbose and print_completed and D > 0:
                print(word, flush=True)
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
                if self.verbose:
                    print(f'Completed beam iterations: {self.beam_iterations}', flush=True)
            if pass_index == greedy_passes - 1 or phase == 'beam search':
                if self.verbose and phase == 'greedy':
                    print(f'Cost after {phase}: {self.best_cost}', flush=True)
                self.saveBeamResult(original, result_path, phase)
            pass_index += 1
        return self.best_state

    def search(self, start_state, W=5, D=4, B=100,
               result_path=None, greedy_passes=1, UpdateAfter=50, X=7, Y=3):
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




import itertools

class SentenceCorrectorSpidy(object):
    def __init__(self, cost_fn, conf_matrix):
        self.conf_matrix = conf_matrix
        self.cost_fn = cost_fn

        # You should keep updating following variable with best string so far.
        self.best_state = None  
        self.original_state = None

    def initialise(self, start_state):
        words = start_state.split()
        weight = 2
        indices = [0]
        for i in range(len(words)):
            indices.append(indices[i] + len(words[i]) + 1)
        cost = self.cost_fn(start_state)
        sentence = start_state
        mat = self.get_conf_matrix()
        return words, indices, weight, sentence, cost, mat

    #The objective function
    def fn(self, initial_cost, sentence, wt):
        cost = self.cost_fn(sentence)
        f = cost*wt + initial_cost-cost
        return f

    #Substitutes the letter in the sentence
    def get_sentence(self,i, sentence, letter):
        return sentence[:i] + letter + sentence[i+1:]

    def get_letters(self, mat, indices, ch):
        to_substitute = []
        for i in range(ch):
            to_substitute.append([])
            l = mat[self.original_state[indices[i]]]
            for elem in l:
                to_substitute[i].append(elem)
            to_substitute[i].append(self.original_state[indices[i]])
        letters = itertools.product(*to_substitute)
        return letters

    def find_best_letters(self, current_letters, original_sentence ,indices, wt, initial_cost, mat, ch, word_index):
        better = current_letters
        min = 10000000000
        letters = self.get_letters(mat, indices, ch)
        for vals in letters:
            sentence = original_sentence
            for j in range(ch):
                sentence = self.get_sentence(indices[j], sentence, vals[j])
            context = []
            test_words = sentence.split()
            
            previous_context = 2
            ahead_context = 2
            for j in range(previous_context,0,-1):
                if word_index>j-1:
                    context.append(test_words[word_index-j])
            context.append(test_words[word_index])
            for j in range(1,1+ahead_context):
                if word_index<=len(test_words) - j-1:
                    context.append(test_words[word_index+j])

            test_sentence = ' '.join(context)
            f= self.fn(initial_cost, test_sentence, wt)
            if f<=min:
                better, min = vals, f
        return better , min

    def diff_letter(self, ch, new_letters, word, index):
        cond = False
        for j in range(ch):
            if new_letters[j]!=word[index[j]]:
                cond = True
                break
        return cond

    def stop_loop(self, ch, letters):
        cond = True
        for j in range(ch):
            if letters[0]!='':
                cond = False
                break
        return cond

    def init(self,ch, word, offset):
        test_list = []
        for i in range(len(word)):
            test_list.append(i)
        indices = list(itertools.combinations(test_list, ch))
        min = 10000000000
        letters = []
        positions = []
        letters_to_send = []
        positions_to_send = []
        for i in range(ch):
            letters.append('')
            positions.append(offset)
            letters_to_send.append("")
            positions_to_send.append(0)
        return indices, min, letters, positions, letters_to_send, positions_to_send

    #Finds the best letter to change in a word
    def find_best_word(self, word, offset, ch, weight, cost_init, mat, sentence, word_index):
        for j in range(len(word)):
            indices, min, letters, positions, letters_to_send, positions_to_send = self.init(ch, word, offset)
            for index in indices:
                for i in range(ch):
                    letters_to_send[i] = word[index[i]]
                    positions_to_send[i] = offset + index[i]

                new_letters, cost= self.find_best_letters(letters_to_send, sentence ,positions_to_send ,weight, cost_init, mat, ch, word_index)
                if self.diff_letter(ch, new_letters, word, index)==True and cost < min:
                    min = cost
                    letters = new_letters
                    positions = [offset + position for position in index]

            if self.stop_loop(ch, letters)==True:
                break 
            else:
                for i in range(ch):
                    sentence = self.get_sentence(positions[i], sentence, letters[i])
        return sentence

    #converts the given conf matrix to the semantically opposite key value pairs
    def get_conf_matrix(self):
        mat = {}
        char = 'a'
        for i in range(26):
            mat[char] = []
            char = chr(ord(char) + 1)
        for key, value in self.conf_matrix.items():
            for letter in value:
                mat[letter].append(key)
        return mat

    
    def search(self, start_state):
        words, indices, weight, self.best_state, cost_init, mat = self.initialise(start_state)
        
        self.original_state = start_state
        
        depth = 1
        while True:
            for j in range(len(words)):
                self.best_state = self.find_best_word(words[j], indices[j], depth, weight, cost_init, mat, self.best_state, j)
            words = self.best_state.split()
            depth+=1 