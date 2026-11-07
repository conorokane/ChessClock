"""Touch-friendly chess clock for an 800 × 480 screen."""

import argparse
from tkinter import StringVar, ttk

from ttkthemes import ThemedTk

from chess_clock.clock import ChessClock, format_time


class ClockUI:
    def __init__(self, window: ThemedTk, clock: ChessClock):
        self.window = window
        self.clock = clock
        self._job = None
        window.title("Chess Clock")
        window.geometry("800x480")
        window.minsize(800, 480)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        window.protocol("WM_DELETE_WINDOW", self.close)

        content = ttk.Frame(window, padding=16)
        self.game_frame = content
        content.grid(sticky="nsew")
        content.columnconfigure((0, 1), weight=1, uniform="players")
        content.rowconfigure(1, weight=1)
        header = ttk.Frame(content)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="CHESS CLOCK", font=("DejaVu Sans", 16, "bold")).pack(side="left")
        self.settings_button = ttk.Button(header, text="Settings", command=self.show_settings)
        self.settings_button.pack(side="left", padx=12)
        self.theme = StringVar(window, value=ttk.Style(window).theme_use())
        themes = ttk.Combobox(header, textvariable=self.theme, state="readonly",
                              values=sorted(window.get_themes()), width=12)
        themes.pack(side="right")
        themes.bind("<<ComboboxSelected>>", self.change_theme)
        ttk.Label(header, text="Theme  ").pack(side="right")

        self.cards = []
        self.names = []
        self.times = []
        self.indicators = []
        for player, name in enumerate(("LEFT", "RIGHT")):
            card = ttk.Frame(content, padding=18, style=f"Player{player}.TFrame")
            card.grid(row=1, column=player, sticky="nsew",
                      padx=(0, 6) if player == 0 else (6, 0))
            card.columnconfigure(0, weight=1)
            card.rowconfigure(1, weight=1)
            title = ttk.Label(card, text=name, font=("DejaVu Sans", 16, "bold"),
                              anchor="center", style=f"Player{player}.TLabel")
            title.grid(row=0, column=0, sticky="ew")
            timer = ttk.Label(card, font=("DejaVu Sans Mono", 56, "bold"),
                              anchor="center", style=f"Player{player}.TLabel")
            timer.grid(row=1, column=0, sticky="nsew")
            indicator = ttk.Label(card, anchor="center", font=("DejaVu Sans", 12),
                                  style=f"Player{player}.TLabel")
            indicator.grid(row=2, column=0, sticky="ew")
            self.cards.append(card)
            self.names.append(title)
            self.times.append(timer)
            self.indicators.append(indicator)

        self.status = ttk.Label(content, anchor="center", font=("DejaVu Sans", 12))
        self.status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        self.rocker_buttons = []
        for side, label in enumerate(("Left player", "Right player")):
            button = ttk.Button(content, text=label, style="Touch.TButton",
                                command=lambda side=side: self.rocker(side))
            button.grid(row=3, column=side, sticky="ew", padx=4, pady=(0, 10))
            self.rocker_buttons.append(button)
        controls = ttk.Frame(content)
        controls.grid(row=4, column=0, columnspan=2, sticky="ew")
        controls.columnconfigure((0, 1, 2), weight=1, uniform="controls")
        self.start_button = ttk.Button(controls, text="Start", style="Touch.TButton", command=self.start)
        self.pause_button = ttk.Button(controls, text="Pause", style="Touch.TButton", command=self.pause)
        self.reset_button = ttk.Button(controls, text="Reset", style="Touch.TButton", command=self.reset)
        for column, button in enumerate((self.start_button, self.pause_button, self.reset_button)):
            button.grid(row=0, column=column, sticky="ew", padx=4)
        ttk.Label(content, text="Rocker test: ← Left player     |     Right player →",
                  anchor="center").grid(row=5, column=0, columnspan=2, pady=(10, 0))
        window.bind("<Left>", lambda event: self.rocker(0))
        window.bind("<Right>", lambda event: self.rocker(1))
        window.bind("<Escape>", lambda event: window.attributes("-fullscreen", False))
        self.build_settings()
        self.show_settings()
        self.tick()

    def build_settings(self):
        self.settings_frame = ttk.Frame(self.window, padding=24)
        self.settings_frame.grid(row=0, column=0, sticky="nsew")
        self.settings_frame.columnconfigure(0, weight=1)
        self.settings_frame.rowconfigure(4, weight=1)
        self.settings_minutes = StringVar(self.window, value=str(max(1, round(self.clock.initial_seconds / 60))))
        self.settings_increment = StringVar(self.window, value=str(int(self.clock.increment)))
        ttk.Label(self.settings_frame, text="Game settings", font=("DejaVu Sans", 24, "bold")).grid(
            row=0, column=0, pady=(0, 6))
        ttk.Label(self.settings_frame, text="One time control for both players", font=("DejaVu Sans", 12)).grid(
            row=1, column=0, pady=(0, 16))
        for row, (label, variable, minimum, maximum) in enumerate((
            ("Starting time · minutes", self.settings_minutes, 1, 180),
            ("Increment per move · seconds", self.settings_increment, 0, 60),
        ), start=2):
            setting = ttk.Frame(self.settings_frame)
            setting.grid(row=row, column=0, sticky="ew", pady=8)
            setting.columnconfigure(0, weight=1)
            ttk.Label(setting, text=label, font=("DejaVu Sans", 15)).grid(row=0, column=0, sticky="w")
            for column, (text, delta) in enumerate((("−", -1), ("+", 1)), start=1):
                ttk.Button(setting, text=text, width=3, style="Touch.TButton",
                           command=lambda v=variable, d=delta, lo=minimum, hi=maximum:
                           self.adjust_setting(v, d, lo, hi)).grid(row=0, column=column * 2 - 1, padx=8)
            ttk.Label(setting, textvariable=variable, width=3, anchor="center",
                      font=("DejaVu Sans Mono", 24, "bold")).grid(row=0, column=2)
        self.settings_colors = ttk.Label(self.settings_frame, anchor="center", font=("DejaVu Sans", 12))
        self.settings_colors.grid(row=4, column=0, sticky="ew", pady=8)
        rockers = ttk.Frame(self.settings_frame)
        rockers.grid(row=5, column=0, sticky="ew")
        rockers.columnconfigure((0, 1), weight=1, uniform="rockers")
        for side, label in enumerate(("Left player", "Right player")):
            ttk.Button(rockers, text=label, style="Touch.TButton",
                       command=lambda side=side: self.rocker(side)).grid(row=0, column=side, sticky="ew", padx=4)
        ttk.Label(self.settings_frame, text="Last rocker pressed is Black · ← Left / Right →").grid(
            row=6, column=0, pady=8)
        self.ready_button = ttk.Button(self.settings_frame, text="Continue to clock", style="Touch.TButton",
                                      command=self.apply_settings)
        self.ready_button.grid(row=7, column=0, sticky="ew")

    def adjust_setting(self, variable, delta, minimum, maximum):
        variable.set(str(max(minimum, min(maximum, int(variable.get()) + delta))))

    def show_settings(self):
        if self.clock.started:
            return
        self.settings_visible = True
        self.game_frame.grid_remove()
        self.settings_frame.grid()

    def apply_settings(self):
        if self.clock.started:
            return
        self.clock.configure(int(self.settings_minutes.get()), int(self.settings_increment.get()))
        self.settings_visible = False
        self.settings_frame.grid_remove()
        self.game_frame.grid()
        self.render()

    def change_theme(self, _event=None):
        self.window.set_theme(self.theme.get())
        self.render()

    def start(self):
        if self.settings_visible:
            return
        self.clock.start()
        self.render()

    def pause(self):
        self.clock.pause()
        self.render()

    def reset(self):
        self.clock.reset()
        self.render()

    def rocker(self, player):
        self.clock.press_rocker(player)
        self.render()
        return "break"

    def render(self):
        clock = self.clock
        style = ttk.Style(self.window)
        style.configure("Touch.TButton", font=("DejaVu Sans", 14, "bold"), padding=(12, 12))
        self.settings_colors.configure(text=f"Left: {clock.color(0)}     |     Right: {clock.color(1)}")
        self.settings_button.state(["disabled"] if clock.started else ["!disabled"])
        for player in (0, 1):
            selected = player == clock.active
            expired = player == clock.expired
            background = "#9b2638" if expired else "#145b78" if selected else "#e8edf1"
            foreground = "#ffffff" if selected or expired else "#263744"
            style.configure(f"Player{player}.TFrame", background=background)
            style.configure(f"Player{player}.TLabel", background=background, foreground=foreground)
            side_name = "LEFT" if player == 0 else "RIGHT"
            self.names[player].configure(text=f"{side_name} · {clock.color(player).upper()}")
            self.times[player].configure(text=format_time(clock.remaining[player]))
            indicator = "WAITING"
            if expired:
                indicator = "TIME EXPIRED"
            elif selected:
                if clock.running:
                    indicator = "YOUR TURN"
                elif not clock.started:
                    indicator = "READY"
                else:
                    indicator = "PAUSED"
            self.indicators[player].configure(text=indicator)
        if clock.expired is not None:
            message = f"{clock.color(clock.expired)} ran out of time — reset to play again"
        elif not clock.started:
            message = (f"{clock.initial_seconds // 60:g} min + {clock.increment:g} sec per move"
                       " · Last rocker pressed is Black")
        else:
            player = clock.color(clock.active)
            message = f"{player} to move" if clock.running else f"Paused — {player} to move"
        self.status.configure(text=message)
        self.start_button.configure(text="Resume" if clock.started else "Start")
        self.start_button.state(["disabled"] if clock.running or clock.expired is not None else ["!disabled"])
        self.pause_button.state(["!disabled"] if clock.running else ["disabled"])
        for button in self.rocker_buttons:
            button.state(["!disabled"] if not clock.started or clock.running else ["disabled"])

    def tick(self):
        self.clock.update()
        self.render()
        self._job = self.window.after(50, self.tick)

    def close(self):
        if self._job is not None:
            self.window.after_cancel(self._job)
        self.window.destroy()


def create_window(theme: str = "arc", seconds: float = 300, increment: int = 0) -> ThemedTk:
    clock = ChessClock(seconds, increment=increment)
    window = ThemedTk()
    themes = sorted(window.get_themes())
    if theme not in themes:
        window.destroy()
        raise ValueError(f"Unknown theme {theme!r}. Available: {', '.join(themes)}")
    window.set_theme(theme)
    window.clock_ui = ClockUI(window, clock)
    return window


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", default="arc", help="Initial ttk theme (default: arc)")
    parser.add_argument("--minutes", type=int, choices=range(1, 181), metavar="1-180",
                        default=5, help="Starting minutes per player (default: 5)")
    parser.add_argument("--increment", type=int, choices=range(0, 61), metavar="0-60",
                        default=0, help="Increment seconds per move (default: 0)")
    parser.add_argument("--fullscreen", action="store_true", help="Fill the TFT display; Escape exits fullscreen")
    args = parser.parse_args()
    try:
        window = create_window(args.theme, seconds=args.minutes * 60, increment=args.increment)
    except ValueError as error:
        parser.error(str(error))
    if args.fullscreen:
        window.attributes("-fullscreen", True)
    window.mainloop()


if __name__ == "__main__":
    main()
