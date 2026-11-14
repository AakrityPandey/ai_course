"""Create light, medium, and heavy corrupted examples for every corpus line."""
import argparse
import json
import random
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=333)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = root / 'data' / 'corpus_examples'
    output.mkdir(parents=True, exist_ok=True)
    matrix = json.loads((root / 'data/conf_matrix.json').read_text())
    rng = random.Random(args.seed)
    records = []
    levels = [('light', .05), ('medium', .10), ('heavy', .20)]
    for line_number, line in enumerate((root / 'data/corpus.txt').read_text().splitlines(), 1):
        if not line.strip():
            continue
        eligible = [i for i, char in enumerate(line) if matrix.get(char)]
        for level, rate in levels:
            chars = list(line)
            count = min(len(eligible), max(1, round(len(eligible) * rate))) if eligible else 0
            for position in rng.sample(eligible, count):
                chars[position] = rng.choice(matrix[chars[position]])
            noisy = ''.join(chars)
            assert len(noisy) == len(line)
            assert sum(a != b for a, b in zip(line, noisy)) == count
            assert all(a == b or b in matrix.get(a, []) for a, b in zip(line, noisy))
            records.append(dict(corpus_line=line_number, difficulty=level,
                                substitutions=count, original=line, input=noisy))
    for level, _ in levels:
        selected = [row for row in records if row['difficulty'] == level]
        (output / ('input_%s.txt' % level)).write_text(''.join(row['input'] + '\n' for row in selected))
    (output / 'expected.txt').write_text(''.join(row['original'] + '\n' for row in records if row['difficulty'] == 'light'))
    (output / 'input_all.txt').write_text(''.join(row['input'] + '\n' for row in records))
    (output / 'expected_all.txt').write_text(''.join(row['original'] + '\n' for row in records))
    (output / 'examples.json').write_text(json.dumps(records, indent=2) + '\n')
    readable = []
    for index in range(0, len(records), len(levels)):
        group = records[index:index + len(levels)]
        readable.extend(['Corpus line %d' % group[0]['corpus_line'],
                         'Original: ' + group[0]['original']])
        readable.extend('%s (%d substitutions): %s' %
                        (row['difficulty'].capitalize(), row['substitutions'], row['input']) for row in group)
        readable.append('')
    (output / 'examples.txt').write_text('\n'.join(readable) + '\n')
    (output / 'README.md').write_text(
        '# Examples for every corpus sentence\n\n'
        'Seed: %d. %d original sentences, %d corrupted examples.\n\n'
        'Each original has light (5%%), medium (10%%), and heavy (20%%) corruption '
        'among characters supported by conf_matrix.json, rounded to the nearest '
        'character with at least one change when possible. Spaces are preserved.\n\n'
        '- examples.txt: original and all three examples together.\n'
        '- input_light.txt, input_medium.txt, input_heavy.txt: one example per corpus sentence in source order.\n'
        '- expected.txt: matching clean references for any one difficulty file.\n'
        '- input_all.txt and expected_all.txt: all examples and matching references, ordered by corpus line then difficulty.\n'
        '- examples.json: examples with source line numbers and substitution counts.\n\n'
        'Regenerate from A1_fresh: `python3 generate_corpus_examples.py --seed 333`.\n'
        % (args.seed, len(records) // len(levels), len(records)))
    print('Created %d examples for %d corpus sentences in %s' %
          (len(records), len(records) // len(levels), output))


if __name__ == '__main__':
    main()
