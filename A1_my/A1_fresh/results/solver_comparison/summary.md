# Solver comparison

All solvers use the same corpus examples and language model. Accuracy is measured against the original corpus sentences. These corpus-derived examples do not measure performance on unseen data.

| Solver | Difficulty | Cases | Initial character errors | Remaining character errors | Word accuracy | Exact sentences | Timeouts | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| solvers_spidy | light | 34 | 144 | 0 | 100.00% | 34 | 34 | 0 |
| solvers_spidy | medium | 33 | 280 | 21 | 98.86% | 27 | 33 | 0 |
| solvers_spidy | heavy | 33 | 562 | 146 | 91.83% | 6 | 33 | 0 |
| solvers_spidy | all | 100 | 986 | 167 | 96.92% | 67 | 100 | 0 |
| solvers_tanmay | light | 34 | 144 | 0 | 100.00% | 34 | 34 | 0 |
| solvers_tanmay | medium | 33 | 280 | 37 | 96.96% | 23 | 33 | 0 |
| solvers_tanmay | heavy | 33 | 562 | 188 | 87.45% | 3 | 33 | 0 |
| solvers_tanmay | all | 100 | 986 | 225 | 94.85% | 60 | 100 | 0 |
| solvers | light | 34 | 144 | 7 | 99.26% | 30 | 34 | 0 |
| solvers | medium | 33 | 280 | 36 | 96.77% | 16 | 33 | 0 |
| solvers | heavy | 33 | 562 | 147 | 89.16% | 5 | 33 | 0 |
| solvers | all | 100 | 986 | 190 | 95.10% | 51 | 100 | 0 |

solvers_spidy: 2.00 seconds per example; 100 completed examples.


solvers_tanmay: 2.00 seconds per example; 100 completed examples.


solvers: 2.00 seconds per example; 100 completed examples.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 17, solvers_tanmay wins 3, ties 80.

Pairwise character-error comparison across 100 shared examples: solvers_spidy wins 34, solvers wins 18, ties 48.

Pairwise character-error comparison across 100 shared examples: solvers_tanmay wins 29, solvers wins 26, ties 45.

Timeouts preserve each solver's best_state and are expected for solvers that search indefinitely. Failures are reported separately. Metrics include the saved output even when a case times out or fails.


Your solvers.py initially failed because removed parameters D and greedy_passes were still referenced. The run uses the minimal repair: initial depth 1, increasing each pass, and removal of obsolete parameter checks. The original failed run is preserved in solvers_failed_undefined_parameters. One logging-related timeout failure was retried successfully.
