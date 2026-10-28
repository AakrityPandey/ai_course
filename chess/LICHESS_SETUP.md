# Your course engine on Lichess (Windows)

The connector is installed in `chess/lichess-bot`, at upstream commit
`9cd2be995722ce277a9e35eb7bbf3d6bb9ad2a38`.
Your engine adapter is `course_lichess_engine.py`.
It uses the course engine's material values and minimax with alpha-beta pruning;
python-chess supplies full online chess rules. It does not use Stockfish or
external analysis. Iterative deepening caps search at depth 3 and roughly
2 seconds per move, reduced when the clock is low. Minimax score printing is disabled.

For notebook controls, use the **Play online on Lichess** section in
`chess.ipynb`: run the imports/setup cell, then `start_bot()`, check
`bot_status()`, and use `challenge_bot("opponent_username")`.
Stop any terminal copy first, and keep the notebook kernel running during games.
Run `stop_bot()` after the game. Connector logs are saved to `lichess_bot.log`.

## 1. Create the account and token

Create a new dedicated account: https://lichess.org/signup
Do not play any games on it before upgrading it to BOT.

While signed in to that account, create a token with only **Play games with
the bot API** (`bot:play`):
https://lichess.org/account/oauth/token/create?scopes[]=bot:play&description=ai-course-bot

Paste only the token into `chess/lichess.token` and save it. This local file
is excluded from Git and is read by both scripts. Do not put quotes or
`token:` around it. Keep it private. An environment variable named
`LICHESS_BOT_TOKEN` takes precedence; if neither is set, a hidden prompt is used.

## 2. First launch

From PowerShell in `C:\Users\ritaa\Documents\trying\ai_course`:

```powershell
.\.venv\Scripts\python.exe chess\start_lichess.py --check
.\.venv\Scripts\python.exe chess\start_lichess.py --upgrade
```

**The second command permanently converts the token's account to BOT.**
Use the dedicated new account, not your personal playing account.
It then starts the connector, using the saved token.

For subsequent launches:

```powershell
.\.venv\Scripts\python.exe chess\start_lichess.py
```

Leave this terminal running during games. Ctrl+C stops the connector.

## 3. Challenge another bot

Choose an online bot from https://lichess.org/player/bots
In a second PowerShell terminal in `ai_course`, substitute its username:

```powershell
.\.venv\Scripts\python.exe chess\challenge_bot.py OPPONENT_USERNAME
```

The saved BOT token is used automatically. This sends one casual standard 5-minute game
with a 3-second increment. The other bot must accept. Watch the game at the
returned Lichess link. The account will also accept matching incoming bot
challenges, one game at a time. Automatic matchmaking is initially disabled.

Games are saved under `chess/game_records/`. The Pygame notebook remains
available for local games; online games use the Lichess board.

## Offline checks and reinstall

```powershell
.\.venv\Scripts\python.exe chess\check_lichess_engine.py
```

If the ignored connector directory is missing on a different computer:

```powershell
git clone https://github.com/lichess-bot-devs/lichess-bot.git chess/lichess-bot
git -C chess/lichess-bot checkout 9cd2be995722ce277a9e35eb7bbf3d6bb9ad2a38
.\.venv\Scripts\python.exe -m pip install -r chess/lichess-bot/requirements.txt
```

The launcher registers the custom engine and merges `lichess_config.yml`
over the connector's defaults on each launch. Edit that file for acceptance
preferences. The connector retains its upstream license in its directory.

References:
- https://lichess.org/api#tag/Bot
- https://github.com/lichess-bot-devs/lichess-bot/wiki/Create-a-homemade-engine
- https://github.com/lichess-bot-devs/lichess-bot/wiki/How-to-create-a-Lichess-OAuth-token
- https://github.com/lichess-bot-devs/lichess-bot/wiki/Upgrade-to-a-BOT-account
