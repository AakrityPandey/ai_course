# Assignment 1 — fresh starter

## Compare the three solvers

Open `compare_solvers.ipynb` and run its cells. `DATASET = "long"` uses the
new 100 contextual passages (90–129 words, 557–904 characters).
`DATASET = "original"` uses the preserved original 100 short cases.
The notebook defaults to 100 cases and two seconds per solver per case.

The exact original cases are saved separately as:

- `data/original_100_test_cases.json`: all original case metadata and text.
- `data/original_100_inputs.txt`: original corrupted inputs, in test order.
- `data/original_100_expected.txt`: corresponding clean references.

New passages and their clean references are in `data/long_corpus_examples/`.
They combine related corpus clauses with authored phrases on ten topics.
The generator targets 90–130 words per passage, above the previous 80-word
cap. The old datasets and old comparison results are preserved.

From `A1_fresh`, run:

```sh
python3 compare_corpus_solvers.py --limit 100 --timeout 2
```

This runs `solvers.py`, `solvers_spidy.py`, and `solvers_tanmay.py` separately
on the new 100 longer examples, using two seconds per example.
It takes about 10 minutes. Each run creates a fresh folder under `results/`,
so editing a solver and running the command again produces new results.
Requires Python 3.7+ on macOS/Linux; no extra packages are needed.
Missing longer examples are created automatically from `data/corpus.txt`.
To select the old cases on the command line, add
`--examples data/original_100_test_cases.json`.

The script prints easy, medium, and hard scores and saves:

- `case_comparison.txt`: each input, correct reference, Spidy/Tanmay/your
  outputs, word and character accuracy, exact match, character error counts,
  language-model cost and cost improvement, runtime, and timeout/error status.
- `difficulty_scores.md` and `.csv`: word accuracy, exact sentence matches,
  remaining character errors, and average language-model cost by difficulty.
- `summary.md`: overall and per-difficulty results for each solver.
- One folder per solver containing `predictions.txt`, `metrics.csv`, and
  `results.jsonl` with each input, expected sentence, and prediction.

Higher accuracy is better; lower model cost is better. These examples come
from the corpus and are not a held-out evaluation. Easy, medium, and hard
mean 5%, 10%, and 20% character corruption respectively. For 100 examples,
the groups contain 34, 33, and 33 examples.

For a quick check, use `--limit 3 --timeout 0.1`. For a custom output folder
and an interrupted run:

```sh
python3 compare_corpus_solvers.py --limit 100 --timeout 2 --output results/my_run
python3 compare_corpus_solvers.py --limit 100 --timeout 2 --output results/my_run --resume
```

Resume requires the same solver code, settings, and examples. Use a new output
folder after changing a solver. You can also select just one solver with
`--solver solvers`, `--solver solvers_spidy`, or `--solver solvers_tanmay`.

Implement `SentenceCorrector.search()` in `solvers.py`. This is a clean
starter, not a completed solver; it raises `NotImplementedError` until you
replace the TODO with your algorithm.

The PDF occasionally calls this file `solver.py`, but the supplied driver
imports `solvers.py`, and the submission instructions use `solvers.py`.

## Requirements

- Use search-based methods and Python 3.7-compatible standard-library code.
- Evaluate candidate strings with `self.cost_fn(state)`; lower cost is better.
- Keep `self.best_state` updated throughout the search for timeout handling.
- Do not use global variables or threading libraries in your implementation.
- Leave the supplied supporting files unchanged.

## Run after implementing

From this folder, create and activate the supplied environment:

```sh
conda env create -f environment.yml
conda activate aia1
python run.py -src data/input.txt -tar data/pred.txt -tm 2
python run_with_scores.py -src data/input.txt -tar data/pred_with_score.txt -tm 5
```

The timeout is per input sentence. The environment file is copied as supplied
and uses older dependency versions; environment installation has not been tested.

## Submission

Submit `solvers.py` and your own `report.txt` inside the folder/zip naming
format specified in the PDF. The report should explain your algorithm,
state representation, operators, transition costs, solution criterion, and
branching factor. The PDF limits the report to two pages.

Supporting files and the five data files listed in the assignment were copied
from `A1_my/A1_A`. Previous solutions, reports, extra datasets, predictions,
archives, and bytecode caches were not copied. These local supporting files
have not been verified against the original Moodle starter archive.
