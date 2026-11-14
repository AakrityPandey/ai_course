# Solver comparison

All solvers use the same corpus examples and language model. Accuracy is measured against the original corpus sentences. These corpus-derived examples do not measure performance on unseen data.

| Solver | Difficulty | Cases | Initial character errors | Remaining character errors | Word accuracy | Exact sentences | Timeouts | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| solvers_spidy | light | 34 | 144 | 2 | 99.82% | 33 | 34 | 0 |
| solvers_spidy | medium | 33 | 280 | 37 | 97.72% | 22 | 33 | 0 |
| solvers_spidy | heavy | 33 | 562 | 184 | 88.59% | 4 | 33 | 0 |
| solvers_spidy | all | 100 | 986 | 223 | 95.42% | 59 | 100 | 0 |
| solvers_tanmay | light | 34 | 144 | 8 | 99.26% | 30 | 34 | 0 |
| solvers_tanmay | medium | 33 | 280 | 43 | 97.15% | 20 | 33 | 0 |
| solvers_tanmay | heavy | 33 | 562 | 203 | 86.88% | 1 | 33 | 0 |
| solvers_tanmay | all | 100 | 986 | 254 | 94.48% | 51 | 100 | 0 |
| solvers | light | 34 | 144 | 6 | 99.26% | 30 | 34 | 0 |
| solvers | medium | 33 | 280 | 29 | 97.91% | 23 | 33 | 0 |
| solvers | heavy | 33 | 562 | 184 | 86.88% | 5 | 33 | 0 |
| solvers | all | 100 | 986 | 219 | 94.73% | 58 | 100 | 0 |

solvers_spidy: 2.00 seconds per example; 100 completed examples.


solvers_tanmay: 2.00 seconds per example; 100 completed examples.


solvers: 2.00 seconds per example; 100 completed examples.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 22, solvers_tanmay wins 7, ties 71.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 21, solvers wins 19, ties 60.

Pairwise character-error comparison across 100 shared examples: solvers_tanmay wins 15, solvers wins 27, ties 58.

Timeouts preserve each solver's best_state and are expected for solvers that search indefinitely. Failures are reported separately. Metrics include the saved output even when a case times out or fails.

