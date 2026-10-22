# Examples for every corpus sentence

Seed: 333. 200 original sentences, 600 corrupted examples.

Each original has light (5%), medium (10%), and heavy (20%) corruption among characters supported by conf_matrix.json, rounded to the nearest character with at least one change when possible. Spaces are preserved.

- examples.txt: original and all three examples together.
- input_light.txt, input_medium.txt, input_heavy.txt: one example per corpus sentence in source order.
- expected.txt: matching clean references for any one difficulty file.
- input_all.txt and expected_all.txt: all examples and matching references, ordered by corpus line then difficulty.
- examples.json: examples with source line numbers and substitution counts.

Regenerate from A1_fresh: `python3 generate_corpus_examples.py --seed 333`.
