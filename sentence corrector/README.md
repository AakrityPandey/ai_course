# Sentence corrector

The corrector reconstructs text containing character-recognition errors. It uses a confusion matrix to identify possible substitutions and a language model to decide which spelling fits the surrounding words. The active implementation is [solvers.py](solvers.py).

## Run a correction

From the repository root, enter the project folder. On macOS and Linux, both runners use Python’s built-in timer. You can use your current Python environment.

```sh
cd "sentence corrector"
python run.py -src data/input.txt -tar predictions.txt -tm 2
```

Supply one input per line. The command writes one corrected line per input to `predictions.txt`. **Set a positive time limit with `-tm`.** The budget applies separately to each input. For nonempty text, the solver keeps searching even after a pass finds no improvement. The runner recovers the latest corrected sentence when the timer expires. Omitting `-tm` disables the timer.

To write each prediction followed by its language-model cost, use the scored runner. Lower cost means the model prefers the text.

```sh
python run_with_scores.py -src data/input.txt -tar predictions_scored.txt -tm 2
```

For the search algorithm and design decisions, see [Sentence correction in the AI course README](../README.md#sentence-correction).

## Evaluate against clean text

Run the single-solver benchmark from this directory on macOS or Linux. It uses a Unix signal timer and refreshes the files in `results/corpus_tests/`.

```sh
python3 test_corpus_inputs.py --seed 333 --timeout 2
```

The benchmark builds 24 cases from passages of one, three, or five corpus lines. Each passage appears at four corruption levels so the clean reference stays fixed while the input gets harder. The [per-case metrics](results/corpus_tests/metrics.csv) record errors fixed, errors introduced, exact matches, model costs, and states visited.

The [saved benchmark](results/corpus_tests/summary.md) records the following results with seed 333 and two seconds per input. These historical figures describe corpus-derived examples. They do not establish accuracy on unseen text or identify the exact solver revision used.

| Eligible characters selected for corruption | Cases | Character errors before → after | Word accuracy | Exact matches |
| --- | ---: | ---: | ---: | ---: |
| 0% | 6 | 0 → 0 | 100.0% | 6/6 |
| 5% | 6 | 82 → 0 | 100.0% | 6/6 |
| 10% | 6 | 164 → 29 | 95.0% | 3/6 |
| 20% | 6 | 328 → 160 | 78.5% | 0/6 |

The [original 100 cases](data/original_100_test_cases.json) and [longer passages](data/long_corpus_examples/) are also available. Earlier multi-solver comparisons are preserved under [results](results/).
