# Chess Clock

A Python chess clock for a Raspberry Pi 4 with a 5-inch 800 × 480 TFT display. Develop and test
locally using Tkinter, then test on the Pi using VS Code Remote SSH.

## Local setup (Windows)

Run these commands in PowerShell from the project root. Python 3.12 with
Tcl/Tk support must be installed:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m chess_clock.ui_tk
```

After setup, only the final command is needed to run the clock. No environment
activation or PowerShell execution-policy change is required. For example,
to start with ten minutes and a five-second increment:

```powershell
.\.venv\Scripts\python.exe -m chess_clock.ui_tk --minutes 10 --increment 5
```

Run the tests with `.\.venv\Scripts\python.exe -m pytest`.
Create a fresh `.venv` on each computer; virtual environments copied from Linux
cannot be used on Windows.

## Local setup (Ubuntu)

Run these commands from the project root:

```bash
sudo apt-get update
sudo apt-get install -y python3-tk python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m tkinter
```

The final command opens a Tkinter test window and requires a graphical desktop.
Tkinter is provided by the operating system, rather than pip.
VS Code is configured to use the project's `.venv` folder on either platform.
If the workspace already has another interpreter selected, use **Python: Select
Interpreter** to select `.venv/Scripts/python.exe` on Windows or
`.venv/bin/python` on Linux.

## Layout

- `src/chess_clock/clock.py`: timing and game state.
- `src/chess_clock/ui_tk.py`: Tkinter UI.
- `src/chess_clock/theme.py`: custom theme, fonts, colours and dimensions.
- `src/chess_clock/displays/`: local preview and TFT display configuration.
- `src/chess_clock/inputs/`: keyboard and physical button adapters.
- `src/chess_clock/assets/images/`: application images.
- `tests/`: automated tests for clock behaviour.

The application provides two countdown timers with start/resume, pause, reset,
and player switching. Display and hardware input modules are placeholders for
future Pi-specific configuration.

## Running the clock

```bash
.venv/bin/chess-clock
# Or choose an initial theme:
.venv/bin/chess-clock --theme breeze
# Set a different starting time and fill the TFT screen:
.venv/bin/chess-clock --minutes 10 --increment 5 --fullscreen
# Equivalent module command with five minutes per player:
.venv/bin/python -m chess_clock.ui_tk
```

The UI uses `tkinter.ttk` widgets with `ttkthemes` and defaults to `chess-clock`,
a custom theme that inherits the `black` theme's widgets and appearance.
Use `--theme` to override the theme at launch. The window opens with an 800 × 480
client area matching the target screen resolution. The same Tkinter UI will
run on the Pi's graphical desktop. See the
[ttkthemes documentation](https://ttkthemes.readthedocs.io/en/latest/example.html).

### Customizing the theme

Edit `src/chess_clock/theme.py` and restart the application:

- `FONTS`: player titles, status text, buttons, settings headings and numbers,
  timer digits and fractional digits. Positive sizes use points; timer fonts
  use negative pixel sizes and automatically fit their available space.
- `COLORS`: active, inactive and expired timers, progress bars, warnings,
  dividers and text shadows.
- `SIZES` and `PADDING`: window dimensions, spacing, shadow offset, line widths
  and button proportions. The middle button has twice the column weight of
  either side button, giving it half of the control row.

The original `black` theme is kept intact when using `chess-clock`.
Other themes remain available through `--theme black`, `--theme breeze`, etc.;
the application's font and layout settings also apply to those themes.

### Controls

- The pre-game settings screen opens first. Use the large **− / +** buttons to
  choose **starting minutes** (1–180) and **increment seconds per move** (0–60).
  The settings apply equally to both players; defaults are five minutes and no
  increment. There are no hour or starting-second fields.
- Touch **Continue to clock** to review the timers, then **Play** to play.
  **Settings** returns to setup before the game starts. Settings are locked once
  play begins, including while paused.
- Left defaults to White and
  right to Black. Before Play, press either rocker to choose colors: whichever
  side pressed last becomes Black, and the opposite side becomes White.
  The left/right timer labels update immediately. White always moves first.
- Use the single **Play / Pause / Resume** button to begin, pause both clocks, or continue.
  **Reset** returns the button to **Play**.
- Use **Left arrow** and **Right arrow** to emulate each side of the rocker,
  regardless of color. The on-screen player testing buttons are hidden.
  During play, the active player presses their side after moving to start the
  opponent's clock. The increment is added to the player who just moved.
  Inactive-player presses are ignored, and increments are not awarded during
  setup, while paused, or after time expires.
- Play locks color assignments for the game, including while paused. Rocker
  presses have no effect while paused or after a timeout.
- Press **Reset** twice within five seconds to reset. The first press shows
  **Reset? 5**, counting down each second while play continues. If unconfirmed,
  the button returns to **Reset** and the next press starts a fresh countdown.
  After a player runs out of time, a single press resets immediately.
  A confirmed reset restores both timers to the chosen starting time and stops the game
  on the clock screen. Player colors, starting time and increment are retained;
  White is ready to move first. Color selection and **Settings** are available
  again before restarting.
- When a player reaches zero, the game stops and highlights the expired timer.
  Reset to begin another game.
- **Escape** exits fullscreen mode.

The countdown uses monotonic elapsed time, independently of the 50 ms UI update
schedule. Physical GPIO rocker wiring is not implemented yet.
The bottom status line shows the turn number, starting at **Turn 1** and
increasing each time Black ends their move and play returns to White.
Reset restores the counter to **Turn 1**.

Each player's heading also shows their session win count. Scores belong to the
left/right players and are retained when colours change or the clock is reset.
Timeout awards one win to the opponent automatically. To record a game decided
before timeout, press **Reset** while playing or paused: for the five-second confirmation window,
the headings become **Winner - Left** and **Winner - Right** buttons. Selecting
one records that player's win and resets the clock. A normal confirmed reset
awards neither player a win. **Reset win count** in settings clears both scores.
Win counts start at 0–0 when the application launches.

While paused or after time expires, each player's clock shows their average,
longest and shortest completed move times in seconds. Paused time and increments
are excluded, and the unfinished move is not counted. A dash means no move has
been completed yet. Resuming restores the turn indicators; reset clears the statistics.

## Testing

```bash
.venv/bin/python -m pytest
```

## Running
From the project folder run:
.venv/bin/chess-clock

Timing tests use a controlled clock without sleeping or requiring a display.
They cover shared settings, increments, switching, rocker input, pause/resume,
reset, expiry and formatting.
Pillow is a runtime dependency for image rendering; pytest is a development extra.

## Raspberry Pi

Target hardware:

- Raspberry Pi 4.
- 5-inch TFT screen, 800 × 480 pixels, landscape orientation.
- Exact screen model, connection interface and touch capability are still to be confirmed.

This TFT replaces the previously considered e-paper display. The UI uses Tkinter
and ttk themes directly on the Pi's graphical display session.

Enable SSH, connect with VS Code Remote SSH, and create a fresh `.venv` on the Pi.
Do not copy the local virtual environment. Install the project there using the
same editable-install command. Screen setup and button GPIO configuration will
be added after confirming the exact screen model and button wiring.

Keep timing logic independent of UI redraws. Running Tkinter on the Pi requires
access to a graphical display session; Remote SSH provides remote development
access but does not automatically show the application's window locally.
