# Longer contextual examples

100 unique passages, ten per topic. Each passage combines related corpus clauses with authored opening or supporting phrases. Corpus line numbers and authored fragments are recorded in examples.json.

Length: 90–129 words; 557–904 characters. Passages target 90–130 words, exceeding the previous 80-word cap.

Difficulty: 34 easy (5% character corruption), 33 medium (10%), 33 hard (20%). Substitutions follow conf_matrix.json. Length varies independently of corruption difficulty.

input.txt and expected.txt have matching lines. examples.txt shows readable pairs. This is synthetic test text, not a factual news report or a held-out accuracy benchmark.

The exact original 100 short cases are preserved separately in ../original_100_test_cases.json, ../original_100_inputs.txt, and ../original_100_expected.txt. Earlier result folders are unchanged.

Regenerate: python3 generate_long_examples.py --seed 333
