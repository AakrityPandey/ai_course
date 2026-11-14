"""Generate confusion-matrix inputs and benchmark the current solver (Unix).

Run: python3 test_corpus_inputs.py --timeout 2 --seed 333
Uses a standard-library signal timer; no optional timeout package required.
"""
import argparse
import contextlib
import csv
import io
import json
import pickle
import random
import signal
import time
from pathlib import Path

from solvers import SentenceCorrector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, default=2)
    parser.add_argument('--seed', type=int, default=333)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    root = Path(__file__).resolve().parent
    out = root / 'results' / 'corpus_tests'
    out.mkdir(parents=True, exist_ok=True)
    corpus = [s.strip() for s in (root / 'data/corpus.txt').read_text().splitlines() if s.strip()]
    matrix = json.loads((root / 'data/conf_matrix.json').read_text())
    rng = random.Random(args.seed)
    cases = []
    # Same source passages across levels make difficulty comparisons meaningful.
    for count in (1, 3, 5):
        for sample in range(2):
            indices = rng.sample(range(len(corpus)), count)
            clean = ' '.join(corpus[i] for i in indices)
            eligible = [i for i, c in enumerate(clean) if matrix.get(c)]
            for level, rate in [('clean', 0), ('light', .05), ('medium', .10), ('heavy', .20)]:
                positions = rng.sample(eligible, round(len(eligible) * rate))
                chars = list(clean)
                for i in positions:
                    chars[i] = rng.choice(matrix[chars[i]])
                noisy = ''.join(chars)
                assert len(noisy) == len(clean)
                assert all(a == b or b in matrix.get(a, []) for a, b in zip(clean, noisy))
                cases.append(dict(id=len(cases) + 1, level=level, sentences=count,
                                  corpus_lines=[i + 1 for i in indices], clean=clean,
                                  input=noisy, substitutions=len(positions)))
    (out / 'input.txt').write_text('\n'.join(c['input'] for c in cases) + '\n')
    (out / 'expected.txt').write_text('\n'.join(c['clean'] for c in cases) + '\n')
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    with (root / 'data/lm_model.pkl').open('rb') as fp:
        model = pickle.load(fp)
    model.unk_prob = 1e-20
    model.set_mode('spell_check')

    def expire(signum, frame):
        raise TimeoutError()

    previous = signal.signal(signal.SIGALRM, expire)
    rows, predictions = [], []
    try:
        for case in cases:
            random.seed(args.seed + case['id'])
            solver = SentenceCorrector(model, matrix)
            timed_out = False
            started = time.monotonic()
            # Isolate solver pass logs from the user's existing experiment logs.
            log = out / ('case_%02d_passes.txt' % case['id'])
            log.write_text('')
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    signal.setitimer(signal.ITIMER_REAL, args.timeout)
                    solver.search(case['input'], result_path=log)
            except TimeoutError:
                timed_out = True
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic() - started
            pred = solver.best_state
            assert isinstance(pred, str) and len(pred) == len(case['clean'])
            assert [i for i, c in enumerate(pred) if c.isspace()] == [i for i, c in enumerate(case['clean']) if c.isspace()]
            predictions.append(pred)
            clean, noisy = case['clean'], case['input']
            rows.append(dict(id=case['id'], level=case['level'], sentences=case['sentences'],
                             words=len(clean.split()), characters=len(clean),
                             substitutions=case['substitutions'],
                             remaining_errors=sum(a != b for a, b in zip(clean, pred)),
                             fixed_errors=sum(a != b and a == p for a, b, p in zip(clean, noisy, pred)),
                             introduced_errors=sum(a == b and a != p for a, b, p in zip(clean, noisy, pred)),
                             correct_words=sum(a == b for a, b in zip(clean.split(), pred.split())),
                             exact_match=pred == clean, input_cost=model(noisy),
                             output_cost=model(pred), expected_cost=model(clean),
                             seconds=elapsed, timed_out=timed_out,
                             greedy_passes=solver.greedy_iterations, beam_passes=solver.beam_iterations,
                             states_visited=solver.states_visited))
            print('Case %02d %-6s: %d -> %d character errors' %
                  (case['id'], case['level'], case['substitutions'], rows[-1]['remaining_errors']), flush=True)
    finally:
        signal.signal(signal.SIGALRM, previous)
    (out / 'predictions.txt').write_text('\n'.join(predictions) + '\n')
    with (out / 'metrics.csv').open('w', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = ['# Corpus test results', '',
               'Seed: %d. Timeout: %.2f seconds per input. %d cases.' % (args.seed, args.timeout, len(cases)),
               'Inputs combine 1, 3, or 5 corpus lines; corruption replaces 0%, 5%, 10%, or 20% of eligible characters using conf_matrix.json.',
               'The solver intentionally runs until timeout; predictions are its saved best_state.',
               'Corpus-derived evaluation is not an independent held-out accuracy estimate.', '',
               '| Difficulty | Cases | Initial errors | Remaining errors | Word accuracy | Exact matches |',
               '|---|---:|---:|---:|---:|---:|']
    for level in ('clean', 'light', 'medium', 'heavy'):
        group = [r for r in rows if r['level'] == level]
        summary.append('| %s | %d | %d | %d | %.1f%% | %d |' % (
            level, len(group), sum(r['substitutions'] for r in group),
            sum(r['remaining_errors'] for r in group),
            100 * sum(r['correct_words'] for r in group) / sum(r['words'] for r in group),
            sum(r['exact_match'] for r in group)))
    summary += ['', 'Re-run from A1_fresh: `python3 test_corpus_inputs.py --timeout 2 --seed 333`',
                'Generated input.txt and expected.txt contain corresponding lines. metrics.csv contains per-case scores and accuracy.',
                'The benchmark uses a Unix signal timer because the optional driver timeout dependency is unavailable. Solver and supporting files are unchanged.']
    (out / 'summary.md').write_text('\n'.join(summary) + '\n')
    print('\n'.join(summary))


if __name__ == '__main__':
    main()
