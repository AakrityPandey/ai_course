# Solver comparison

All solvers use the same corpus examples and language model. Accuracy is measured against the original corpus sentences. These corpus-derived examples do not measure performance on unseen data.

| Solver | Difficulty | Cases | Initial character errors | Remaining character errors | Word accuracy | Exact sentences | Timeouts | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| solvers_spidy | light | 34 | 1071 | 197 | 97.21% | 2 | 34 | 0 |
| solvers_spidy | medium | 33 | 2065 | 731 | 91.18% | 0 | 33 | 0 |
| solvers_spidy | heavy | 33 | 4134 | 2496 | 72.40% | 0 | 33 | 0 |
| solvers_spidy | all | 100 | 7270 | 3424 | 87.07% | 2 | 100 | 0 |
| solvers_tanmay | light | 34 | 1071 | 1071 | 75.46% | 0 | 34 | 0 |
| solvers_tanmay | medium | 33 | 2065 | 2065 | 57.09% | 0 | 33 | 0 |
| solvers_tanmay | heavy | 33 | 4134 | 4134 | 31.50% | 0 | 33 | 0 |
| solvers_tanmay | all | 100 | 7270 | 7270 | 54.95% | 0 | 100 | 0 |
| solvers | light | 34 | 1071 | 93 | 98.63% | 11 | 34 | 0 |
| solvers | medium | 33 | 2065 | 566 | 93.12% | 1 | 33 | 0 |
| solvers | heavy | 33 | 4134 | 2469 | 72.59% | 0 | 33 | 0 |
| solvers | all | 100 | 7270 | 3128 | 88.25% | 12 | 100 | 0 |

solvers_spidy: 2.00 seconds per example; 100 completed examples.


solvers_tanmay: 2.00 seconds per example; 100 completed examples.


solvers: 2.00 seconds per example; 100 completed examples.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 100, solvers_tanmay wins 0, ties 0.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 18, solvers wins 68, ties 14.

Pairwise character-error comparison across 100 shared examples: solvers_tanmay wins 0, solvers wins 100, ties 0.

Timeouts preserve each solver's best_state and are expected for solvers that search indefinitely. Failures are reported separately. Metrics include the saved output even when a case times out or fails.

