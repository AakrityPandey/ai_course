# Solver comparison

All solvers use the same corpus examples and language model. Accuracy is measured against the original corpus sentences. These corpus-derived examples do not measure performance on unseen data.

| Solver | Difficulty | Cases | Initial character errors | Remaining character errors | Word accuracy | Exact sentences | Timeouts | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| solvers_spidy | light | 34 | 144 | 0 | 100.00% | 34 | 34 | 0 |
| solvers_spidy | medium | 33 | 280 | 32 | 98.10% | 24 | 33 | 0 |
| solvers_spidy | heavy | 33 | 562 | 177 | 89.16% | 3 | 33 | 0 |
| solvers_spidy | all | 100 | 986 | 209 | 95.79% | 61 | 100 | 0 |
| solvers_tanmay | light | 34 | 144 | 14 | 98.34% | 28 | 34 | 0 |
| solvers_tanmay | medium | 33 | 280 | 47 | 96.58% | 21 | 33 | 0 |
| solvers_tanmay | heavy | 33 | 562 | 229 | 82.89% | 1 | 33 | 0 |
| solvers_tanmay | all | 100 | 986 | 290 | 92.66% | 50 | 100 | 0 |
| solvers | light | 34 | 144 | 7 | 99.26% | 30 | 34 | 0 |
| solvers | medium | 33 | 280 | 20 | 98.29% | 26 | 33 | 0 |
| solvers | heavy | 33 | 562 | 131 | 91.06% | 10 | 33 | 0 |
| solvers | all | 100 | 986 | 158 | 96.23% | 66 | 100 | 0 |

solvers_spidy: 2.00 seconds per example; 100 completed examples.


solvers_tanmay: 2.00 seconds per example; 100 completed examples.


solvers: 2.00 seconds per example; 100 completed examples.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 27, solvers_tanmay wins 5, ties 68.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 18, solvers wins 25, ties 57.

Pairwise character-error comparison across 100 shared examples: solvers_tanmay wins 11, solvers wins 37, ties 52.

Timeouts preserve each solver's best_state and are expected for solvers that search indefinitely. Failures are reported separately. Metrics include the saved output even when a case times out or fails.

