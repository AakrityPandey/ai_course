# Offline chess matches

Open `offline_benchmark.ipynb` with the shared ai_course Python kernel.
Run its cells in order. It does not use Lichess, your account, or your token.
Both downloaded engines are already installed for this Windows computer:

- Stockfish 19: official universal Windows x86-64 build, with source and
  GPLv3 license included. Download URL and checksum are recorded in
  `offline_engines/stockfish/download.json`.
- Sunfish: source at commit `e396948acbd80cdcbad3dccfb07e878fba9df8f4`,
  including its license, in `offline_engines/sunfish`.

Sources:
https://github.com/official-stockfish/Stockfish/releases/tag/sf_19
https://github.com/thomasahle/sunfish

The notebook compares random play, Sunfish, and three Stockfish skill
levels. Each pair plays a seeded four-ply opening with colors reversed.
The course bot uses the same search function as the Lichess adapter;
it also shares that adapter's material values. Full chess legality is
provided by python-chess for all competitors.

Settings include number of pairs, initial clock time, increment, course search
depth, and move limit. The default is 5+0: 300 seconds per player, with no
additional time after moves. Actual thinking time is deducted,
including engine communication overhead. Flag falls are scored as losses
(or draws if the opponent has insufficient mating material). UCI engines
receive both clocks and increments and manage their own search time. The
course bot uses its Lichess clock-aware budget and depth cap. Clocks are
saved in PGN move comments and final clock values are saved in games.csv.
The seeded opening is supplied before the clocks start.
Stockfish runs with one thread and 32 MB hash. Weak skill levels and small
samples do not measure a human Elo rating. Random seeds fix openings and
the random opponent; engine tie breaking and UCI engines may vary.

Each run saves settings, a source fingerprint, individual PGNs, games.csv,
and summary.csv under a new `offline_results` directory. Completed games
are saved as they finish. Draws may be claimed by either side when legal.
Games stopped by the move limit are unfinished, and engine errors are
reported separately; neither contributes to the displayed score percentage.

For meaningful comparisons, increase the number of pairs, use the same
settings and openings across bot revisions, and inspect unfinished/error
counts alongside win/draw/loss totals.

The downloaded engine directories and generated results are excluded from
Git. The existing Lichess setup is independent and remains available.
