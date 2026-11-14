# Solver comparison

All solvers use the same corpus examples and language model. Accuracy is measured against the original corpus sentences. These corpus-derived examples do not measure performance on unseen data.

| Solver | Difficulty | Cases | Initial character errors | Remaining character errors | Word accuracy | Exact sentences | Timeouts | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| solvers_spidy | light | 34 | 564 | 63 | 98.37% | 19 | 34 | 0 |
| solvers_spidy | medium | 33 | 1092 | 286 | 93.17% | 1 | 33 | 0 |
| solvers_spidy | heavy | 33 | 2197 | 1142 | 77.94% | 0 | 33 | 0 |
| solvers_spidy | all | 100 | 3853 | 1491 | 89.91% | 20 | 100 | 0 |
| solvers_tanmay | light | 34 | 564 | 434 | 81.40% | 3 | 34 | 0 |
| solvers_tanmay | medium | 33 | 1092 | 968 | 63.05% | 0 | 33 | 0 |
| solvers_tanmay | heavy | 33 | 2197 | 2109 | 36.23% | 0 | 33 | 0 |
| solvers_tanmay | all | 100 | 3853 | 3511 | 60.43% | 3 | 100 | 0 |
| solvers | light | 34 | 564 | 42 | 98.73% | 15 | 34 | 0 |
| solvers | medium | 33 | 1092 | 116 | 97.19% | 8 | 33 | 0 |
| solvers | heavy | 33 | 2197 | 1043 | 79.40% | 0 | 33 | 0 |
| solvers | all | 100 | 3853 | 1201 | 91.84% | 23 | 100 | 0 |

solvers_spidy: 2.00 seconds per example; 100 completed examples.


solvers_tanmay: 2.00 seconds per example; 100 completed examples.


solvers: 2.00 seconds per example; 100 completed examples.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 95, solvers_tanmay wins 0, ties 5.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 19, solvers wins 60, ties 21.

Pairwise character-error comparison across 100 shared examples: solvers_tanmay wins 1, solvers wins 95, ties 4.

Timeouts preserve each solver's best_state and are expected for solvers that search indefinitely. Failures are reported separately. Metrics include the saved output even when a case times out or fails.

