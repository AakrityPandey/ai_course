"""Generate 100 coherent, varied-length passages without replacing old examples."""
import argparse
import itertools
import json
import random
from pathlib import Path


# Each pool combines related corpus clauses with explicitly authored transitions.
# Entries are ordered to form a short report rather than unrelated sentences.
TOPICS = [
    ('currency markets',
     'central banks reviewed conditions in the foreign exchange market',
     ['the recent stability would last', 'under such circumstances the countries',
      'there are signs that central banks', 'while relatively unsuccessful',
      'poehl says currency market intervention', 'the central bank is checking',
      'analysts said the yen also gained'],
     ['dealers said coordinated action had helped restore confidence in trading',
      'officials said monetary policy would remain important in the coming weeks',
      'traders expected further changes in currency prices before the next meeting']),
    ('crop weather',
     'farmers assessed the effect of recent weather on grain crops',
     ['damage was most severe on plants', 'stands in these fields were thin',
      'he said rains some six weeks', 'summerfallow crops were in fair',
      'they said the sunflower maize', 'late season rains damaged soviet'],
     ['agricultural officials said conditions varied across the areas under review',
      'farmers would need more favorable weather before production could recover',
      'the agency said final yields would depend on conditions during harvest']),
    ('oil refining',
     'oil traders reviewed refinery supplies and the outlook for margins',
     ['prices had also been forced down', 'wish said refineries will stockpile',
      'despite these concerns refiners are expecting', 'the soft tone to refining'],
     ['maintenance plans were expected to affect refinery production in the coming weeks',
      'dealers said existing stocks would help customers meet their immediate needs',
      'the industry would watch demand before deciding whether to increase output',
      'analysts said stronger demand could improve profits later in the year']),
    ('offshore exploration',
     'energy companies examined new opportunities for offshore oil and gas exploration',
     ['he suggested that some independents', 'but despite promising indications',
      'santos said tmoc holds', 'the spokesman added cnooc was ready',
      'norwegian companies landed operatorships'],
     ['each project would require further surveys before development could begin',
      'officials said the cost of drilling remained important to investment decisions',
      'companies were reviewing plans for new fields and related transport facilities',
      'the timing of production would depend on reserves and market conditions']),
    ('company acquisitions',
     'several companies reviewed proposed acquisitions and the terms of competing offers',
     ['the company said the agreement is subject', 'the transaction is subject',
      'the company said the offer and withdrawal', 'citicorp said if dixons',
      'great atlantic and pacific tea co said'],
     ['shareholders were asked to review the proposed terms before making a decision',
      'the boards said the final agreements would require further review',
      'advisers said financing and regulatory approval remained important to the transactions',
      'the companies expected to provide more information after discussions were completed']),
    ('vehicle manufacturing',
     'vehicle manufacturers studied changes designed to improve production and fuel economy',
     ['armstrong tire co an armtek', 'raybestos with manufacturing facilities',
      'the company said the lighter weight', 'it said the frame would reduce'],
     ['suppliers were also reviewing the cost of materials used in new vehicles',
      'engineers said the new designs could reduce costs without reducing quality',
      'manufacturers expected demand for replacement parts to remain an important business',
      'the industry said further improvements would depend on testing and investment']),
    ('electronics manufacturing',
     'electronics companies outlined plans for new products and manufacturing agreements',
     ['under the pact california micro devices', 'gtx located in phoenix',
      'under the agreement control data', 'conrac is involved in video displays'],
     ['the companies said demand from business customers would influence production plans',
      'manufacturers were developing equipment for communications and other industrial applications',
      'new supply agreements were expected to improve access to important components',
      'management said product development and service would remain major priorities']),
    ('grain markets',
     'grain traders reported changing supplies and demand in agricultural markets',
     ['it stressed the need to segregate wheat', 'futures traders said tight cash',
      'the grain futures market also intends', 'with futures down processors',
      'this is the second day running', 'if supplies become more difficult'],
     ['dealers said transport costs and available stocks would affect cash prices',
      'exporters were watching demand before making further commitments to buyers',
      'processors said they would review purchases as new crop estimates became available']),
    ('international trade',
     'government officials discussed trade policy and competition in international markets',
     ['to promote trade saudi arabia', 'the united states conducts no trade',
      'he urged american manufacturers', 'but now after some experience',
      'house and senate negotiators', 'organized labor has pressed'],
     ['business leaders said access to foreign markets remained important for growth',
      'officials said new agreements would require further discussions with trading partners',
      'companies were reviewing how changes in trade rules could affect their plans']),
    ('industrial restructuring',
     'industrial companies reviewed costs and management plans after difficult trading conditions',
     ['manufacturing activity showed signs', 'weiss attributed the poor year',
      'securities analysts at major securities', 'he said the company was reorganizing',
      'modern techniques of cost control', 'the new facility will lower'],
     ['management said improving product quality remained a priority during the changes',
      'analysts expected investment decisions to depend on the outlook for orders',
      'companies would review staffing and distribution as demand developed']),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=333)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    corpus = (root / 'data/corpus.txt').read_text().splitlines()
    min_words, max_words = 90, 130
    matrix = json.loads((root / 'data/conf_matrix.json').read_text())
    rng = random.Random(args.seed)
    output = root / 'data/long_corpus_examples'
    output.mkdir(parents=True, exist_ok=True)
    cases, used = [], set()
    bands = [(90, 97), (98, 105), (106, 113), (114, 121), (122, 130)]
    for topic_index, (topic, opening, prefixes, authored) in enumerate(TOPICS):
        fragments = []
        for prefix in prefixes:
            matches = [(i + 1, text) for i, text in enumerate(corpus) if text.startswith(prefix)]
            if len(matches) != 1:
                raise ValueError('Expected exactly one corpus match for %r' % prefix)
            line_number, text = matches[0]
            fragments.append(dict(text=text, corpus_line=line_number))
        fragments.extend(dict(text=text, corpus_line=None) for text in authored)
        fragments.extend(dict(text=text, corpus_line=None) for text in (
            'the report said more details would be available next month',
            'the outlook would be reviewed again later this year'))
        candidates = []
        for count in range(2, len(fragments) + 1):
            for selection in itertools.combinations(fragments, count):
                text = ' '.join([opening] + [part['text'] for part in selection])
                word_count = len(text.split())
                if min_words <= word_count <= max_words:
                    candidates.append((text, selection, word_count))
        for sample in range(10):
            low, high = bands[sample % len(bands)]
            options = [c for c in candidates if low <= c[2] <= high and c[0] not in used]
            if not options:
                raise ValueError('No unique %s passage in word range %d-%d' % (topic, low, high))
            target = rng.randint(low, high)
            closest = min(abs(c[2] - target) for c in options)
            text, selection, word_count = rng.choice([c for c in options if abs(c[2] - target) == closest])
            used.add(text)
            difficulty, rate = [('light', .05), ('medium', .10), ('heavy', .20)][(topic_index * 10 + sample) % 3]
            eligible = [i for i, char in enumerate(text) if matrix.get(char)]
            substitutions = max(1, round(len(eligible) * rate))
            noisy = list(text)
            for position in rng.sample(eligible, substitutions):
                noisy[position] = rng.choice(matrix[text[position]])
            noisy = ''.join(noisy)
            source_lines = [part['corpus_line'] for part in selection if part['corpus_line'] is not None]
            cases.append(dict(case_id=len(cases) + 1, topic=topic,
                              corpus_line=source_lines[0] if source_lines else None,
                              corpus_lines=source_lines, difficulty=difficulty,
                              substitutions=substitutions, words=word_count, characters=len(text),
                              original=text, input=noisy,
                              authored_fragments=[opening] + [p['text'] for p in selection if p['corpus_line'] is None]))
    assert len(cases) == len(used) == 100
    for case in cases:
        assert min_words <= len(case['input'].split()) <= max_words
        assert len(case['input']) == len(case['original'])
        assert sum(a != b for a, b in zip(case['original'], case['input'])) == case['substitutions']
        assert all(a == b or b in matrix.get(a, []) for a, b in zip(case['original'], case['input']))
    (output / 'examples.json').write_text(json.dumps(cases, indent=2) + '\n')
    for field, filename in [('input', 'input.txt'), ('original', 'expected.txt')]:
        (output / filename).write_text(''.join(case[field] + '\n' for case in cases))
    readable = []
    for case in cases:
        readable.extend(['Case {case_id:03d} | {topic} | {difficulty} | {words} words | {characters} characters'.format(**case),
                         'Original: ' + case['original'], 'Input:    ' + case['input'], ''])
    (output / 'examples.txt').write_text('\n'.join(readable) + '\n')
    description = [
        '# Longer contextual examples', '',
        '100 unique passages, ten per topic. Each passage combines related corpus clauses with authored opening or supporting phrases. Corpus line numbers and authored fragments are recorded in examples.json.', '',
        'Length: %d–%d words; %d–%d characters. Passages target 90–130 words, exceeding the previous 80-word cap.' %
        (min(c['words'] for c in cases), max(c['words'] for c in cases), min(c['characters'] for c in cases), max(c['characters'] for c in cases)), '',
        'Difficulty: 34 easy (5% character corruption), 33 medium (10%), 33 hard (20%). Substitutions follow conf_matrix.json. Length varies independently of corruption difficulty.', '',
        'input.txt and expected.txt have matching lines. examples.txt shows readable pairs. This is synthetic test text, not a factual news report or a held-out accuracy benchmark.', '',
        'The exact original 100 short cases are preserved separately in ../original_100_test_cases.json, ../original_100_inputs.txt, and ../original_100_expected.txt. Earlier result folders are unchanged.', '',
        'Regenerate: python3 generate_long_examples.py --seed %d' % args.seed,
    ]
    (output / 'README.md').write_text('\n'.join(description) + '\n')
    print('\n'.join(description))


if __name__ == '__main__':
    main()
