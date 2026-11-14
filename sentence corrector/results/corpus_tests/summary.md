# Corpus test results

Seed: 333. Timeout: 2.00 seconds per input. 24 cases.
Inputs combine 1, 3, or 5 corpus lines; corruption replaces 0%, 5%, 10%, or 20% of eligible characters using conf_matrix.json.
The solver intentionally runs until timeout; predictions are its saved best_state.
Corpus-derived evaluation is not an independent held-out accuracy estimate.

| Difficulty | Cases | Initial errors | Remaining errors | Word accuracy | Exact matches |
|---|---:|---:|---:|---:|---:|
| clean | 6 | 0 | 0 | 100.0% | 6 |
| light | 6 | 82 | 0 | 100.0% | 6 |
| medium | 6 | 164 | 29 | 95.0% | 3 |
| heavy | 6 | 328 | 160 | 78.5% | 0 |

Re-run from A1_fresh: `python3 test_corpus_inputs.py --timeout 2 --seed 333`
Generated input.txt and expected.txt contain corresponding lines. metrics.csv contains per-case scores and accuracy.
The benchmark uses a Unix signal timer because the optional driver timeout dependency is unavailable. Solver and supporting files are unchanged.
