"""Compare all three solvers on the same generated corpus examples (macOS/Linux).

python3 compare_corpus_solvers.py --limit 100 --timeout 2
python3 compare_corpus_solvers.py --limit 100 --timeout 2 --output results/my_run
python3 compare_corpus_solvers.py --output results/my_run --resume
Each run saves separate predictions, per-case metrics, and grouped comparisons.
Default runs use a new timestamped folder. --resume reuses completed cases.
"""
import argparse
import contextlib
import csv
import datetime
import hashlib
import importlib
import itertools
import json
import math
import os
import pickle
import random
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'results' / 'solver_comparison'


class SearchDeadline(Exception):
    """Use a non-OSError deadline so filesystem helpers cannot swallow it."""


def export_case_comparison(output=None):
    """Export saved outputs and metrics together, one readable block per case.

    Reads saved results only; does not run or modify any solver.
    """
    output = Path(output) if output is not None else OUTPUT
    names = [('solvers_spidy', 'Spidy'), ('solvers_tanmay', 'Tanmay'), ('solvers', 'Yours')]
    saved = {}
    for name, _ in names:
        path = output / name / 'results.jsonl'
        if path.exists():
            rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            if len({row['case_id'] for row in rows}) != len(rows):
                raise ValueError('Duplicate case IDs in %s' % path)
            saved[name] = {row['case_id']: row for row in rows}
    case_ids = sorted(set().union(*(set(rows) for rows in saved.values())))
    if not case_ids:
        raise ValueError('No saved cases found in %s' % output)

    def errors(expected, actual):
        return sum(a != b for a, b in itertools.zip_longest(expected, actual, fillvalue=None))

    def accuracy(expected, actual):
        return 100 * (1 - errors(expected, actual) / max(len(expected), len(actual), 1))

    lines = [
        'CASE-BY-CASE SOLVER COMPARISON',
        'Run folder: %s' % output.resolve(),
        'Cases: %d' % len(case_ids),
        'Actual = correct reference text. Yours = solvers.py.',
        'Word accuracy compares words at the same positions; character accuracy compares character positions.',
        'Accuracy and cost reduction: higher is better. Cost_fn = saved language-model cost; lower is better.',
        'Fixed errors count corrupted characters restored to the reference; introduced errors count previously correct positions made wrong.',
        'Timeouts score the saved best_state. Missing results and other failures are shown explicitly.', '',
    ]
    for case_id in case_ids:
        available = [rows[case_id] for rows in saved.values() if case_id in rows]
        reference = available[0]
        noisy, clean = reference['input'], reference['expected']
        if any(row['input'] != noisy or row['expected'] != clean or
               row['difficulty'] != reference['difficulty'] for row in available):
            raise ValueError('Case %s has mismatched inputs or references between solvers' % case_id)
        level = {'light': 'Easy', 'medium': 'Medium', 'heavy': 'Hard'}.get(
            reference['difficulty'], reference['difficulty'])
        heading = 'CASE %03d | %s | %d words | %d characters' % (case_id, level, len(clean.split()), len(clean))
        if reference.get('topic'):
            heading += ' | ' + reference['topic']
        lines.extend(['=' * 100, heading, '-' * 100,
                      'Input:  ' + noisy, 'Actual: ' + clean,
                      'Input metrics: word_accuracy=%.2f%% | character_accuracy=%.2f%% | character_errors=%d | cost_fn=%.6f' %
                      (accuracy(clean.split(), noisy.split()), accuracy(clean, noisy), errors(clean, noisy), reference['input_cost']),
                      'Actual metrics: word_accuracy=100.00%% | character_accuracy=100.00%% | character_errors=0 | cost_fn=%.6f' % reference['expected_cost'], ''])
        for name, label in names:
            row = saved.get(name, {}).get(case_id)
            if row is None:
                lines.extend([label + ' output: NOT AVAILABLE', ''])
                continue
            pred = row['prediction']
            remaining = errors(clean, pred)
            fixed = sum(a != b and p == a for a, b, p in itertools.zip_longest(clean, noisy, pred, fillvalue=None))
            introduced = sum(a == b and p != a for a, b, p in itertools.zip_longest(clean, noisy, pred, fillvalue=None))
            changed = errors(noisy, pred)
            lines.extend([
                label + ' output: ' + pred,
                '  Accuracy: word=%.2f%% | character=%.2f%% | exact_match=%s' %
                (accuracy(clean.split(), pred.split()), accuracy(clean, pred), str(pred == clean)),
                '  Errors: remaining=%d | fixed=%d | introduced=%d | changed_positions=%d' %
                (remaining, fixed, introduced, changed),
                '  Cost: cost_fn=%.6f | input_cost_reduction=%.6f | cost_minus_actual=%.6f' %
                (row['output_cost'], row['input_cost'] - row['output_cost'], row['output_cost'] - row['expected_cost']),
                '  Runtime: %.4fs | time_limit=%.4fs | timed_out=%s | error=%s' %
                (row['elapsed_seconds'], row['timeout_seconds'], str(row['timed_out']), row['error'] or 'None'), '',
            ])
    path = output / 'case_comparison.txt'
    path.write_text('\n'.join(lines) + '\n')
    return path


def summarize():
    lines = ['# Solver comparison', '',
             'All solvers use the same corpus examples and language model. '
             'Accuracy is measured against the original corpus sentences. '
             'These corpus-derived examples do not measure performance on unseen data.', '',
             '| Solver | Difficulty | Cases | Initial character errors | Remaining character errors | Word accuracy | Exact sentences | Timeouts | Failures |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    all_rows = {}
    for name in ('solvers_spidy', 'solvers_tanmay', 'solvers'):
        path = OUTPUT / name / 'results.jsonl'
        if not path.exists():
            continue
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        all_rows[name] = rows
        for level in ('light', 'medium', 'heavy', 'all'):
            group = [r for r in rows if level == 'all' or r['difficulty'] == level]
            if not group:
                continue
            lines.append('| %s | %s | %d | %d | %d | %.2f%% | %d | %d | %d |' % (
                name, level, len(group), sum(r['initial_errors'] for r in group),
                sum(r['remaining_errors'] for r in group),
                100 * sum(r['correct_words'] for r in group) / sum(r['words'] for r in group),
                sum(r['exact_match'] for r in group), sum(r['timed_out'] for r in group),
                sum(bool(r['error']) for r in group)))
    for name, rows in all_rows.items():
        if rows:
            lines.extend(['', '%s: %.2f seconds per example; %d completed examples.' %
                          (name, rows[0]['timeout_seconds'], len(rows)), ''])
    for first_name, second_name in itertools.combinations(all_rows, 2):
        first = {r['case_id']: r for r in all_rows[first_name]}
        second = {r['case_id']: r for r in all_rows[second_name]}
        pairs = [(first[i], second[i]) for i in sorted(first.keys() & second.keys())]
        wins_a = sum(a['remaining_errors'] < b['remaining_errors'] for a, b in pairs)
        wins_b = sum(b['remaining_errors'] < a['remaining_errors'] for a, b in pairs)
        lines.extend(['Pairwise character-error comparison across %d shared examples: '
                      '%s wins %d, %s wins %d, ties %d.' %
                      (len(pairs), first_name, wins_a, second_name, wins_b,
                       len(pairs) - wins_a - wins_b), ''])
    lines.extend(['Timeouts preserve each solver\'s best_state and are expected for solvers '
                  'that search indefinitely. Failures are reported separately. '
                  'Metrics include the saved output even when a case times out or fails.', ''])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'summary.md').write_text('\n'.join(lines) + '\n')
    grouped = []
    labels = {'solvers': 'Yours', 'solvers_spidy': 'Spidy', 'solvers_tanmay': 'Tanmay'}
    for difficulty, label in [('light', 'Easy'), ('medium', 'Medium'), ('heavy', 'Hard')]:
        for name, rows in all_rows.items():
            group = [r for r in rows if r['difficulty'] == difficulty]
            if not group:
                continue
            grouped.append(dict(difficulty=label, solver=labels[name], cases=len(group),
                                word_accuracy_percent=100 * sum(r['correct_words'] for r in group) / sum(r['words'] for r in group),
                                exact_sentences=sum(r['exact_match'] for r in group),
                                remaining_character_errors=sum(r['remaining_errors'] for r in group),
                                mean_input_cost=sum(r['input_cost'] for r in group) / len(group),
                                mean_output_cost=sum(r['output_cost'] for r in group) / len(group)))
    if grouped:
        with (OUTPUT / 'difficulty_scores.csv').open('w', newline='') as target:
            writer = csv.DictWriter(target, fieldnames=list(grouped[0]))
            writer.writeheader()
            writer.writerows(grouped)
        table = ['# Scores by difficulty', '',
                 'Easy: 5% corruption; medium: 10%; hard: 20%. All solvers use the same examples and time limit.', '',
                 '| Difficulty | Solver | Cases | Word accuracy | Exact sentences | Remaining character errors | Average model cost |',
                 '|---|---|---:|---:|---:|---:|---:|']
        table.extend('| {difficulty} | {solver} | {cases} | {word_accuracy_percent:.2f}% | {exact_sentences}/{cases} | {remaining_character_errors} | {mean_output_cost:.3f} |'.format(**row) for row in grouped)
        table.extend(['', 'Higher accuracy is better; lower model cost is better. Compare model costs within each difficulty group.'])
        (OUTPUT / 'difficulty_scores.md').write_text('\n'.join(table) + '\n')
    if all_rows:
        print('Case-by-case outputs and metrics: %s' % export_case_comparison())
    print('\n'.join(lines))


def run(args):
    cases = json.loads(args.examples.read_text())
    matrix = json.loads((ROOT / 'data/conf_matrix.json').read_text())
    solver_class = importlib.import_module(args.solver).SentenceCorrector
    with (ROOT / 'data/lm_model.pkl').open('rb') as source:
        model = pickle.load(source)
    model.unk_prob = 1e-20
    model.set_mode('spell_check')
    folder = OUTPUT / args.solver
    folder.mkdir(parents=True, exist_ok=True)
    if args.limit > len(cases):
        raise ValueError('Requested %d examples, but only %d exist.' % (args.limit, len(cases)))
    manifest = dict(solver=args.solver, timeout=args.timeout, seed=args.seed, cases=cases,
                    solver_sha256=hashlib.sha256((ROOT / (args.solver + '.py')).read_bytes()).hexdigest(),
                    confusion_matrix=matrix)
    manifest_path = folder / 'manifest.json'
    if manifest_path.exists():
        if not args.resume:
            raise ValueError('This output folder already contains a run. Use --resume or choose a new --output.')
        if json.loads(manifest_path.read_text()) != manifest:
            raise ValueError('Solver code, settings, or examples changed; choose a new --output folder.')
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    cases = cases[:args.limit]
    (folder / 'input.txt').write_text(''.join(case['input'] + '\n' for case in cases))
    (folder / 'expected.txt').write_text(''.join(case['original'] + '\n' for case in cases))
    result_path = folder / 'results.jsonl'
    rows = [json.loads(line) for line in result_path.read_text().splitlines() if line] if result_path.exists() else []
    assert [r['case_id'] for r in rows] == list(range(1, len(rows) + 1))
    if len(rows) > len(cases):
        raise ValueError('Saved results exceed the requested limit; use a fresh output folder.')

    def expire(signum, frame):
        raise SearchDeadline('Per-case time limit reached')

    previous = signal.signal(signal.SIGALRM, expire)
    try:
        with open(os.devnull, 'w') as quiet:
            indices = ([index for index, row in enumerate(rows) if row['error']]
                       if args.retry_errors else []) + list(range(len(rows), len(cases)))
            for index in indices:
                case = cases[index]
                random.seed(args.seed + index)
                solver = solver_class(model, matrix)
                timed_out, error = False, ''
                started = time.monotonic()
                try:
                    with contextlib.redirect_stdout(quiet):
                        signal.setitimer(signal.ITIMER_REAL, args.timeout)
                        if args.solver == 'solvers':
                            solver.search(case['input'], result_path=folder / 'passes.txt')
                        else:
                            solver.search(case['input'])
                except SearchDeadline:
                    timed_out = True
                except Exception as exc:
                    error = '%s: %s' % (type(exc).__name__, exc)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                elapsed = time.monotonic() - started
                pred = solver.best_state
                if not isinstance(pred, str):
                    error = error or 'Solver did not save a string best_state'
                    pred = case['input']
                clean = case['original']
                # The assignment's operators preserve length; flag violations.
                if len(pred) != len(clean):
                    error = error or 'Output length differs from original'
                remaining = sum(a != b for a, b in zip(clean, pred)) + abs(len(clean) - len(pred))
                words, predicted_words = clean.split(), pred.split()
                row = dict(case_id=index + 1, corpus_line=case['corpus_line'],
                           topic=case.get('topic', ''),
                           difficulty=case['difficulty'], input=case['input'], expected=clean,
                           prediction=pred, initial_errors=case['substitutions'],
                           remaining_errors=remaining, words=len(words),
                           correct_words=sum(a == b for a, b in zip(words, predicted_words)),
                           exact_match=pred == clean, input_cost=model(case['input']),
                           output_cost=model(pred), expected_cost=model(clean),
                           elapsed_seconds=elapsed, timeout_seconds=args.timeout,
                           timed_out=timed_out, error=error)
                if index < len(rows):
                    rows[index] = row
                else:
                    rows.append(row)
                checkpoint = result_path.with_suffix('.tmp')
                checkpoint.write_text(''.join(json.dumps(saved) + '\n' for saved in rows))
                checkpoint.replace(result_path)
                if (index + 1) % 25 == 0 or error or index == len(cases) - 1:
                    print('%s: %d/%d completed; latest errors %d -> %d%s' %
                          (args.solver, index + 1, len(cases), case['substitutions'], remaining,
                           ('; ' + error) if error else ''), flush=True)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    (folder / 'predictions.txt').write_text(''.join(r['prediction'] + '\n' for r in rows))
    fields = [key for key in rows[0] if key not in ('input', 'expected', 'prediction')]
    with (folder / 'metrics.csv').open('w', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    print('%s finished: %s' % (args.solver, folder), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solver', choices=['solvers_spidy', 'solvers_tanmay', 'solvers'])
    parser.add_argument('--timeout', type=float, default=2)
    parser.add_argument('--seed', type=int, default=333)
    parser.add_argument('--limit', type=int, default=100,
                        help='Number of examples to compare, in source order (default: 100)')
    parser.add_argument('--summarize', action='store_true')
    parser.add_argument('--retry-errors', action='store_true',
                        help='Retry saved cases that failed before continuing')
    parser.add_argument('--output', type=Path,
                        help='Output folder; defaults to a fresh timestamped folder under results/')
    parser.add_argument('--examples', type=Path,
                        default=ROOT / 'data/long_corpus_examples/examples.json',
                        help='Examples JSON; defaults to the 100 longer contextual passages')
    parser.add_argument('--resume', action='store_true',
                        help='Resume a previous run; requires --output and matching settings')
    arguments = parser.parse_args()
    if not math.isfinite(arguments.timeout) or arguments.timeout <= 0 or arguments.limit <= 0:
        parser.error('--timeout must be finite and positive; --limit must be positive')
    if arguments.resume and not arguments.output:
        parser.error('--resume requires the previous --output folder')
    if arguments.output:
        OUTPUT = arguments.output.resolve()
    elif not arguments.summarize:
        OUTPUT = ROOT / 'results' / ('comparison_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    if arguments.summarize:
        summarize()
    else:
        if not hasattr(signal, 'setitimer'):
            parser.error('This script requires macOS or Linux for per-case signal timers')
        arguments.examples = arguments.examples.expanduser().resolve()
        if not arguments.examples.exists():
            if arguments.examples == ROOT / 'data/long_corpus_examples/examples.json':
                subprocess.run([sys.executable, str(ROOT / 'generate_long_examples.py'),
                                '--seed', str(arguments.seed)], check=True)
            else:
                parser.error('Examples file does not exist: %s' % arguments.examples)
        selected = [arguments.solver] if arguments.solver else ['solvers', 'solvers_spidy', 'solvers_tanmay']
        print('Output folder: %s' % OUTPUT, flush=True)
        print('Up to %.1f minutes: %d solvers x %d examples x %.2f seconds.' %
              (len(selected) * arguments.limit * arguments.timeout / 60,
               len(selected), arguments.limit, arguments.timeout), flush=True)
        try:
            for name in selected:
                arguments.solver = name
                print('\nRunning %s...' % name, flush=True)
                run(arguments)
        except KeyboardInterrupt:
            print('\nInterrupted. Completed cases are saved. Resume with the same settings and --output "%s" --resume.' % OUTPUT)
            sys.exit(130)
        summarize()
        print('\nEasy / medium / hard comparison:\n')
        print((OUTPUT / 'difficulty_scores.md').read_text())
        print('Reports and predictions saved in: %s' % OUTPUT)
